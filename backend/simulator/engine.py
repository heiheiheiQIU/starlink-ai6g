"""Single-policy R2 synthetic validation. ACK/receive/retry belong to R3."""

import argparse
import copy
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Literal

from pydantic import model_validator

from backend.contracts import (Action, ContractModel, Event, HealthEstimate, InFlight,
    NonEmpty, NonNegativeFloat, Observation, PositiveFloat, SnapshotData, StepResult, Task, Window)
from .energy import EnergyLedgerEntry, PowerProfile, advance_energy, finite_number
from .link import transmission_time
from .queue import visible_tasks
from .protocol import ProtocolConfig, ProtocolState


class TransmitPower(ContractModel):
    robust: NonNegativeFloat
    fast: NonNegativeFloat


class ScenarioConfig(ContractModel):
    schema_version: Literal["1.0"]
    scenario_id: NonEmpty
    source: Literal["synthetic"]
    capacity_Wh: PositiveFloat
    initial_energy_Wh: NonNegativeFloat
    reserve_Wh: NonNegativeFloat
    max_power_W: PositiveFloat
    powers: PowerProfile
    tx_power_W: TransmitPower
    slot_s: PositiveFloat
    forecast_version: NonEmpty
    tasks: list[Task]
    true_windows: list[Window]
    forecast_windows: list[Window]
    health_observations: list[HealthEstimate]
    protocol: ProtocolConfig | None = None

    @model_validator(mode="after")
    def supported_deterministic_scenario(self):
        if self.protocol is not None:
            control_time = 128 / self.protocol.control_bps + self.protocol.ack_propagation_s
            if control_time > self.slot_s:
                raise ValueError('ACK control/propagation must fit one slot')
            if self.powers.base_W + self.powers.compute_W + self.protocol.ack_rx_W > self.max_power_W:
                raise ValueError('Active ACK reception exceeds power limit')
        if max(self.initial_energy_Wh, self.reserve_Wh) > self.capacity_Wh:
            raise ValueError("Initial energy/reserve cannot exceed capacity")
        ids = [task.task_id for task in self.tasks]
        if len(ids) != len(set(ids)) or any(t.remaining_bytes != t.payload_bytes for t in self.tasks):
            raise ValueError("Scenario tasks need unique IDs and full initial payload")
        for windows in (self.true_windows, self.forecast_windows):
            ids = [window.window_id for window in windows]
            if len(ids) != len(set(ids)) or any(w.source != "synthetic" for w in windows):
                raise ValueError("Window IDs must be unique and sources synthetic")
        actual = sorted(self.true_windows, key=lambda w: w.start_s)
        if any(left.end_s > right.start_s for left, right in zip(actual, actual[1:])):
            raise ValueError("Overlapping actual windows are ambiguous")
        if any(point.robust_loss_prob != 0 or point.fast_loss_prob != 0
               for window in actual for point in window.loss_profile):
            raise ValueError("R2 only supports deterministic zero actual loss")
        if any(w.forecast_version != self.forecast_version for w in self.forecast_windows):
            raise ValueError("Forecast windows must use one declared batch")
        if not any(h.available_at_s == 0.0 for h in self.health_observations):
            raise ValueError("An explicit health observation must be available at start")
        times = [h.available_at_s for h in self.health_observations]
        if len(times) != len(set(times)):
            raise ValueError("Health availability times must be unique")
        return self


@dataclass(frozen=True)
class TimedEnergy:
    start_s: float
    end_s: float
    entry: EnergyLedgerEntry


@dataclass
class SimulatorState:
    """Private environment data. Never pass this to a learned scorer."""
    run_id: str
    policy_id: str
    config: ScenarioConfig
    sim_time_s: float = 0.0
    energy_Wh: float = 0.0
    tasks: list[Task] = field(default_factory=list)
    inflight: InFlight | None = None
    next_event_id: int = 1
    announced: set[str] = field(default_factory=set)
    expired: set[str] = field(default_factory=set)
    energy_ledger: list[TimedEnergy] = field(default_factory=list)
    protocol_state: ProtocolState = field(default_factory=ProtocolState)


def load_scenario(path: Path) -> ScenarioConfig:
    return ScenarioConfig.model_validate_json(path.read_text(encoding="utf-8"))


def create_state(config: ScenarioConfig | dict, *, run_id: str = "r2_minimal_validation",
                 policy_id: str = "manual") -> SimulatorState:
    parsed = ScenarioConfig.model_validate(config).model_copy(deep=True)
    state = SimulatorState(run_id, policy_id, parsed, energy_Wh=parsed.initial_energy_Wh,
                           tasks=copy.deepcopy(parsed.tasks))
    observe(state)  # Validate public IDs and initial observability before a run starts.
    return state


