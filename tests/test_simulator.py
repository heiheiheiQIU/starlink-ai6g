"""R2 deterministic synthetic checks, not satellite measurements or policy results."""

import copy
import json
from pathlib import Path

import pytest

from backend.contracts import Task, Window
from backend.simulator.energy import PowerProfile, advance_energy
from backend.simulator.link import transmission_time
from backend.simulator.queue import visible_tasks


def task(arrival=0.0, deadline=200.0):
    return Task(task_id="T1", arrival_s=arrival, deadline_s=deadline,
                payload_bytes=1024, remaining_bytes=1024, priority_weight=1.0,
                business_class="synthetic", data_location="satellite_1")


def window(start=0.0, end=120.0):
    return Window(window_id="W1", start_s=start, end_s=end,
                  rate_profile=[dict(time_s=start, robust_bps=8192.0, fast_bps=16384.0)],
                  loss_profile=[dict(time_s=start, robust_loss_prob=0.0, fast_loss_prob=0.0)],
                  source="synthetic", forecast_version="r2-synthetic-v1")


def test_36_watt_net_load_for_100_seconds_consumes_one_Wh():
    entry = advance_energy(10.0, 20.0, 100.0, PowerProfile(base_W=36.0))
    assert entry.energy_unclipped_Wh == pytest.approx(9.0)
    assert entry.energy_after_Wh == pytest.approx(9.0)
    assert entry.consumed_Wh == pytest.approx(1.0)
    assert not entry.lower_violation


def test_negative_energy_evidence_survives_clipping():
    entry = advance_energy(0.1, 20.0, 100.0, PowerProfile(base_W=36.0))
    assert entry.energy_unclipped_Wh == pytest.approx(-0.9)
    assert entry.energy_after_Wh == 0.0
    assert entry.lower_violation


def test_solar_input_is_separate_and_capacity_is_clipped():
    entry = advance_energy(19.9, 20.0, 100.0, PowerProfile(base_W=36.0, solar_W=72.0))
    assert entry.energy_unclipped_Wh == pytest.approx(20.9)
    assert entry.energy_after_Wh == 20.0
    assert entry.solar_input_Wh == pytest.approx(2.0)
    assert entry.consumed_Wh == pytest.approx(1.0)


@pytest.mark.parametrize("duration", [0.0, -1.0, float("nan"), float("inf"), True])
def test_energy_rejects_invalid_duration(duration):
    with pytest.raises(ValueError):
        advance_energy(10.0, 20.0, duration, PowerProfile())


def test_queue_excludes_future_and_expired_but_keeps_deadline_equality():
    future, current, expired = task(15.0, 20.0), task(0.0, 10.0), task(0.0, 9.0)
    future.task_id, expired.task_id = "future", "expired"
    tasks = [future, current, expired]
    assert [item.task_id for item in visible_tasks(tasks, 10.0)] == ["T1"]
    visible_tasks(tasks, 10.0)[0].remaining_bytes = 0
    assert current.remaining_bytes == 1024


def test_data_header_consumes_real_link_time():
    assert transmission_time([window()], 0.0, "robust", 1056, 2.0) == pytest.approx(1.03125)


@pytest.mark.parametrize("windows,now,dt", [([], 0.0, 2.0), ([window(2.0, 10.0)], 0.0, 3.0),
    ([window()], 120.0, 2.0), ([window(0.0, 1.03125)], 0.0, 2.0), ([window()], 0.0, 1.0)])
def test_link_rejects_no_window_end_boundary_or_insufficient_time(windows, now, dt):
    assert transmission_time(windows, now, "robust", 1056, dt) is None


def test_link_integrates_piecewise_rates_instead_of_extending_initial_rate():
    data = window().model_dump()
    data["rate_profile"] = [dict(time_s=0.0, robust_bps=8192.0, fast_bps=16384.0),
                            dict(time_s=0.5, robust_bps=4096.0, fast_bps=8192.0)]
    # 4096 bits first 0.5s, remaining 4352 bits at 4096bps -> 1.5625s total.
    assert transmission_time([Window.model_validate(data)], 0.0, "robust", 1056, 2.0) == pytest.approx(1.5625)
    data["rate_profile"][0]["robust_bps"] = 0.0
    data["rate_profile"] = data["rate_profile"][:1]
    assert transmission_time([Window.model_validate(data)], 0.0, "robust", 1056, 2.0) is None


def scenario_data():
    return dict(schema_version="1.0", scenario_id="synthetic_r2", source="synthetic",
        capacity_Wh=20.0, initial_energy_Wh=10.0, reserve_Wh=0.5, max_power_W=150.0,
        powers=dict(base_W=36.0, solar_W=0.0, compute_W=0.0),
        tx_power_W=dict(robust=36.0, fast=72.0), slot_s=1.0,
        forecast_version="r2-synthetic-v1", tasks=[task().model_dump()],
        true_windows=[window().model_dump()], forecast_windows=[window().model_dump()],
        health_observations=[dict(soc_est=0.5, soc_lower=0.45, capacity_Wh_est=20.0,
            capacity_lower_Wh=20.0, energy_lower_Wh=9.0, rul_est=None, rul_unit=None,
            uncertainty_method="synthetic_fixed_bounds", model_version="synthetic-r2-v1",
            observed_at_s=0.0, available_at_s=0.0, reason_codes=["RUL_UNAVAILABLE"])])


