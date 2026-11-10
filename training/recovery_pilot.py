"""Versioned development-only pilot; do not alter the frozen A-N4b or formal runs."""
import argparse
import copy
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
import zipfile

from backend.simulator.engine import ScenarioConfig, create_state, observe
from training.generate_policy_pilot import sample_source, label_state, _check_record
from training.pilot_scenarios import ROOT, IDLE, _source, _window, build_source_splits, canonical_json, sha256_json

VERSION = 'b-recovery-dev-v1'
FAMILIES = ('wait_then_send','last_chance','task_conflict','must_wait')


def build_sources():
    rows = []
    for index in range(30):
        family, variant = FAMILIES[index % 4], index//4
        tasks = [dict(task_id='T00',arrival_s=0.0,deadline_s=4.0,payload_bytes=1024,
                      remaining_bytes=1024,priority_weight=1+.13*variant,business_class='synthetic',data_location='satellite_1')]
        windows = [_window('W0',0.,4.)]
        energy = 6.+.17*variant
        if family == 'last_chance':
            windows = [_window('W0',0.,2.)]
        elif family == 'task_conflict':
            # Only one of two equal-duration tasks fits the final opportunity.
            tasks.append(dict(tasks[0],task_id='T01',priority_weight=2.+.19*variant))
        elif family == 'must_wait':
            if variant % 2 == 0:
                energy = .5
            else:
                windows = []
        source = _source(f'recovery_{index:02d}',710000+index,family,energy_wh=energy,tasks=tasks,windows=windows,partial=False)
        scenario = source['scenario']
        scenario['forecast_version'] = VERSION
        for window in scenario['true_windows']+scenario['forecast_windows']:
            window['forecast_version'] = VERSION
        scenario['health_observations'][0]['model_version'] = 'synthetic-'+VERSION
        scenario['channel'] = dict(version='time-indexed-sha256-v1',seed=source['seed'],step_s=.25,ack_loss_prob=0.)
        source['scenario'] = ScenarioConfig.model_validate(scenario).model_dump(mode='json')
        source['evolution_steps'] = [dict(dt_s=2.,action=copy.deepcopy(IDLE))]
        source['capture_after_steps'] = [0,1]
        identity = copy.deepcopy(source['scenario'])
        identity.pop('scenario_id')
        identity['channel'].pop('seed')
        source['content_sha256'] = sha256_json(identity)
        rows.append(source)
    return rows


def make_splits(sources):
    manifest = build_source_splits(sources,split_seed=20261110,counts=(18,6,6))
    return {source:split for split,ids in manifest['splits'].items() for source in ids}


def classify(row):
    if not row.get('label_eligible'):
        return 'ineligible'
    scores = row['candidate_scores']
    idle = next(s['score'] for s in scores if s['mode']=='idle')
    sends = [s['score'] for s in scores if s['mode']!='idle' and s['feasible']]
    if not sends: return 'no_feasible_send'
    difference = max(sends)-idle
    return 'send_strictly_better' if difference>1e-9 else 'wait_strictly_better' if difference < -1e-9 else 'tied'


def check_disjoint(sources, prior):
    for field in ('seed','content_sha256'):
        values = {s.get(field) for s in sources}-{None}
        if len(values) != len(sources) or values & ({s.get(field) for s in prior}-{None}):
            raise ValueError('source overlap: '+field)


def semantic_observation(payload):
    # Remove identity-only provenance; retain all physical/public values.
    value = copy.deepcopy(payload)
    for key in ('run_id','policy_id','forecast_version'):
        value.pop(key,None)
    if 'health' in value:
        for key in ('model_version','uncertainty_method'):
            value['health'].pop(key,None)
    for window in value.get('forecast_windows',[]):
        window.pop('forecast_version',None)
        window.pop('window_id',None)
    for task in value.get('tasks',[]):
        for key in ('task_id','business_class','data_location'):
            task.pop(key,None)
    return sha256_json(value)


