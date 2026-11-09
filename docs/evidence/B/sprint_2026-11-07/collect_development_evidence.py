"""One-off B evidence collection using existing Runner; never a formal batch."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import time

from backend.api.inference import inspect_model
from backend.cli import _hash
from backend.formal_inputs import verify_inputs
from backend.policies import edf, learned
from backend.policies.runner import run_policy
from backend.simulator.engine import create_state, observe

ROOT = Path.cwd()
OUT = ROOT/'runs/b_sprint_20261107/development'


def load(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def execute(name, config, policy, **kwargs):
    start = time.perf_counter()
    folder = OUT/name
    result = run_policy(config, folder, policy_id=policy, run_id='development_B_20261107_'+name, **kwargs)
    elapsed = time.perf_counter()-start
    events = [json.loads(line) for line in (folder/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    return dict(case=name, data_scope='development_fault_or_protocol_validation_not_formal',
                run_id=result['run_id'], policy_id=policy, input_hash=result['input_hash'], elapsed_s=elapsed,
                model_hash=result['model_hash'], files={p.name:sha(p) for p in folder.iterdir() if p.is_file()},
                notable_events=[e for e in events if e.get('reason_code') or e['event_type'] in ('sent', 'received', 'acked')])


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    cases=[]
    cases.append(execute('ack_loss', load(ROOT/'configs/scenarios/r3_ack_loss.json'), 'edf'))
    normal = load(ROOT/'configs/scenarios/r3_normal.json')
    package = OUT/'corrupt_model'; shutil.copytree(ROOT/'artifacts/models/a_n3_policy_v1', package)
    (package/'weights.npz').write_bytes(b'PK\x03\x04truncated-development-fault')
    cfg = load(ROOT/'configs/learned_policy.json'); cfg['package_dir']=str(package)
    cfg['weights_sha256']=sha(package/'weights.npz')
    cfg['model_version']='fault-injection-corrupt-npz'
    def bad_package(observation): return learned.score_actions(observation, config=cfg)
    cases.append(execute('corrupt_npz', normal, 'learned', inference_client=bad_package,
                         model_metadata=dict(model_hash=cfg['weights_sha256'], model_version=cfg['model_version'],
                                             feature_schema_version=cfg['feature_schema_version'])))
    low = load(ROOT/'configs/scenarios/r3_normal.json')
    low['scenario']['initial_energy_Wh']=.51
    health=low['scenario']['health_observations'][0]
    health.update(energy_lower_Wh=.51,soc_est=.51/20,soc_lower=.51/20)
    low['evaluation_end_s']=2.0
    def high_scores(observation):
        return [s.model_copy(update={'score':10.0 if s.task_id else 0.0}) for s in edf.score_actions(observation)]
    cases.append(execute('constraint_reject', low, 'learned', inference_client=high_scores,
                         model_metadata=dict(model_hash='0'*64, model_version='injected-high-score-probe-not-trained-AI')))
    timing=[]
    for policy in ('edf','value','learned'):
        start=time.perf_counter()
        result=run_policy(normal,OUT/('timing_'+policy),policy_id=policy,run_id='development_timing_'+policy)
        timing.append(dict(policy_id=policy,elapsed_s=time.perf_counter()-start,input_hash=result['input_hash']))
    save(OUT/'cases.json',dict(data_scope='development_only',cases=cases,timing=timing,
         caution='High-score case is an injected scoring probe, not a real trained-model decision; corrupt package bypass is only this local development callback.'))
    # Source review: same encoding for Scenario content, public Observation projection for old data.
    manifest_path=ROOT/'runs/formal_inputs_20261104/final_inputs/manifest.json'
    candidate=verify_inputs(manifest_path)
    old=[json.loads(line) for line in (ROOT/'data/teacher/sources/a_n3_20_v2.jsonl').read_text(encoding='utf-8').splitlines()]
    pilot=[json.loads(line) for line in (ROOT/'data/teacher/a_n4_pilot_v1/sources.jsonl').read_text(encoding='utf-8').splitlines()]
    def scene_digest(scene):
        scene=json.loads(json.dumps(scene));scene.pop('scenario_id',None)
        if scene.get('channel'): scene['channel'].pop('seed',None)
        return _hash(scene)
    def observation_digest(obs):
        obj=dict(obs)
        for key in ('run_id','policy_id','forecast_version'):obj.pop(key,None)
        return _hash(obj)
    old_obs={observation_digest(r['observation']) for r in old}
    pilot_content={scene_digest(r['scenario']) for r in pilot}
    collisions=[]
    for row in candidate['trajectories']:
        config=load(manifest_path.parent/row['config_path']);scene=config['scenario']
        if scene_digest(scene) in pilot_content:collisions.append({'trajectory':row['trajectory_id'],'type':'pilot_scenario'})
        visible=observe(create_state(scene)).model_dump(mode='json')
        if observation_digest(visible) in old_obs:collisions.append({'trajectory':row['trajectory_id'],'type':'old_observation'})
    files=['data/teacher/sources/a_n3_20_v2.jsonl','data/teacher/a_n3_20_v2/manifest.json',
           'data/teacher/a_n4_pilot_v1/sources.jsonl','data/teacher/a_n4_pilot_v1/source_splits.json',
           'data/teacher/a_n4_pilot_v1/manifest.json','docs/evidence/A/A_N4b_pilot_2026-11-04/audit.json',
           'experiments/test_matrix.json']
    save(OUT/'source_review.json',dict(status='B_checked_pending_A_C_review',candidate_manifest_sha256=sha(manifest_path),
        old_source_observations=len(old),pilot_sources=len(pilot),formal_trajectories=180,
        excluded_seeds=list(range(10000,10180))+[r['seed'] for r in pilot],
        pilot_content_hashes=sorted(pilot_content),collisions=collisions,source_files={p:sha(ROOT/p) for p in files},
        method='Scenario JSON normalized with backend.cli._hash after removing scenario_id and channel.seed; old Observation separately projected and compared at initial state. Semantic difference also checked: old/pilot zero-loss forecasts vs all formal nonzero loss.',
        limitations=['Old 20-source observations lack full scenario seeds; cannot claim namespace proof from observation hashes alone.',
                     'formal_v1_cell_00_trace_00 used by software integration tests before production freeze; no model/input/statistical tuning from its outcomes. A/C must decide continued eligibility or a new versioned holdout.'],
        exposed_candidate_trajectories=['formal_v1_cell_00_trace_00']))
    print(json.dumps({'cases':len(cases),'timing':timing,'source_collisions':collisions},ensure_ascii=False))


if __name__=='__main__':main()