def send_action():
    from backend.contracts import Action
    return Action(task_id="T1", mode="robust", scheduled_bytes=1024, reason_codes=[], fallback=False)


def idle_action():
    from backend.contracts import Action
    return Action(task_id=None, mode="idle", scheduled_bytes=0, reason_codes=[], fallback=False)


def create_state(data=None):
    from backend.simulator.engine import create_state
    return create_state(scenario_data() if data is None else data, run_id="r2_handcheck", policy_id="manual")


def test_engine_36W_100s_energy_and_event_accounting():
    from backend.simulator.engine import observe, step
    state = create_state()
    result = step(state, idle_action(), 100.0)
    assert result.next_state.energy_Wh == pytest.approx(9.0)
    assert sum(event.energy_Wh for event in result.events) == pytest.approx(1.0)
    assert state.energy_Wh == 10.0 and state.sim_time_s == 0.0
    assert observe(result.next_state).health.soc_est == 0.5  # No invented truth-based sensor update.


def test_engine_records_negative_energy_in_snapshot_before_clip():
    from backend.simulator.engine import step
    data = scenario_data(); data["initial_energy_Wh"] = 0.1
    result = step(create_state(data), idle_action(), 100.0)
    assert result.next_state.energy_Wh == 0.0
    assert result.next_state.energy_ledger[-1].entry.energy_unclipped_Wh == pytest.approx(-0.9)
    snap = [e for e in result.events if e.event_type == "snapshot"][-1]
    assert snap.data.evaluation_truth.energy_true_Wh == pytest.approx(-0.9)
    assert "ENERGY_BELOW_ZERO" in snap.data.reason_codes


def test_engine_rejects_send_without_current_window_even_if_one_opens_during_step():
    from backend.simulator.engine import step
    data = scenario_data(); data["true_windows"] = [window(20.0, 120.0).model_dump()]
    result = step(create_state(data), send_action(), 30.0)
    assert not any(e.event_type == "sent" for e in result.events)
    assert any(e.reason_code == "NO_VISIBLE_WINDOW" for e in result.events)
    assert result.next_state.inflight is None


def test_engine_filters_future_tasks_and_future_health_and_hides_actual_window():
    from backend.simulator.engine import observe, step
    data = scenario_data(); data["tasks"][0]["arrival_s"] = 5.0
    data["true_windows"] = [window(70.0, 90.0).model_dump()]
    future = copy.deepcopy(data["health_observations"][0]); future.update(available_at_s=5.0, observed_at_s=5.0)
    future.update(soc_est=0.9, soc_lower=0.8, energy_lower_Wh=16.0)
    data["health_observations"].append(future)
    state = create_state(data); observed = observe(state)
    assert observed.tasks == [] and observed.cache_bytes == 0
    assert observed.health.soc_est == 0.5
    assert observed.forecast_windows[0].start_s == 0.0
    assert not any(key in observed.model_dump() for key in ("energy_Wh", "true_windows", "capacity_Wh"))
    result = step(state, send_action(), 5.0)
    assert not any(e.event_type == "sent" for e in result.events)
    assert observe(result.next_state).tasks[0].arrival_s == 5.0
    assert observe(result.next_state).health.soc_est == 0.9


def test_send_charges_only_airtime_and_retains_single_unacknowledged_block():
    from backend.simulator.engine import observe, step
    state = create_state(); result = step(state, send_action(), 2.0)
    sent = [e for e in result.events if e.event_type == "sent"]
    assert len(sent) == 1 and sent[0].payload_bytes == 1024 and sent[0].overhead_bytes == 32
    expected_consumption = (36.0 * 2.0 + 36.0 * 1.03125) / 3600.0
    assert result.next_state.energy_Wh == pytest.approx(10.0 - expected_consumption)
    assert sum(e.energy_Wh for e in result.events) == pytest.approx(expected_consumption)
    assert result.next_state.inflight.payload_bytes == 1024
    assert observe(result.next_state).tasks[0].remaining_bytes == 1024
    assert not any(e.event_type in {"received", "acked"} for e in result.events)
    second = step(result.next_state, send_action(), 2.0)
    assert not any(e.event_type == "sent" for e in second.events)
    assert any(e.reason_code == "INFLIGHT_BLOCK" for e in second.events)


@pytest.mark.parametrize("change,reason", [({"initial_energy_Wh": 0.51}, "ENERGY_RESERVE"),
    ({"max_power_W": 40.0}, "POWER_LIMIT"), ({"true_windows": []}, "NO_VISIBLE_WINDOW")])
def test_send_safety_checks_produce_no_payload(change, reason):
    from backend.simulator.engine import step
    data = scenario_data(); data.update(change)
    if reason == "ENERGY_RESERVE":
        data["health_observations"][0].update(soc_est=0.0255, soc_lower=0.0255, energy_lower_Wh=0.51)
    result = step(create_state(data), send_action(), 2.0)
    assert not any(e.event_type == "sent" for e in result.events)
    assert any(e.reason_code == reason for e in result.events)


