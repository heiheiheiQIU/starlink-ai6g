"""Sample public, protocol-clean observations from real pilot evolution."""

from backend.contracts import Action, Observation
from backend.simulator.engine import SimulatorState, create_state, observe, step
from training.pilot_scenarios import sha256_json


class PilotDataError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def admit_state(state: SimulatorState) -> Observation:
    protocol = state.protocol_state
    if (state.inflight is not None
            or protocol.retry_required_key is not None
            or protocol.pending):
        raise PilotDataError(
            "SOURCE_PROTOCOL_STATE",
            "State has inflight, retry, or pending protocol work",
        )
    observation = observe(state)
    if observation.health.available_at_s > observation.sim_time_s:
        raise PilotDataError("FUTURE_HEALTH", "Health is not yet available")
    if any(task.arrival_s > observation.sim_time_s for task in observation.tasks):
        raise PilotDataError("FUTURE_TASK", "Future task leaked into observation")
    if any(
        point.robust_loss_prob != 0.0 or point.fast_loss_prob != 0.0
        for window in observation.forecast_windows
        for point in window.loss_profile
    ):
        raise PilotDataError("UNSUPPORTED_LOSS", "Pilot labels require zero loss")
    return observation


def _source_record(
    source: dict[str, object], capture_index: int, observation: Observation
) -> dict[str, object]:
    payload = observation.model_dump(mode="json")
    return {
        "source_id": source["source_id"],
        "family": source["family"],
        "seed": source["seed"],
        "capture_index": capture_index,
        "state_id": f"{source['source_id']}:{capture_index}",
        "observation": payload,
        "observation_sha256": sha256_json(payload),
    }


def sample_source(source: dict[str, object]) -> list[dict[str, object]]:
    state = create_state(
        source["scenario"], run_id=str(source["source_id"]), policy_id="pilot-source"
    )
    captured = []
    capture_steps = set(source["capture_after_steps"])
    if 0 in capture_steps:
        captured.append(_source_record(source, 0, admit_state(state)))
    for index, command in enumerate(source["evolution_steps"], start=1):
        state = step(
            state, Action.model_validate(command["action"]), float(command["dt_s"])
        ).next_state
        if index in capture_steps:
            captured.append(_source_record(source, index, admit_state(state)))
    if not 2 <= len(captured) <= 4:
        raise PilotDataError("CAPTURE_COUNT", "Each source needs 2..4 states")
    return captured