def observe(state: SimulatorState) -> Observation:
    available = [health for health in state.config.health_observations
                 if health.available_at_s <= state.sim_time_s]
    if not available:
        raise ValueError("No health observation available")
    health = max(available, key=lambda item: item.available_at_s)
    if state.config.protocol is not None:
        # Propagate only observable modeled flows, never energy_before/after truth.
        lower, estimate = health.energy_lower_Wh, health.soc_est * health.capacity_Wh_est
        propagated = False
        for row in state.energy_ledger:
            left = max(row.start_s, health.observed_at_s)
            right = min(row.end_s, state.sim_time_s)
            if right <= left:
                continue
            fraction = (right-left)/(row.end_s-row.start_s)
            entry = row.entry
            change = (entry.solar_input_Wh-entry.consumed_Wh)*fraction
            lower = min(health.capacity_lower_Wh, max(0.0, lower+change))
            estimate = min(health.capacity_Wh_est, max(0.0, estimate+change))
            propagated = True
        if propagated:
            soc = estimate/health.capacity_Wh_est
            soc_lower = min(soc,lower/health.capacity_lower_Wh) if health.capacity_lower_Wh else 0.0
            health = health.model_copy(update=dict(soc_est=soc,soc_lower=soc_lower,
                energy_lower_Wh=soc_lower*health.capacity_lower_Wh,
                reason_codes=list(dict.fromkeys([*health.reason_codes,'ENERGY_PROPAGATED']))))
    tasks = visible_tasks(state.tasks, state.sim_time_s)
    # Retain only the metadata needed to reference an unacknowledged block,
    # even when its business deadline passes. It is not a new schedulable task.
    if state.inflight is not None and state.inflight.task_id not in {t.task_id for t in tasks}:
        tasks.extend(t.model_copy(deep=True) for t in state.tasks if t.task_id == state.inflight.task_id)
    return Observation(schema_version="1.0", run_id=state.run_id, policy_id=state.policy_id,
        sim_time_s=state.sim_time_s, tasks=tasks, forecast_windows=state.config.forecast_windows,
        health=health, inflight=state.inflight, cache_bytes=sum(t.remaining_bytes for t in tasks),
        forecast_version=state.config.forecast_version)


def _energy_segments(state: SimulatorState, dt: float, airtime: float, tx: float,
                     initial: float | None = None) -> list[TimedEnergy]:
    energy = state.energy_Wh if initial is None else initial
    capacity = state.config.capacity_Wh if initial is None else max(state.config.capacity_Wh, energy)
    cursor = state.sim_time_s
    result = []
    step_end = finite_number(state.sim_time_s + dt, "step end")
    cuts = ([(min(step_end, state.sim_time_s + airtime), tx)] if airtime > 0 else [])
    cuts.append((step_end, 0.0))
    for end, power in cuts:
        duration = end - cursor
        if duration <= 0:
            continue
        entry = advance_energy(energy, capacity, duration, state.config.powers, power)
        result.append(TimedEnergy(cursor, end, entry))
        energy, cursor = entry.energy_after_Wh, end
    return result


