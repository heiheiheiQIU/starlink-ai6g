"""Capacity timing of initial synthetic observations; emits no training dataset."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter, process_time

root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(root))
from backend.simulator.engine import create_state, observe
from backend.policies.teacher import solve_teacher
from backend.contracts import validate_teacher_result

matrix_path = root / 'experiments/teacher_scale_probe_2026-10-31.json'
matrix = json.loads(matrix_path.read_bytes())
base = json.loads((root / 'configs/scenarios/r3_normal.json').read_bytes())['scenario']
records = []
for scene in matrix['scenes']:
    data = copy.deepcopy(base)
    data['scenario_id'] = scene['id']
    task = data['tasks'][0]
    data['tasks'] = [dict(task, task_id=f'T{i}', deadline_s=float(4+i%3),
                          priority_weight=float(1+i%3)) for i in range(scene['tasks'])]
    data['health_observations'][0]['energy_lower_Wh'] = scene['energy_lower_Wh']
    data['health_observations'][0]['soc_lower'] = min(0.45, scene['energy_lower_Wh']/20)
    for group in ('true_windows', 'forecast_windows'):
        data[group][0]['end_s'] = scene['window_s']
        data[group][0]['rate_profile'][0].update(robust_bps=scene['robust_bps'], fast_bps=scene['robust_bps']*2)
        loss = scene['forecast_loss'] if group == 'forecast_windows' else 0
        data[group][0]['loss_profile'][0].update(robust_loss_prob=loss, fast_loss_prob=loss)
    obs = observe(create_state(data, run_id=scene['id'], policy_id='teacher'))
    for repeat in range(matrix['repeats']):
        start, cpu = perf_counter(), process_time()
        result = solve_teacher(obs, matrix['budget_ms'])
        wall, cpu = perf_counter()-start, process_time()-cpu
        validate_teacher_result(obs, result)
        records.append(dict(scene=scene['id'], repeat=repeat, status=result.solver_status,
                            elapsed_ms=result.elapsed_ms, wall_seconds=wall, cpu_seconds=cpu,
                            eligible=result.solver_status=='OPTIMAL' and result.gap==0,
                            observation_sha256=hashlib.sha256(obs.model_dump_json().encode()).hexdigest()))
report = dict(kind=matrix['kind'], matrix_sha256=hashlib.sha256(matrix_path.read_bytes()).hexdigest(),
              teacher_sha256=hashlib.sha256((root/'backend/policies/teacher.py').read_bytes()).hexdigest(),
              source_kind='synthetic_initial_observation', training_rows_generated=0,
              records=records, total_cpu_seconds=sum(r['cpu_seconds'] for r in records),
              total_wall_seconds=sum(r['wall_seconds'] for r in records))
Path(sys.argv[1]).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(calls=len(records), total_wall_seconds=report['total_wall_seconds'],
                     statuses={status:sum(r['status']==status for r in records) for status in {r['status'] for r in records}})))
