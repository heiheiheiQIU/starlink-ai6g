import copy

import pytest

from backend.contracts import Action, Observation
from backend.simulator.engine import create_state, step
from training.generate_policy_pilot import PilotDataError, admit_state, sample_source
from training.pilot_scenarios import build_sources, sha256_json


def test_sampling_uses_real_steps_and_preserves_source_identity():
    source = build_sources()[0]
    rows = sample_source(source)
    assert 2 <= len(rows) <= 4
    assert {row["source_id"] for row in rows} == {source["source_id"]}
    assert len({row["observation"]["sim_time_s"] for row in rows}) >= 2


@pytest.mark.parametrize("mutation", ["inflight", "retry", "pending"])
def test_admission_rejects_unresolved_private_protocol_state(mutation):
    source = build_sources()[0]
    state = create_state(source["scenario"], run_id=source["source_id"], policy_id="pilot")
    advanced = step(state, Action.model_validate(source["evolution_steps"][0]["action"]), 2.0).next_state
    if mutation == "inflight":
        state = advanced
    elif mutation == "retry":
        state.protocol_state.retry_required_key = ("T00", 0)
    else:
        state.protocol_state.pending.append(copy.deepcopy(advanced.protocol_state.pending[0]))
    with pytest.raises(PilotDataError, match="SOURCE_PROTOCOL_STATE") as error:
        admit_state(state)
    assert error.value.code == "SOURCE_PROTOCOL_STATE"


def test_records_are_public_observations_with_block_aligned_partial_delivery():
    forbidden = {"protocol_state", "true_windows", "future_arrivals", "energy_true_Wh", "evaluation_truth"}

    def check_keys(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            for child in value.values():
                check_keys(child)
        elif isinstance(value, list):
            for child in value:
                check_keys(child)

    rows = [row for source in build_sources() for row in sample_source(source)]
    assert any(row["observation"]["sim_time_s"] > 0 for row in rows)
    partial = False
    for row in rows:
        check_keys(row)
        observation = Observation.model_validate(row["observation"])
        assert row["observation_sha256"] == sha256_json(row["observation"])
        for task in observation.tasks:
            assert task.remaining_bytes > 0
            assert (task.payload_bytes - task.remaining_bytes) % 1024 == 0
            partial |= task.remaining_bytes < task.payload_bytes
    assert partial


def test_sampling_is_deterministic_and_records_have_only_public_fields():
    source = build_sources()[0]
    rows = sample_source(source)
    assert rows == sample_source(source)
    assert len({row["state_id"] for row in rows}) == len(rows)
    for row in rows:
        assert set(row) == {"source_id", "family", "seed", "capture_index", "state_id", "observation", "observation_sha256"}
        assert row["seed"] == source["seed"]
        assert row["family"] == source["family"]


@pytest.mark.parametrize("captures", [[0], [0, 1, 2, 3, 4]])
def test_capture_count_is_enforced(captures):
    source = copy.deepcopy(build_sources()[1])
    source["capture_after_steps"] = captures
    if len(captures) > 4:
        source["evolution_steps"] *= 2
    with pytest.raises(PilotDataError, match="CAPTURE_COUNT"):
        sample_source(source)


@pytest.mark.parametrize("mutation,code", [
    ("health", "FUTURE_HEALTH"),
    ("task", "FUTURE_TASK"),
    ("robust_loss_prob", "UNSUPPORTED_LOSS"),
    ("fast_loss_prob", "UNSUPPORTED_LOSS"),
])
def test_admission_rejects_unsupported_public_observation(monkeypatch, mutation, code):
    from backend.simulator.engine import observe

    source = build_sources()[0]
    state = create_state(source["scenario"], run_id=source["source_id"], policy_id="pilot")
    observation = observe(state).model_copy(deep=True)
    if mutation == "health":
        observation.health.available_at_s = observation.sim_time_s + 1
    elif mutation == "task":
        observation.tasks[0].arrival_s = observation.sim_time_s + 1
    else:
        setattr(observation.forecast_windows[0].loss_profile[0], mutation, 0.1)
    monkeypatch.setattr("training.generate_policy_pilot.observe", lambda _: observation)
    with pytest.raises(PilotDataError, match=code) as error:
        admit_state(state)
    assert error.value.code == code
