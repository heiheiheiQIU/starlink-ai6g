"""Weight per predicted complete-task service time, never weight per sent block."""
import math
from backend.contracts import CandidateScore, Observation
from .common import settings


def score_actions(obs: Observation, *, config=None) -> list[CandidateScore]:
    observed=Observation.model_validate(obs); cfg=settings(config)
    result=[]
    current=next((w for w in observed.forecast_windows if w.start_s <= observed.sim_time_s < w.end_s),None)
    for task in observed.tasks:
        for mode in ('robust','fast'):
            point=max((p for p in current.rate_profile if p.time_s <= observed.sim_time_s),key=lambda p:p.time_s) if current else None
            rate=getattr(point,mode+'_bps') if point is not None else 0.0
            blocks=math.ceil(task.remaining_bytes/1024)
            cost=((task.remaining_bytes+32*blocks)*8/rate + blocks*(cfg.slot_s+cfg.protocol.data_propagation_s)) if rate else math.inf
            score=task.priority_weight/cost if cost > 0 else 0.0
            result.append(CandidateScore(task_id=task.task_id,mode=mode,score=score))
    return result+[CandidateScore(task_id=None,mode='idle',score=0.0)]
