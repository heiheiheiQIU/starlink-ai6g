import copy
import pytest
from backend.contracts import ContractViolation, validate_teacher_result
from backend.policies.teacher import solve_teacher, TeacherConfig
from backend.policies.common import PolicyConfig
from tests.test_policies import obs
from tests.test_protocol import config


def score(result,task,mode): return next(s for s in result.candidate_scores if (s.task_id,s.mode)==(task,mode))


def test_exact_short_deadline_conflict_full_task_rewards_and_scale():
    data=config(deadline=1.0)
    # Only fast fits the first task's deadline; two complete tasks can be received by t4.
    data['tasks'][0]['priority_weight']=2.0
    t=copy.deepcopy(data['tasks'][0]);t.update(task_id='T2',deadline_s=4.0,priority_weight=1.0)
    data['tasks'].append(t)
    result=solve_teacher(obs(data),1000)
    assert result.solver_status=='OPTIMAL' and result.gap==0.0
    assert score(result,'T1','fast').score==pytest.approx(1.0)
    assert not score(result,'T1','robust').feasible
    assert score(result,None,'idle').score==pytest.approx(1/3)
    validate_teacher_result(obs(data),result)


def test_partial_task_not_counted_and_energy_shortage_is_explicit():
    data=config(payload=2500,deadline=2.0)
    result=solve_teacher(obs(data),1000)
    assert all(c.score==0.0 for c in result.candidate_scores)
    data=config(deadline=2.0)
    data['health_observations'][0].update(soc_est=0.01,soc_lower=0.01,energy_lower_Wh=0.2)
    result=solve_teacher(obs(data),1000)
    assert result.solver_status=='OPTIMAL'
    assert [c.mode for c in result.candidate_scores if c.feasible]==['idle']


def test_idle_first_can_be_valuable_and_empty_queue_valid():
    from tests.test_simulator import window
    data=config(deadline=4.0);data['forecast_windows']=[window(2.0,6.0).model_dump()]
    result=solve_teacher(obs(data),1000)
    assert result.solver_status=='OPTIMAL' and score(result,None,'idle').score==1.0
    assert not any(c.feasible for c in result.candidate_scores if c.mode!='idle')
    data['tasks']=[]
    result=solve_teacher(obs(data),1000)
    assert len(result.candidate_scores)==1 and result.solver_status=='OPTIMAL'


def test_timeout_and_unsupported_never_claim_optimal(monkeypatch):
    import backend.policies.teacher as module
    clock=[0.0]
    def advancing(): clock[0]+=0.01;return clock[0]
    monkeypatch.setattr(module,'_clock',advancing)
    result=solve_teacher(obs(config(deadline=4.0)),1)
    assert result.solver_status=='TIME_LIMIT_FEASIBLE' and result.gap is not None and result.gap>0
    assert all(0<=c.score<=1 for c in result.candidate_scores)
    data=config();data['forecast_windows'][0]['loss_profile'][0]['fast_loss_prob']=0.1
    result=solve_teacher(obs(data),1000)
    assert result.solver_status=='UNSUPPORTED_LOSS' and result.gap is None


@pytest.mark.parametrize('budget',[0,-1,True,1.5,100000])
def test_invalid_budget_controlled(budget):
    with pytest.raises(ContractViolation): solve_teacher(obs(),budget)


def test_input_unchanged_and_true_environment_not_used():
    data=config(deadline=4.0);data['true_windows']=[]
    observed=obs(data);before=observed.model_dump()
    left=solve_teacher(observed,1000);right=solve_teacher(observed,1000)
    assert left.solver_status==right.solver_status=='OPTIMAL'
    assert [c.model_dump() for c in left.candidate_scores]==[c.model_dump() for c in right.candidate_scores]
    assert observed.model_dump()==before
