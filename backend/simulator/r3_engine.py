"""Event-boundary integration for opt-in R3 synthetic protocol validation."""
import copy

from backend.contracts import Action, Event, InFlight, SnapshotData, StepResult, WindowChangedData
from .energy import advance_energy, finite_number
from .link import transmission_time
from .protocol import Pending


def protocol_step(state, action: Action, dt_s: float) -> StepResult:
    # Import locally: the public engine owns config/state and dispatches here.
    from .engine import observe, TimedEnergy
    dt = finite_number(dt_s, 'dt_s', positive=True)
    end = finite_number(state.sim_time_s + dt, 'step end')
    if end <= state.sim_time_s:
        raise ValueError('dt_s cannot advance floating clock')
    command = Action.model_validate(action)
    s = copy.deepcopy(state)
    cfg, protocol, events = s.config, s.protocol_state, []
    params = cfg.protocol

    def emit(t, kind, *, task=None, block=None, payload=0, overhead=0, energy=0.0, reason=None, data=None):
        events.append(Event(event_id=1, run_id=s.run_id, policy_id=s.policy_id, sim_time_s=t,
            event_type=kind, task_id=task, block_id=block, payload_bytes=payload,
            overhead_bytes=overhead, energy_Wh=energy, reason_code=reason, data=data))

    def process(now):
        due = [p for p in protocol.pending if p.time_s <= now]
        protocol.pending = [p for p in protocol.pending if p.time_s > now]
        order = {'received': 0, 'acked': 1, 'timeout': 2}
        for p in sorted(due, key=lambda p: (p.time_s, order[p.kind])):
            key = (p.task_id, p.block_id)
            if p.kind == 'received':
                duplicate = key in protocol.gateway
                protocol.gateway.add(key)
                emit(p.time_s, 'received', task=p.task_id, block=p.block_id,
                     payload=p.payload_bytes, reason='DUPLICATE_BLOCK' if duplicate else None)
            elif p.kind == 'acked':
                if not p.valid_ack:
                    emit(p.time_s, 'dropped', task=p.task_id, block=p.block_id, overhead=16,
                         reason='ACK_LOST_WINDOW_CLOSED')
                elif key not in protocol.confirmed:
                    protocol.confirmed.add(key)
                    task = next(t for t in s.tasks if t.task_id == p.task_id)
                    task.remaining_bytes -= p.payload_bytes
                    if s.inflight is not None and (s.inflight.task_id, s.inflight.block_id) == key:
                        s.inflight = None
                    emit(p.time_s, 'acked', task=p.task_id, block=p.block_id, overhead=16)
                else:
                    emit(p.time_s, 'acked', task=p.task_id, block=p.block_id, overhead=16,
                         reason='DUPLICATE_ACK')
            elif (s.inflight is not None and (s.inflight.task_id, s.inflight.block_id) == key
                  and protocol.attempts[key] == p.attempt):
                s.inflight = None
                emit(p.time_s, 'fallback', task=p.task_id, block=p.block_id, reason='ACK_TIMEOUT')
        for task in s.tasks:
            if task.arrival_s <= now and task.task_id not in s.announced:
                s.announced.add(task.task_id)
                emit(task.arrival_s, 'arrived', task=task.task_id, payload=task.payload_bytes)
            if task.deadline_s < now and task.remaining_bytes and task.task_id not in s.expired:
                s.expired.add(task.task_id)
                emit(now, 'dropped', task=task.task_id, payload=task.remaining_bytes, reason='DEADLINE_EXPIRED')

    process(s.sim_time_s)
    start = s.sim_time_s
    obs = observe(s)
    tx_end, tx_power, reason = start, 0.0, None
    selected = next((t for t in obs.tasks if t.task_id == command.task_id and t.deadline_s >= start), None)
    if command.mode != 'idle':
        if s.inflight is not None:
            reason = 'INFLIGHT_BLOCK'
        elif selected is None:
            reason = 'TASK_NOT_AVAILABLE'
        elif command.scheduled_bytes != min(1024, selected.remaining_bytes):
            reason = 'INVALID_BLOCK_SIZE'
        elif not any(w.start_s <= start < w.end_s for w in cfg.true_windows):
            reason = 'NO_VISIBLE_WINDOW'
        else:
            air = transmission_time(cfg.true_windows, start, command.mode, command.scheduled_bytes+32, dt)
            power = getattr(cfg.tx_power_W, command.mode)
            if air is None:
                reason = 'INSUFFICIENT_LINK_TIME'
            elif any(p.kind == 'acked' and ((start < p.ack_visible_end_s and start+air > p.ack_start_s)
                     or (start < p.rx_visible_end_s and start+air > p.rx_start_s))
                     for p in protocol.pending):
                reason = 'CONTROL_RESERVED'
            elif cfg.powers.base_W + cfg.powers.compute_W + power > cfg.max_power_W:
                reason = 'POWER_LIMIT'
            else:
                # Conservative observable lower bound, no physical energy oracle.
                projected = obs.health.energy_lower_Wh - ((cfg.powers.base_W+cfg.powers.compute_W)*dt
                            + power*air + params.ack_rx_W*(128/params.control_bps))/3600
                if projected < cfg.reserve_Wh:
                    reason = 'ENERGY_RESERVE'
                else:
                    tx_end = finite_number(start+air, 'send end')
                    receive = finite_number(tx_end+params.data_propagation_s, 'receive time')
                    ack = finite_number(receive+cfg.slot_s, 'ACK time')
                    timeout = finite_number(tx_end+2*cfg.slot_s, 'timeout')
                    control_end = ack-params.ack_propagation_s
                    control_start = control_end-128/params.control_bps
                    w = next((w for w in cfg.true_windows if w.start_s <= control_start < w.end_s), None)
                    valid = w is not None and ack < w.end_s
                    visible_end = min(control_end, w.end_s) if w is not None else control_start
                    rx_start = control_start+params.ack_propagation_s
                    rx_visible_end = min(ack,w.end_s) if w is not None else rx_start
                    block = (selected.payload_bytes-selected.remaining_bytes)//1024
                    key = (selected.task_id, block)
                    attempt = protocol.attempts.get(key, 0)+1
                    protocol.attempts[key] = attempt
                    s.inflight = InFlight(task_id=selected.task_id, block_id=block,
                        payload_bytes=command.scheduled_bytes, mode=command.mode,
                        sent_at_s=start, timeout_at_s=timeout, retries=attempt-1)
                    protocol.pending.extend([
                        Pending(receive, 'received', selected.task_id, block, command.scheduled_bytes, attempt),
                        Pending(ack, 'acked', selected.task_id, block, command.scheduled_bytes, attempt,
                                control_start, control_end, visible_end, valid,
                                rx_start, max(rx_start,rx_visible_end)),
                        Pending(timeout, 'timeout', selected.task_id, block, command.scheduled_bytes, attempt)])
                    tx_power = power
                    emit(start, 'sent', task=selected.task_id, block=block, payload=command.scheduled_bytes,
                         overhead=32, energy=power*air/3600)
        if reason:
            emit(start, 'fallback', task=command.task_id, reason=reason)

    boundaries = {end}
    boundaries.update(p.time_s for p in protocol.pending if start < p.time_s <= end)
    for p in protocol.pending:
        if p.kind == 'acked':
            boundaries.update(t for t in (p.ack_start_s, p.ack_visible_end_s,p.rx_start_s,p.rx_visible_end_s)
                              if start < t <= end)
    if start < tx_end <= end: boundaries.add(tx_end)
    boundaries.update(t.arrival_s for t in s.tasks if start < t.arrival_s <= end)
    # Equality at deadline is on time; expiration is checked at the next boundary.
    boundaries.update(t.deadline_s for t in s.tasks if start < t.deadline_s <= end)
    windows = [(t,w,visible) for w in cfg.true_windows for t,visible in ((w.start_s,True),(w.end_s,False))
               if start <= t <= end]
    boundaries.update(t for t,_,_ in windows if t > start)
    for t,w,visible in windows:
        # Open at zero once, boundaries at the next step's start were emitted before.
        if t > start or (t == 0 and state.next_event_id == 1):
            emit(t, 'window_changed', data=WindowChangedData(window_id=w.window_id, is_visible=visible))
    for target in sorted(boundaries):
        duration = target-s.sim_time_s
        if duration <= 0: continue
        rx = sum(params.ack_rx_W for p in protocol.pending if p.kind == 'acked'
                 and p.rx_start_s <= s.sim_time_s < p.rx_visible_end_s)
        tx = tx_power if s.sim_time_s < tx_end else 0.0
        row = advance_energy(s.energy_Wh, cfg.capacity_Wh, duration, cfg.powers, tx, rx)
        s.energy_ledger.append(TimedEnergy(s.sim_time_s, target, row))
        s.energy_Wh, s.sim_time_s = row.energy_after_Wh, target
        process(target)
        health = observe(s).health
        reasons = ['R3_FORECAST_BAND_UNAVAILABLE'] + (['ENERGY_BELOW_ZERO'] if row.lower_violation else [])
        snap = SnapshotData(soc_est=health.soc_est, energy_est_Wh=health.soc_est*health.capacity_Wh_est,
            energy_lower_Wh=health.energy_lower_Wh, queue_count=len(observe(s).tasks),
            forecast_energy_band=None, policy_version='manual-r3-v1', reason_codes=reasons,
            evaluation_truth=dict(label='posthoc_simulation', energy_true_Wh=row.energy_unclipped_Wh,
                soc_true=row.energy_unclipped_Wh/cfg.capacity_Wh, capacity_true_Wh=cfg.capacity_Wh))
        emit(target, 'snapshot', energy=row.background_Wh+row.compute_Wh+row.receive_Wh, data=snap)
    events.sort(key=lambda e: e.sim_time_s)
    for event in events:
        event.event_id = s.next_event_id; s.next_event_id += 1
    return StepResult(next_state=s, events=events)
