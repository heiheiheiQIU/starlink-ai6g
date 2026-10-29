"""R2 deterministic synthetic checks, not satellite measurements or policy results."""

import copy

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