def test_optimistic_health_does_not_use_hidden_energy_as_oracle_guard():
    from backend.simulator.engine import step
    data = scenario_data(); data["initial_energy_Wh"] = 0.001
    result = step(create_state(data), send_action(), 2.0)
    assert any(e.event_type == "sent" for e in result.events)
    assert any(row.entry.lower_violation for row in result.next_state.energy_ledger)


@pytest.mark.parametrize("dt", [0.0, -1.0, float("inf"), float("nan"), True, 10**1000])
def test_step_rejects_invalid_time_without_mutating_state(dt):
    from backend.simulator.engine import step
    state = create_state()
    with pytest.raises(ValueError):
        step(state, idle_action(), dt)
    assert state.sim_time_s == 0.0 and state.energy_Wh == 10.0 and state.next_event_id == 1


def test_step_rejects_positive_dt_that_cannot_advance_floating_clock():
    from backend.simulator.engine import step
    state = step(create_state(), idle_action(), 100.0).next_state
    with pytest.raises(ValueError):
        step(state, idle_action(), 1e-320)
    assert state.sim_time_s == 100.0


def test_segment_end_cannot_emit_future_snapshot_or_reveal_future_health():
    from backend.simulator.engine import step
    data = scenario_data()
    future = copy.deepcopy(data["health_observations"][0])
    future.update(observed_at_s=2.4, available_at_s=2.4000000000000004,
                  soc_est=0.9, soc_lower=0.8, energy_lower_Wh=16.0)
    data["health_observations"].append(future)
    state = step(create_state(data), idle_action(), 0.3).next_state
    result = step(state, send_action(), 2.1)
    assert all(event.sim_time_s <= result.next_state.sim_time_s for event in result.events)
    assert result.next_state.energy_ledger[-1].end_s == result.next_state.sim_time_s
    snapshots = [e.data for e in result.events if e.event_type == "snapshot"]
    assert all(snapshot.soc_est == 0.5 for snapshot in snapshots)


def test_instances_observations_and_next_state_are_isolated():
    from backend.simulator.engine import observe, step
    data = scenario_data(); left = create_state(data); right = create_state(data)
    data["tasks"][0]["remaining_bytes"] = 0
    observed = observe(left); observed.tasks[0].remaining_bytes = 0
    assert observe(left).tasks[0].remaining_bytes == 1024
    next_left = step(left, idle_action(), 10.0).next_state
    assert next_left.energy_Wh < left.energy_Wh
    assert left.energy_Wh == right.energy_Wh == 10.0


def test_expired_queued_task_is_removed_but_expired_inflight_metadata_is_observable():
    from backend.simulator.engine import observe, step
    data = scenario_data(); data["tasks"][0]["deadline_s"] = 3.0
    idle = step(create_state(data), idle_action(), 4.0)
    assert observe(idle.next_state).tasks == []
    assert any(e.event_type == "dropped" for e in idle.events)
    sent = step(create_state(data), send_action(), 2.0)
    later = step(sent.next_state, idle_action(), 2.0)
    obs = observe(later.next_state)
    assert obs.inflight is not None and obs.tasks[0].task_id == obs.inflight.task_id


@pytest.mark.parametrize("change", ["non_synthetic", "lossy", "duplicate_task", "mixed_forecast", "missing_initial_health"])
def test_scenario_rejects_unsupported_or_ambiguous_inputs(change):
    data = scenario_data()
    if change == "non_synthetic": data["source"] = "measured"
    elif change == "lossy": data["true_windows"][0]["loss_profile"][0]["robust_loss_prob"] = 0.1
    elif change == "duplicate_task": data["tasks"].append(copy.deepcopy(data["tasks"][0]))
    elif change == "mixed_forecast": data["forecast_windows"][0]["forecast_version"] = "other"
    else: data["health_observations"][0].update(observed_at_s=5.0, available_at_s=5.0)
    with pytest.raises(ValueError): create_state(data)


def test_example_config_and_event_export_are_reproducible(tmp_path):
    from backend.contracts import Event
    from backend.simulator.engine import load_scenario, export_demo
    config = load_scenario(Path("configs/scenarios/minimal.json"))
    left, right = tmp_path / "first", tmp_path / "second"
    export_demo(config, left); export_demo(config, right)
    assert (left / "events.jsonl").read_bytes() == (right / "events.jsonl").read_bytes()
    events = [Event.model_validate_json(line) for line in (left / "events.jsonl").read_text().splitlines()]
    assert any(e.event_type == "sent" for e in events)
    assert all(e.run_id == "r2_minimal_validation" and e.policy_id == "manual" for e in events)
    assert [e.event_id for e in events] == list(range(1, len(events) + 1))
    assert not (left / "results.json").exists()
    manifest = json.loads((left / "manifest.json").read_text())
    assert manifest["protocol_stage"] == "send_only_ack_pending"
    with pytest.raises(ValueError): export_demo(config, left)
