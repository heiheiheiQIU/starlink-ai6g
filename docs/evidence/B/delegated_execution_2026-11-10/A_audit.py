"""Independent, user-delegated A-scope machine audit. Never runs a policy or trains.

Run with main checkout .venv/Scripts/python.exe; imports frozen revision only.
Writes this audit's JSON/log and, only on complete success, proposed_review/A.json.
"""
from pathlib import Path
import copy
from datetime import datetime, timezone, timedelta
import hashlib
import json
import subprocess
import sys
import traceback

MAIN = Path(__file__).resolve().parents[4]
FROZEN = MAIN.parent / 'formal-frozen-verification-20261109'
OUT = Path(__file__).resolve().parent
CANDIDATE = MAIN / 'docs/evidence/B/formal_v2_candidate_2026-11-09'
REVIEW = MAIN / 'docs/evidence/B/formal_v2_finalization_2026-11-10/proposed_review'
EXPECTED_REV = '48157a8f4a1cdd7770685b79deb3fe4524b1bf7d'
EXPECTED_LEAKAGE = 'e8da2be7968020eb9d1e974ae1cd5b46d3ca89ebec3fab466750bc4df7747018'
checks = []

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def pretty(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode('utf-8')

def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines() if line.strip()]

def check(name, condition, detail=None):
    checks.append(dict(name=name, passed=bool(condition), detail=detail))
    if not condition:
        raise AssertionError(name + ': ' + str(detail))

def content_key(scene):
    scene = copy.deepcopy(scene)
    scene.pop('scenario_id', None)
    if scene.get('channel'):
        scene['channel'].pop('seed', None)
    return digest(pretty(scene))

def projection(observation):
    return digest(pretty({k:v for k,v in observation.items() if k not in {'run_id','policy_id','forecast_version'}}))

