"""Energy-constrained EDF ranking; execution always passes the shared guard."""
from backend.contracts import CandidateScore, Observation


def score_actions(obs: Observation, *, config=None) -> list[CandidateScore]:
    observed=Observation.model_validate(obs)
    ordered=sorted(observed.tasks,key=lambda t:(t.deadline_s,t.task_id))
    return [CandidateScore(task_id=t.task_id,mode=mode,score=float(len(ordered)-index))
            for index,t in enumerate(ordered) for mode in ('robust','fast')] + [
                CandidateScore(task_id=None,mode='idle',score=0.0)]
