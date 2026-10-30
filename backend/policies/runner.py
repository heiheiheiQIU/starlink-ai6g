"""Bounded callback gateway and single-policy autonomous rule validation."""
import copy
from queue import Queue, Empty
from threading import Thread
from time import perf_counter
from backend.contracts import Event, Observation, WindowChangedData
from backend.simulator.energy import finite_number
from .common import PolicyConfig, settings
from .guard import decode_safe, fallback_decision


class ScorerGateway:
    """At most one daemon callback per gateway; timed-out results are never reused.

    This bounds caller wait and concurrent callback count, not callback CPU use.
    Process isolation for persistent API workers belongs to the API stage.
    """
    def __init__(self, scorer, *, config=None, budget_ms=100.0):
        self.scorer=scorer; self.config=settings(config)
        self.budget_ms=finite_number(budget_ms,'budget_ms',positive=True)
        self.worker=None

    def decide(self, obs):
        start=perf_counter(); observed=Observation.model_validate(obs)
        reason=None; scores=None
        if self.scorer is None: reason='MODEL_UNAVAILABLE'
        elif self.worker is not None and self.worker.is_alive(): reason='MODEL_BUSY'
        else:
            out=Queue(maxsize=1)
            def work():
                try: out.put((True,self.scorer(observed.model_copy(deep=True))))
                except BaseException: out.put((False,None))
            self.worker=Thread(target=work,daemon=True);self.worker.start()
            try:
                success,scores=out.get(timeout=self.budget_ms/1000)
                if not success: reason='MODEL_UNAVAILABLE'
            except Empty: reason='MODEL_TIMEOUT'
        result=fallback_decision(observed,reason,config=self.config) if reason else decode_safe(observed,scores,config=self.config)
        return result.model_copy(update={'decision_latency_ms':(perf_counter()-start)*1000})


def policy_config(scenario, *, decision_dt_s=2.0):
    return PolicyConfig(decision_dt_s=decision_dt_s,slot_s=scenario.slot_s,
        base_W=scenario.powers.base_W,compute_W=scenario.powers.compute_W,solar_W=scenario.powers.solar_W,
        max_power_W=scenario.max_power_W,reserve_Wh=scenario.reserve_Wh,
        tx_power_W=scenario.tx_power_W.model_dump(),protocol=scenario.protocol)


def run_policy(config, output, *, policy_id='edf', run_id=None):
    from backend.cli import RunConfig, run_experiment
    from backend.simulator.engine import observe, step
    from . import edf, value
    modules={'edf':edf,'value':value}
    if policy_id not in modules: raise ValueError('Supported rule policies: edf, value')
    parsed=RunConfig.model_validate(config)
    cfg=policy_config(parsed.scenario)

    def execute(state,horizon):
        events=[]
        retry_key=None  # Controller memory derived only from public protocol events.
        def record(event):
            events.append(event); state.next_event_id+=1
        # Initial environmental arrivals/window changes precede the first decision.
        for task in state.tasks:
            if task.arrival_s==0:
                record(Event(event_id=state.next_event_id,run_id=state.run_id,policy_id=policy_id,
                    sim_time_s=0.0,event_type='arrived',task_id=task.task_id,block_id=None,
                    payload_bytes=task.payload_bytes,overhead_bytes=0,energy_Wh=0.0,reason_code=None,data=None))
                state.announced.add(task.task_id)
        for window in state.config.true_windows:
            if window.start_s==0:
                record(Event(event_id=state.next_event_id,run_id=state.run_id,policy_id=policy_id,
                    sim_time_s=0.0,event_type='window_changed',task_id=None,block_id=None,
                    payload_bytes=0,overhead_bytes=0,energy_Wh=0.0,reason_code=None,
                    data=WindowChangedData(window_id=window.window_id,is_visible=True)))
        gateway=ScorerGateway(lambda observed: modules[policy_id].score_actions(observed,config=cfg),config=cfg)
        while state.sim_time_s < horizon:
            end=min(state.sim_time_s+cfg.decision_dt_s,horizon)
            gateway.config=cfg.model_copy(update={'decision_dt_s':end-state.sim_time_s})
            started=perf_counter()
            visible=observe(state)
            decision=gateway.decide(visible)
            if retry_key is not None:
                # Keep the complete candidate set, but rank only the required block above idle.
                # Task/block identity is inferred from public remaining bytes and ACK events.
                retry_scores=[row.model_copy(update={'score':(
                    1.0 if row.task_id==retry_key[0] and any(
                        t.task_id==row.task_id and (t.payload_bytes-t.remaining_bytes)//1024==retry_key[1]
                        for t in visible.tasks) else (0.0 if row.mode=='idle' else -1.0))})
                    for row in decision.candidate_scores]
                decoded=decode_safe(visible,retry_scores,config=gateway.config)
                action=decoded.action.model_copy(update={
                    'fallback':decision.fallback,
                    'reason_codes':list(dict.fromkeys([*decision.action.reason_codes,*decoded.action.reason_codes,'RETRY_REQUIRED']))})
                decision=decoded.model_copy(update={'action':action,'fallback':decision.fallback})
            decision=decision.model_copy(update={'decision_latency_ms':(perf_counter()-started)*1000})
            decision=decision.model_copy(update={'policy_version':policy_id+'-r4-v1'})
            record(Event(event_id=state.next_event_id,run_id=state.run_id,policy_id=policy_id,
                sim_time_s=state.sim_time_s,event_type='decision',task_id=decision.action.task_id,
                block_id=None,payload_bytes=0,overhead_bytes=0,energy_Wh=0.0,
                reason_code=decision.action.reason_codes[0] if decision.fallback else None,data=decision.to_event_data()))
            result=step(state,decision.action,end-state.sim_time_s)
            state=result.next_state
            for event in result.events:
                key=(event.task_id,event.block_id)
                if event.reason_code=='ACK_TIMEOUT': retry_key=key
                elif key==retry_key and ((event.event_type=='acked' and event.reason_code is None)
                        or event.reason_code=='RETRY_RETIRED_EXPIRED'):
                    retry_key=None
                if event.event_type=='snapshot': event.data.policy_version=policy_id+'-r4-v1'
            events.extend(result.events)
        return state,events

    # Manual scripts have no effect on automatic policy runs; record that explicitly.
    parsed=parsed.model_copy(update={'kind':'rule_validation','actions':[]})
    return run_experiment(parsed,output,run_id=run_id,_policy_id=policy_id,_executor=execute,
        _runtime=dict(policy_id=policy_id,policy_version=policy_id+'-r4-v1',
                      public_policy_config=cfg.model_dump(),scoring_budget_ms=100.0))
