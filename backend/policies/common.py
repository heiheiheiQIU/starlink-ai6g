"""Shared public resource assumptions, independent of environment truth."""
from dataclasses import dataclass
from pathlib import Path
import math
from pydantic import Field
from backend.contracts import (Action, ConstraintCheck, ContractModel, NonNegativeFloat,
                               Observation, PositiveFloat, Task)
from backend.simulator.link import transmission_time
from backend.simulator.protocol import ProtocolConfig


class ModePower(ContractModel):
    robust: NonNegativeFloat = 36.0
    fast: NonNegativeFloat = 72.0


class PolicyConfig(ContractModel):
    decision_dt_s: PositiveFloat = 2.0
    slot_s: PositiveFloat = 1.0
    base_W: NonNegativeFloat = 36.0
    compute_W: NonNegativeFloat = 0.0
    solar_W: NonNegativeFloat = 0.0
    max_power_W: PositiveFloat = 150.0
    reserve_Wh: NonNegativeFloat = 0.5
    tx_power_W: ModePower = Field(default_factory=ModePower)
    protocol: ProtocolConfig = Field(default_factory=lambda: ProtocolConfig(
        data_propagation_s=0.0,ack_propagation_s=0.0,control_bps=1024.0,ack_rx_W=8.0))


def settings(config=None) -> PolicyConfig:
    if config is None:
        path=Path(__file__).resolve().parents[2]/'configs/policy.json'
        return PolicyConfig.model_validate_json(path.read_text(encoding='utf-8'))
    return PolicyConfig.model_validate(config)


@dataclass
class CandidatePlan:
    action: Action
    feasible: bool
    airtime_s: float
    cost_Wh: float
    checks: list[ConstraintCheck]


def plan_candidate(obs: Observation, task: Task, mode: str, cfg: PolicyConfig) -> CandidatePlan:
    checks=[]
    def check(code, passed):
        checks.append(ConstraintCheck(code=code,passed=bool(passed),details={'task_id':task.task_id,'mode':mode}))
        return passed
    payload=min(1024,task.remaining_bytes)
    action=Action(task_id=task.task_id,mode=mode,scheduled_bytes=max(1,payload),reason_codes=[],fallback=False)
    def blocked(): return CandidatePlan(action,False,math.inf,math.inf,checks)
    if not check('TASK_NOT_AVAILABLE',task.arrival_s <= obs.sim_time_s <= task.deadline_s and payload > 0): return blocked()
    if not check('INFLIGHT_BLOCK',obs.inflight is None): return blocked()
    if not check('NO_VISIBLE_WINDOW',any(w.start_s <= obs.sim_time_s < w.end_s for w in obs.forecast_windows)): return blocked()
    air=transmission_time(obs.forecast_windows,obs.sim_time_s,mode,payload+32,cfg.decision_dt_s)
    if not check('INSUFFICIENT_LINK_TIME',air is not None): return blocked()
    if not check('DEADLINE_UNREACHABLE',obs.sim_time_s+air+cfg.protocol.data_propagation_s <= task.deadline_s): return blocked()
    tx=getattr(cfg.tx_power_W,mode)
    base=cfg.base_W+cfg.compute_W
    if not check('POWER_LIMIT',base+max(tx,cfg.protocol.ack_rx_W) <= cfg.max_power_W): return blocked()
    ack_air=128/cfg.protocol.control_bps
    if not check('CONTROL_BUDGET',ack_air+cfg.protocol.ack_propagation_s <= cfg.slot_s): return blocked()
    horizon=max(cfg.decision_dt_s,air+cfg.protocol.data_propagation_s+cfg.slot_s)
    # No credit for future solar input: conservative below the public nominal profile.
    cost=(base*horizon+tx*air+cfg.protocol.ack_rx_W*ack_air)/3600
    if not check('ENERGY_RESERVE',math.isfinite(cost) and obs.health.energy_lower_Wh-cost >= cfg.reserve_Wh): return blocked()
    return CandidatePlan(action,True,air,cost,checks)
