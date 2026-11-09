"""B independent arithmetic, reserve probes and teacher support checks; no training."""
from pathlib import Path
import copy
import hashlib
import json
import math
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path.insert(0, str(ROOT))
from backend.contracts import Observation
from backend.policies.common import plan_candidate, settings
from backend.policies.teacher import solve_teacher
from backend.simulator.engine import create_state, observe, step
from tests.test_protocol import config, send


def main():
    output = Path(sys.argv[1]); output.mkdir(parents=True, exist_ok=False)
    rows = [json.loads(line) for line in (ROOT / 'data/teacher/a_n3_20_v2/samples.jsonl').read_text(encoding='utf-8').splitlines()]
    counts = dict(task_action_all_zero=0, idle_in_optimal_set=0, unique_non_idle_best=0,
                  tied_optimal_set=0, low_energy_at_or_below_reserve=0, no_forecast_window=0,
                  deadline_before_or_at_first_window=0, all_task_actions_infeasible=0)
    reserve = settings().reserve_Wh
    for row in rows:
        scores = row['candidate_scores']; feasible = [c for c in scores if c['feasible']]
        active = [c for c in scores if c['mode'] != 'idle']
        best = max(c['score'] for c in feasible)
        winners = [c for c in feasible if c['score'] == best]
        obs = row['observation']; windows = obs['forecast_windows']
        counts['task_action_all_zero'] += bool(active) and all(c['score'] == 0 for c in active)
        counts['idle_in_optimal_set'] += any(c['mode'] == 'idle' for c in winners)
        counts['unique_non_idle_best'] += len(winners) == 1 and winners[0]['mode'] != 'idle'
        counts['tied_optimal_set'] += len(winners) > 1
        counts['low_energy_at_or_below_reserve'] += obs['health']['energy_lower_Wh'] <= reserve
        counts['no_forecast_window'] += not windows
        counts['deadline_before_or_at_first_window'] += bool(windows) and any(t['deadline_s'] <= min(w['start_s'] for w in windows) for t in obs['tasks'])
        counts['all_task_actions_infeasible'] += bool(active) and not any(c['feasible'] for c in active)
    reference = json.loads((ROOT / 'docs/evidence/A/A_N4_dataset_audit_2026-11-03/audit.json').read_bytes())
    for key, value in counts.items():
        area = 'label_quality' if key in reference['label_quality'] else 'coverage'
        assert reference[area][key]['count'] == value, key

    public = observe(create_state(config(deadline=4.0)))
    cfg = settings()
    full = plan_candidate(public, public.tasks[0], 'robust', cfg)
    assert full.feasible
    threshold = reserve + full.cost_Wh
    probes = []
    for energy in (0.49, 0.5, 0.51, threshold - 1e-6, threshold, threshold + 1e-6):
        raw = public.model_dump()
        raw['health'].update(capacity_Wh_est=20.0, capacity_lower_Wh=20.0,
                             soc_est=energy / 20, soc_lower=energy / 20, energy_lower_Wh=energy)
        obs = Observation.model_validate(raw)
        plan = plan_candidate(obs, obs.tasks[0], 'robust', cfg)
        assert plan.feasible == (energy - full.cost_Wh >= reserve)
        result = solve_teacher(obs, 1000)
        assert result.solver_status == 'OPTIMAL'
        probes.append(dict(energy_lower_Wh=energy, robust_feasible=plan.feasible,
                           robust_cost_Wh=full.cost_Wh, projected_lower_Wh=energy-full.cost_Wh,
                           teacher_status=result.solver_status,
                           feasible_modes=[c.mode for c in result.candidate_scores if c.feasible]))

    cases = []
    def check(name, obs, expected):
        before = obs.model_dump()
        result = solve_teacher(obs, 1000)
        assert result.solver_status == expected, (name, result.solver_status)
        assert obs.model_dump() == before
        cases.append(dict(name=name, expected=expected, actual=result.solver_status,
                          gap=result.gap, candidates=[c.model_dump() for c in result.candidate_scores]))
    check('normal', public, 'OPTIMAL')
    raw = public.model_dump();raw['forecast_windows'] = []
    check('no_window', Observation.model_validate(raw), 'OPTIMAL')
    raw = public.model_dump()
    for w in raw['forecast_windows']:
        w['start_s'] = 6.0;w['end_s'] = 12.0
        for p in w['rate_profile'] + w['loss_profile']:p['time_s'] = 6.0
    check('deadline_before_window', Observation.model_validate(raw), 'OPTIMAL')
    raw = public.model_dump(); raw['forecast_windows'][0]['loss_profile'][0]['fast_loss_prob'] = 0.1
    check('nonzero_loss', Observation.model_validate(raw), 'UNSUPPORTED_LOSS')
    check('inflight', observe(step(create_state(config()), send(), 1.5).next_state), 'UNSUPPORTED_INFLIGHT')
    raw = public.model_dump();raw['tasks'][0]['payload_bytes'] = 2500;raw['tasks'][0]['remaining_bytes'] = 2000;raw['cache_bytes'] = 2000
    check('misaligned_partial', Observation.model_validate(raw), 'UNSUPPORTED_BLOCK_STATE')
    raw = public.model_dump();raw['tasks'] = [{**copy.deepcopy(raw['tasks'][0]), 'task_id': f'T{i}'} for i in range(13)];raw['cache_bytes'] = 13*1024
    check('too_many_tasks', Observation.model_validate(raw), 'UNSUPPORTED_TASK_COUNT')
    raw = public.model_dump();raw['tasks'][0]['deadline_s'] = 241
    check('too_long_horizon', Observation.model_validate(raw), 'UNSUPPORTED_HORIZON')
    raw = public.model_dump();raw['forecast_windows'] = [{**copy.deepcopy(raw['forecast_windows'][0]), 'window_id': f'W{i}'} for i in range(4)]
    check('too_many_windows', Observation.model_validate(raw), 'UNSUPPORTED_WINDOW_COUNT')
    raw = public.model_dump();raw['tasks'][0].update(payload_bytes=122881, remaining_bytes=122881);raw['cache_bytes'] = 122881
    check('oversized_history_payload', Observation.model_validate(raw), 'UNSUPPORTED_PAYLOAD_RANGE')
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
        'configs/teacher.json', 'configs/policy.json', 'backend/policies/teacher.py',
        'backend/policies/common.py', 'data/teacher/a_n3_20_v2/samples.jsonl',
        'data/teacher/a_n3_20_v2/splits.json', 'artifacts/models/a_n3_policy_v1/weights.npz')}
    record = dict(kind='B_independent_support_check_not_new_training_data', observation_count=len(rows),
                  independent_counts=counts, reserve_Wh=reserve, robust_start_threshold_Wh=threshold,
                  reserve_probes=probes, support_cases=cases, input_hashes=hashes)
    (output / 'verification.json').write_bytes((json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps(dict(counts=counts, reserve=reserve, threshold=threshold, probes=len(probes), support_cases=len(cases)), ensure_ascii=False))


if __name__ == '__main__':
    main()