def generate(output):
    if output.exists(): raise ValueError('Use a fresh output directory')
    config_path = ROOT/'configs/recovery_pilot.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    for key, expected in dict(dataset_version=VERSION,training_enabled=False,source_count=30,seed_start=710000,source_split_counts={'train':18,'validation':6,'test':6},states_per_source=2).items():
        if config.get(key) != expected:
            raise ValueError('Unsupported pilot configuration: '+key)
    teacher_path = ROOT/'configs/teacher.json'
    teacher = json.loads(teacher_path.read_text(encoding='utf-8'))
    teacher_sha = hashlib.sha256(teacher_path.read_bytes()).hexdigest()
    sources = build_sources()
    splits = make_splits(sources)
    prior_sources, prior_observations, evidence = [], set(), {}
    # Collect every original dataset and the full registered formal inputs.
    files = sorted((ROOT/'data/teacher').rglob('*.jsonl'))
    candidate_manifest = ROOT/'docs/evidence/B/formal_v2_candidate_2026-11-09/candidate/manifest.json'
    evidence[candidate_manifest.relative_to(ROOT).as_posix()] = hashlib.sha256(candidate_manifest.read_bytes()).hexdigest()
    formal_package = ROOT/'docs/evidence/B/delegated_execution_2026-11-10/formal_v2_delegated_results_20261110.zip'
    evidence[formal_package.relative_to(ROOT).as_posix()] = hashlib.sha256(formal_package.read_bytes()).hexdigest()
    with zipfile.ZipFile(formal_package) as package:
        for row in json.loads(candidate_manifest.read_text(encoding='utf-8'))['trajectories']:
            raw = package.read('frozen/candidate/'+row['config_path'])
            if hashlib.sha256(raw).hexdigest()!=row['config_sha256']:
                raise ValueError('Formal exclusion input hash mismatch')
            old_config = json.loads(raw)
            prior_observations.add(semantic_observation(observe(create_state(old_config['scenario'])).model_dump(mode='json')))
            prior_sources.append(dict(seed=row['seed'],content_sha256=row['content_hash']))
    prior_sources.extend(dict(seed=s) for start,end in [(10000,10180),(200000,200180),(410000,410030),(600000,600180)] for s in range(start,end))
    for path in files:
        evidence[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        for line in path.read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            prior_sources.append(row)
            if isinstance(row.get('scenario'),dict):
                prior_observations.add(semantic_observation(observe(create_state(row['scenario'])).model_dump(mode='json')))
            if isinstance(row.get('observation'),dict):
                prior_observations.add(semantic_observation(row['observation']))
    check_disjoint(sources,prior_sources)
    attempts, failures, seen_ids, seen_hashes, projected = [], [], set(), set(), set()
    started = time.perf_counter()
    output.mkdir(parents=True)
    for source in sources:
        try:
            records = sample_source(source)
            for record in records:
                _check_record(record,source,seen_ids,seen_hashes)
                projected_hash = semantic_observation(record['observation'])
                if projected_hash in prior_observations or projected_hash in projected:
                    raise ValueError('observation overlap')
                projected.add(projected_hash)
                record['split'] = splits[source['source_id']]
                try:
                    label = label_state(record,teacher_config=teacher,teacher_config_sha256=teacher_sha,budget_ms=config['teacher_budget_ms'])
                    label['dataset_version'] = VERSION
                except Exception as error:
                    label = dict(record,label_eligible=False,solver_status='ERROR',gap=None,error=f'{type(error).__name__}: {error}')
                label['decision_class'] = classify(label)
                label.pop('label_content_sha256',None)
                label['label_content_sha256'] = sha256_json({k:v for k,v in label.items() if k!='elapsed_ms'})
                attempts.append(label)
        except Exception as error:
            failures.append(dict(source_id=source['source_id'],error=f'{type(error).__name__}: {error}'))
    eligible = [s for s in attempts if s['label_eligible']]
    counts = Counter(s['decision_class'] for s in attempts)
    ready = len(eligible)==60 and not failures and counts['send_strictly_better']>=config['minimum_send_better_states'] and counts['no_feasible_send']>=config['minimum_no_feasible_states']
    summary = dict(dataset_version=VERSION,status='ready_for_A_label_review' if ready else 'blocked',training_enabled=False,
                   sources=len(sources),states=len(attempts),eligible=len(eligible),ineligible=len(attempts)-len(eligible),
                   source_split_counts=dict(Counter(splits.values())),state_split_counts=dict(Counter(s['split'] for s in attempts)),
                   family_counts=dict(Counter(s['family'] for s in sources)),decision_counts=dict(counts),
                   solver_status_counts=dict(Counter(s['solver_status'] for s in attempts)),
                   family_decision_counts={f:dict(Counter(s['decision_class'] for s in attempts if s['family']==f)) for f in FAMILIES},
                   failures=failures,wall_seconds=time.perf_counter()-started,formal_results_reused=False)
    leakage = dict(status='passed' if not failures else 'failed',seed_overlap=0,source_content_overlap=0,
                   semantic_observation_overlap=0,prior_observations=len(prior_observations),
                   exclusion_evidence=evidence,excluded_seed_ranges_inclusive=[[10000,10179],[200000,200179],[410000,410029],[600000,600179]],
                   scope='all repository teacher JSONL public observations, all 30 old pilot initial observations, 180 hash-verified formal initial observations and excluded seed ranges')
    def write(name,value):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name,rows in [('sources.jsonl',sources),('attempts.jsonl',attempts),('samples.jsonl',eligible),('diagnostics.jsonl',[s for s in attempts if not s['label_eligible']])]:
        (output/name).write_text(''.join(canonical_json(row)+'\n' for row in rows),encoding='utf-8')
    write('source_splits.json',dict(dataset_version=VERSION,split_seed=20261110,by_source=splits))
    write('summary.json',summary)
    write('leakage.json',leakage)
    write('config.json',config)
    write('teacher_config.json',teacher)
    manifest = dict(dataset_version=VERSION,training_enabled=False,teacher_config_sha256=teacher_sha,
                    code_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'training/generate_policy_pilot.py',ROOT/'training/pilot_scenarios.py',ROOT/'backend/contracts.py',*sorted((ROOT/'backend/simulator').glob('*.py')),*sorted((ROOT/'backend/policies').glob('*.py'))]},
                    output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())})
    write('manifest.json',manifest)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    raise SystemExit(0 if generate(args.output)['status']=='ready_for_A_label_review' else 1)