def audit():
    revision = subprocess.run(['git','rev-parse','HEAD'], cwd=FROZEN, capture_output=True, text=True, check=True).stdout.strip()
    check('frozen_execution_revision', revision == EXPECTED_REV, revision)
    sys.path.insert(0, str(FROZEN))
    from backend.formal_freeze import freeze_binding
    from backend.formal_v2 import verify, MODEL, ANALYSIS, subject
    from backend.experiments import build_config
    from backend.simulator.engine import create_state, observe
    from training.pilot_scenarios import build_sources
    manifest = verify(CANDIDATE/'candidate/manifest.json')
    check('frozen_candidate_verify', True)
    binding = read(REVIEW/'binding.json')
    actual_binding = freeze_binding(CANDIDATE/'candidate/manifest.json', MODEL, ANALYSIS)
    check('full_frozen_code_model_statistics_candidate_binding', binding == actual_binding, actual_binding)
    check('candidate_manifest_expected_sha256', digest((CANDIDATE/'candidate/manifest.json').read_bytes()) == '2b0814db44b7c70cd94e44608e34c762ffaa86969ea6f955e4736b7b3cdcd31f')
    expected_subject = subject()
    for role in 'ABC':
        check('generation_receipt_subject_'+role, manifest['generation_receipts'][role]['subject'] == expected_subject)
    check('generation_source_code_aggregate', digest(pretty(binding['source_sha256'])) == expected_subject['code_sha256'])

    # Recompute all frozen code digests without source_hashes. The working main
    # checkout may have subsequent unrelated edits and is not the execution code.
    source_digests = {}
    for name, expected in binding['source_sha256'].items():
        actual = digest((FROZEN/name).read_text(encoding='utf-8-sig').encode('utf-8'))
        check('code_bytes_'+name, actual == expected)
        source_digests[name] = actual

    leakage = read(REVIEW/'leakage.json')
    draft = read(CANDIDATE/'review/leakage.json')
    expected_final = dict(draft, status='accepted')
    proposal = read(REVIEW.parent/'C_leakage_proposal.json')
    check('leakage_only_status_changed', leakage == expected_final)
    check('exact_final_leakage_bytes', (REVIEW/'leakage.json').read_bytes() == pretty(expected_final))
    check('exact_C_proposal_leakage_sha256', digest((REVIEW/'leakage.json').read_bytes()) == EXPECTED_LEAKAGE == proposal['proposed_final_leakage']['sha256'])
    for name, expected in leakage['source_files'].items():
        check('copied_leakage_source_'+name, digest((REVIEW/name).read_bytes()) == expected)
        check('frozen_leakage_source_'+name, (REVIEW/name).read_bytes() == (FROZEN/name.removeprefix('sources/')).read_bytes())
    for name, expected in expected_subject['source_inputs'].items():
        check('actual_source_binding_'+name, digest((FROZEN/name).read_bytes()) == expected)

    # Actual model training source: package summary -> samples -> source bytes.
    model_dir = FROZEN / read(MODEL)['package_dir']
    training = read(model_dir/'training_summary.json')
    samples_path = FROZEN/'data/teacher/a_n3_20_v2/samples.jsonl'
    split_path = samples_path.parent/'splits.json'
    split = read(split_path)
    samples = rows(samples_path)
    old_path = FROZEN/'data/teacher/sources/a_n3_20_v2.jsonl'
    old = rows(old_path)
    dataset_manifest = read(samples_path.parent/'manifest.json')
    check('training_summary_binds_actual_samples', training['samples_sha256'] == digest(samples_path.read_bytes()) == dataset_manifest['output_sha256']['samples.jsonl'])
    check('training_summary_binds_actual_split', training['split_sha256'] == digest(split_path.read_bytes()))
    check('dataset_binds_actual_legacy_source_bytes', dataset_manifest['source_sha256'] == digest(old_path.read_bytes()) == expected_subject['source_inputs']['data/teacher/sources/a_n3_20_v2.jsonl'])
    check('actual_legacy_sources_and_samples_20', len(old) == len(samples) == 20)
    by_id = {r['sample_id']:r for r in old}
    check('unique_legacy_source_ids', len(by_id) == 20)
    for row in samples:
        source = by_id[row['sample_id']]
        check('sample_source_identity_'+row['sample_id'], row['source_group_id'] == source['source_group_id'] and row['observation'] == source['observation'])
        normalized = {k:v for k,v in row['observation'].items() if k not in {'run_id','policy_id'}}
        check('sample_content_hash_'+row['sample_id'], row['observation_content_sha256'] == digest(compact(normalized)))
        check('eligible_teacher_sample_'+row['sample_id'], row['label_eligible'] is True and row['solver_status'] == 'OPTIMAL' and row['gap'] == 0.0)
    group_ids = {r['source_group_id'] for r in samples}
    ordered = sorted(group_ids, key=lambda x:(digest(f"{split['split_seed']}:{x}".encode()), x))
    check('A_N3_twenty_unique_groups', len(group_ids) == 20)
    offset = 0
    for name, count in [('train',12),('validation',4),('test',4)]:
        group_selection = ordered[offset:offset+count]
        selected = [r for r in samples if r['source_group_id'] in group_selection]
        actual = split['splits'][name]
        check('A_N3_recomputed_'+name, actual['source_group_ids'] == group_selection and actual['sample_count'] == count and actual['sample_ids'] == sorted(r['sample_id'] for r in selected) and actual['scenario_ids'] == sorted({r['scenario_id'] for r in selected}) and actual['observation_content_sha256'] == sorted(r['observation_content_sha256'] for r in selected))
        check('training_metrics_count_'+name, training['linear_baseline'][name]['observation_count'] == count)
        offset += count
    for left,right in [('train','validation'),('train','test'),('validation','test')]:
        for field in ['source_group_ids','scenario_ids','sample_ids','observation_content_sha256']:
            check('A_N3_no_overlap_'+left+'_'+right+'_'+field, not (set(split['splits'][left][field]) & set(split['splits'][right][field])))
    check('legacy_has_no_full_scenario_seed', all('seed' not in r and 'scenario' not in r for r in old), 'No legacy scenario-seed non-overlap claim is made.')
    check('frozen_model_is_A_N3', read(MODEL)['model_version'] == training['model_version'] == 'a-n3-mlp-v1')

    pilot_dir = FROZEN/'data/teacher/a_n4_pilot_v1'
    pilot = rows(pilot_dir/'sources.jsonl')
    ps = read(pilot_dir/'source_splits.json')
    pm = read(pilot_dir/'manifest.json')
    psummary = read(pilot_dir/'summary.json')
    for name, expected in pm['output_sha256'].items():
        check('A_N4b_artifact_'+name, digest((pilot_dir/name).read_bytes()) == expected)
    check('A_N4b_sources_reconstructed', pilot == build_sources())
    check('A_N4b_30_seeds_410000_410029', len(pilot) == 30 and {r['seed'] for r in pilot} == set(range(410000,410030)))
    ordered = sorted([r['source_id'] for r in pilot], key=lambda x:digest(f"{ps['split_seed']}:{x}".encode()))
    offset = 0
    for name,count in [('train',18),('validation',6),('test',6)]:
        check('A_N4b_recomputed_'+name, ps['counts'][name] == count and ps['splits'][name] == ordered[offset:offset+count])
        offset += count
    check('A_N4b_no_source_overlap', len(set(sum(ps['splits'].values(), []))) == 30)
    check('A_N4b_remains_blocked_untrained', pm['training_enabled'] is False and psummary['training_enabled'] is False and psummary['status'] == 'blocked')

    archive = read(FROZEN/'experiments/formal_v1/input_manifest.json')['trajectories']
    development = read(FROZEN/'experiments/test_matrix.json')
    cells = {r['cell_id']:r for r in development['cells']}
    excluded_seeds = {r['seed'] for r in archive+pilot}
    excluded_content = {r['content_hash'] for r in archive}
    excluded_content.update(content_key(r['scenario']) for r in pilot)
    for trace in development['trajectories']:
        seed = trace['environment_seed']
        excluded_seeds.add(seed)
        excluded_content.add(content_key(build_config(cells[trace['cell_id']], seed)['scenario']))
    check('exclusion_set_exact_390_seeds', len(excluded_seeds) == 390 and sorted(excluded_seeds) == leakage['excluded_seeds'])
    check('exclusion_set_exact_374_content', len(excluded_content) == 374 and sorted(excluded_content) == leakage['excluded_content_hashes'])
    candidate_rows = manifest['trajectories']
    check('candidate_180_unique_registered_seeds', len(candidate_rows) == 180 and {r['seed'] for r in candidate_rows} == set(range(600000,600180)))
    check('candidate_no_excluded_seeds', not ({r['seed'] for r in candidate_rows} & excluded_seeds))
    old_keys = {projection(r['observation']) for r in old}
    check('legacy_20_unique_public_projections', len(old_keys) == 20)
    for trace in candidate_rows:
        cfg = read(CANDIDATE/'candidate'/trace['config_path'])
        check('candidate_recomputed_content_'+trace['trajectory_id'], content_key(cfg['scenario']) == trace['content_hash'] and trace['content_hash'] not in excluded_content)
        public = observe(create_state(cfg['scenario'])).model_dump(mode='json')
        check('legacy_observation_projection_no_overlap_'+trace['trajectory_id'], projection(public) not in old_keys)

    # Author only this independently performed machine review, transparently.
    receipt = read(REVIEW/'A.json')
    check('A_receipt_binding_unchanged', receipt['binding'] == binding and receipt['role'] == 'A')
    receipt.update(status='accepted_with_notes', reviewer='codex-delegated-A-source-review',
        reviewed_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'), leakage_sha256=EXPECTED_LEAKAGE,
        notes='User-authorized independent delegated A-scope machine review, performed by a separate Codex agent. This is an actual machine review and is not a human member-A signature. Recomputed actual A-N3 training-source binding and 12/4/4 splits, A-N4b 18/6/6 splits and seeds 410000-410029, 390 excluded seeds and 374 excluded contents, 20 legacy observation projections against 180 candidate initial observations, and frozen code/model/statistics/candidate bindings. Exact final accepted leakage bytes match C proposal e8da2be7968020eb9d1e974ae1cd5b46d3ca89ebec3fab466750bc4df7747018. Legacy sources lack full scenario seeds; no legacy seed-level comparison claimed. A-N4b stays blocked and training-disabled. No policies or training executed by this review; no policy-superiority or formal-result approval.',
        delegation=dict(authorized_by='user', authorization_text='能不能替ac进行检查，直接推进下一步', reviewer_type='independent_codex_agent_machine_review', scope='A_training_provenance_splits_exclusions_frozen_bindings', human_member_A_signature=False, audit_script='../../delegated_execution_2026-11-10/A_audit.py', audit_report='../../delegated_execution_2026-11-10/A_audit.json'))
    (REVIEW/'A.json').write_bytes(pretty(receipt))
    return dict(binding=binding, leakage_sha256=EXPECTED_LEAKAGE, receipt_sha256=digest((REVIEW/'A.json').read_bytes()), summary=dict(A_N3_splits=[12,4,4], A_N4b_splits=[18,6,6], A_N4b_seeds=[410000,410029], excluded_seeds=390, excluded_contents=374, legacy_projection_count=20, candidate_count=180, candidate_legacy_projection_overlap=0, policy_runs=0, training_runs=0))

if __name__ == '__main__':
    report = dict(schema_version='delegated-A-source-audit-v1', reviewer='codex-delegated-A-source-review', started_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'), frozen_checkout=str(FROZEN), audit_script_sha256=digest(Path(__file__).read_bytes()), checks=checks)
    try:
        report.update(audit(), status='passed')
    except Exception:
        report.update(status='failed', error=traceback.format_exc())
    report['finished_at'] = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    (OUT/'A_audit.json').write_bytes(pretty(report))
    lines = [f"{('PASS' if r['passed'] else 'FAIL')} {r['name']}" for r in checks]
    lines += [f"status={report['status']}", f"checks={len(checks)}", report.get('error','')]
    (OUT/'A_audit.log').write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in {'binding','checks'}}, ensure_ascii=False, indent=2))
    sys.exit(0 if report['status'] == 'passed' else 1)