def step(state: SimulatorState, action: Action, dt_s: float) -> StepResult:
    if state.config.protocol is not None:
        from .r3_engine import protocol_step
        return protocol_step(state, action, dt_s)
    dt = finite_number(dt_s, "dt_s", positive=True)
    end = finite_number(state.sim_time_s + dt, "step end")
    if end <= state.sim_time_s:
        raise ValueError("dt_s is too small to advance this floating-point clock")
    command = Action.model_validate(action)
    current = copy.deepcopy(state)
    obs = observe(current)
    events = []

    def emit(time, kind, *, task_id=None, block_id=None, payload=0, overhead=0,
             energy=0.0, reason=None, data=None):
        events.append(Event(event_id=1, run_id=current.run_id, policy_id=current.policy_id,
            sim_time_s=time, event_type=kind, task_id=task_id, block_id=block_id,
            payload_bytes=payload, overhead_bytes=overhead, energy_Wh=energy,
            reason_code=reason, data=data))

    for task in current.tasks:
        if task.arrival_s <= end and task.task_id not in current.announced:
            emit(task.arrival_s, "arrived", task_id=task.task_id, payload=task.payload_bytes)
            current.announced.add(task.task_id)

    reason, airtime, tx = None, 0.0, 0.0
    selected = next((task for task in obs.tasks if task.task_id == command.task_id
                     and task.deadline_s >= current.sim_time_s), None)
    if command.mode != "idle":
        if current.inflight is not None:
            reason = "INFLIGHT_BLOCK"
        elif selected is None:
            reason = "TASK_NOT_AVAILABLE"
        elif command.scheduled_bytes != min(1024, selected.remaining_bytes):
            reason = "INVALID_BLOCK_SIZE"
        elif not any(w.start_s <= current.sim_time_s < w.end_s for w in current.config.true_windows):
            reason = "NO_VISIBLE_WINDOW"
        else:
            duration = transmission_time(current.config.true_windows, current.sim_time_s,
                                          command.mode, command.scheduled_bytes + 32, dt)
            power = getattr(current.config.tx_power_W, command.mode)
            if duration is None:
                reason = "INSUFFICIENT_LINK_TIME"
            elif current.config.powers.base_W + current.config.powers.compute_W + power > current.config.max_power_W:
                reason = "POWER_LIMIT"
            else:
                # Guard on observable lower energy, never hidden physical truth.
                estimate = _energy_segments(current, dt, duration, power, obs.health.energy_lower_Wh)
                minimum = min(obs.health.energy_lower_Wh,
                              *(row.entry.energy_unclipped_Wh for row in estimate))
                if minimum < current.config.reserve_Wh:
                    reason = "ENERGY_RESERVE"
                else:
                    airtime, tx = duration, power
                    timeout = finite_number(current.sim_time_s + airtime + 2 * current.config.slot_s,
                                            "block timeout", positive=True)
                    current.inflight = InFlight(task_id=selected.task_id, block_id=0,
                        payload_bytes=command.scheduled_bytes, mode=command.mode,
                        sent_at_s=current.sim_time_s, timeout_at_s=timeout, retries=0)
                    emit(current.sim_time_s, "sent", task_id=selected.task_id, block_id=0,
                         payload=command.scheduled_bytes, overhead=32, energy=tx * airtime / 3600.0)
        if reason:
            emit(current.sim_time_s, "fallback", task_id=command.task_id, reason=reason)

    for row in _energy_segments(current, dt, airtime, tx):
        current.energy_ledger.append(row)
        current.energy_Wh, current.sim_time_s = row.entry.energy_after_Wh, row.end_s
        health = observe(current).health
        reasons = ["R2_FORECAST_BAND_UNAVAILABLE"]
        if row.entry.lower_violation:
            reasons.append("ENERGY_BELOW_ZERO")
        data = SnapshotData(soc_est=health.soc_est, energy_est_Wh=health.soc_est * health.capacity_Wh_est,
            energy_lower_Wh=health.energy_lower_Wh, queue_count=len(observe(current).tasks),
            forecast_energy_band=None, policy_version="manual-r2-v1", reason_codes=reasons,
            evaluation_truth=dict(label="posthoc_simulation", energy_true_Wh=row.entry.energy_unclipped_Wh,
                soc_true=row.entry.energy_unclipped_Wh / current.config.capacity_Wh,
                capacity_true_Wh=current.config.capacity_Wh))
        emit(row.end_s, "snapshot", energy=row.entry.background_Wh + row.entry.compute_Wh, data=data)

    for task in current.tasks:
        if task.deadline_s < end and task.task_id not in current.expired and (
            current.inflight is None or current.inflight.task_id != task.task_id):
            emit(end, "dropped", task_id=task.task_id, payload=task.remaining_bytes, reason="DEADLINE_EXPIRED")
            current.expired.add(task.task_id)
    events.sort(key=lambda event: event.sim_time_s)
    for event in events:
        event.event_id = current.next_event_id
        current.next_event_id += 1
    current.sim_time_s = end
    return StepResult(next_state=current, events=events)


def export_demo(config: ScenarioConfig, output: Path) -> None:
    """Export actual send-only synthetic execution, never a completed RunResult."""
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be new or empty")
    output.mkdir(parents=True, exist_ok=True)
    state = create_state(config)
    tasks = observe(state).tasks
    action = Action(task_id=tasks[0].task_id if tasks else None, mode="robust" if tasks else "idle",
        scheduled_bytes=min(1024, tasks[0].remaining_bytes) if tasks else 0, reason_codes=[], fallback=False)
    result = step(state, action, 2.0)
    write = lambda path, value: path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8", newline="\n")
    write(output / "config.json", config.model_dump())
    (output / "events.jsonl").write_text("".join(event.model_dump_json() + "\n" for event in result.events),
                                        encoding="utf-8", newline="\n")
    write(output / "energy_ledger.json", [asdict(row) for row in result.next_state.energy_ledger])
    root = Path(__file__).resolve().parents[2]
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                              text=True, check=False).stdout.strip() or None
    code_files = [root / "backend/contracts.py", *sorted(Path(__file__).parent.glob("*.py"))]
    write(output / "manifest.json", dict(kind="r2_synthetic_validation", source="synthetic",
        protocol_stage="send_only_ack_pending", is_real_satellite_measurement=False, is_policy_benchmark=False,
        run_id=state.run_id, policy_id=state.policy_id, code_revision=revision,
        source_sha256={path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in code_files},
        artifacts_sha256={name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                          for name in ("config.json", "events.jsonl", "energy_ledger.json")}))


def main():
    parser = argparse.ArgumentParser(description="R2 send-only synthetic validation, no final results or API")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export_demo(load_scenario(args.config), args.output)


if __name__ == "__main__":
    main()
