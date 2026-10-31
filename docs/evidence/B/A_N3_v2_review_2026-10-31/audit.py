"""B independent audit; run with A snapshot as cwd and B's Python environment."""
import hashlib
import json
from pathlib import Path
import sys
import subprocess
from collections import defaultdict

root = Path.cwd()
sys.path.insert(0, str(root))
from backend.contracts import Observation, validate_teacher_result
from backend.policies.teacher import solve_teacher
from training.policy_features import encode_observation

out = Path(sys.argv[1]).resolve()
sha = lambda raw: hashlib.sha256(raw).hexdigest()
canon = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True,
                                separators=(',', ':'), allow_nan=False).encode()
load = lambda path: json.loads((root / path).read_bytes())
folder = root / 'data/teacher/a_n3_20_v2'
rows = [json.loads(line) for line in (folder / 'samples.jsonl').read_bytes().splitlines()]
sources = {r['sample_id']: r for r in (json.loads(line) for line in
           (root / 'data/teacher/sources/a_n3_20_v2.jsonl').read_bytes().splitlines())}
manifest = load('data/teacher/a_n3_20_v2/manifest.json')
splits = load('data/teacher/a_n3_20_v2/splits.json')
summary = load('data/teacher/a_n3_20_v2/summary.json')
config = load('configs/teacher.json')
revision = '8f206b4f6d029ddaf3cfd6163777e0c9a57b03ee'
paths = ['data/teacher/a_n3_20_v2/' + name for name in
         ('samples.jsonl', 'summary.json', 'manifest.json', 'splits.json')]
paths += ['data/teacher/sources/a_n3_20_v2.jsonl', 'configs/teacher.json',
          'backend/contracts.py', 'backend/policies/teacher.py', 'training/policy_features.py']
hashes = {}
for path in paths:
    raw = (root / path).read_bytes()
    original = subprocess.check_output(['git', '-C', str(Path(__file__).resolve().parents[4]), 'show', revision + ':' + path])
    assert raw == original, path
    hashes[path] = sha(raw)
for name, digest in manifest['output_sha256'].items():
    assert sha((folder / name).read_bytes()) == digest
assert manifest['source_sha256'] == hashes['data/teacher/sources/a_n3_20_v2.jsonl']
assert manifest['teacher_config_sha256'] == hashes['configs/teacher.json']
assert splits['source_jsonl_sha256'] == hashes['data/teacher/a_n3_20_v2/samples.jsonl']
assert len(rows) == len(sources) == summary['total'] == 20
label_fields = ('dataset_version', 'source_group_id', 'observation_content_sha256', 'sample_id', 'scenario_id', 'state_id', 'source_revision',
                'source_observation_sha256', 'observation', 'teacher_version',
                'teacher_config_sha256', 'candidate_scores', 'solver_status',
                'gap', 'diagnostics', 'label_eligible', 'exclusion_reasons')
split_of = {}
scenario_sets = []
for name, count in [('train', 12), ('validation', 4), ('test', 4)]:
    part = splits['splits'][name]
    assert len(part['sample_ids']) == len(part['scenario_ids']) == count
    scenario_sets.append(set(part['scenario_ids']))
    for identity in part['sample_ids']:
        assert identity not in split_of
        split_of[identity] = name
assert set(split_of) == {r['sample_id'] for r in rows}
assert all(not scenario_sets[i] & scenario_sets[j] for i in range(3) for j in range(i))
semantic = defaultdict(list)
details = []
for row in rows:
    observation = Observation.model_validate(row['observation'])
    assert row['observation'] == sources[row['sample_id']]['observation']
    assert row['source_observation_sha256'] == sha(canon(row['observation']))
    assert row['label_content_sha256'] == sha(canon({k: row[k] for k in label_fields}))
    result = validate_teacher_result(observation, {k: row[k] for k in
        ('candidate_scores', 'solver_status', 'gap', 'elapsed_ms')})
    diagnostic = {}
    recomputed = solve_teacher(observation, budget_ms=manifest['budget_ms'],
                               config=config, diagnostics=diagnostic)
    validate_teacher_result(observation, recomputed)
    assert recomputed.solver_status == result.solver_status == 'OPTIMAL'
    assert recomputed.gap == result.gap == 0
    assert [x.model_dump() for x in recomputed.candidate_scores] == row['candidate_scores']
    assert {(c['task_id'], c['mode']) for c in row['candidate_scores']} == (
        {(t.task_id, m) for t in observation.tasks for m in ('robust', 'fast')} | {(None, 'idle')})
    features = encode_observation(observation)
    assert len(features.global_features) == 14
    assert all(len(values) == 9 for values in features.candidate_features)
    assert features.candidate_keys[-1] == (None, 'idle') and features.candidate_mask[-1]
    assert row['scenario_id'] in splits['splits'][split_of[row['sample_id']]]['scenario_ids']
    normalized = dict(row['observation'])
    normalized.pop('run_id')
    normalized.pop('policy_id')
    assert row['observation_content_sha256'] == sha(canon(normalized))
    assert row['source_group_id'] == sources[row['sample_id']]['source_group_id']
    semantic[sha(canon(normalized))].append(dict(sample_id=row['sample_id'], split=split_of[row['sample_id']]))
    details.append(dict(sample_id=row['sample_id'], status=recomputed.solver_status,
                        elapsed_ms=recomputed.elapsed_ms, label_matches=True))
for field in ('source_group_ids', 'scenario_ids', 'sample_ids', 'observation_content_sha256'):
    sets = [set(splits['splits'][name][field]) for name in ('train', 'validation', 'test')]
    assert [len(values) for values in sets] == [12, 4, 4]
    assert all(not sets[i] & sets[j] for i in range(3) for j in range(i))
    row_field = {'source_group_ids': 'source_group_id', 'scenario_ids': 'scenario_id', 'sample_ids': 'sample_id', 'observation_content_sha256': 'observation_content_sha256'}[field]
    assert set.union(*sets) == {r[row_field] for r in rows}
assert len(semantic) == 20
assert len({r['source_group_id'] for r in rows}) == 20
assert splits['split_algorithm_version'] == 'source-group-sha256-v2'
assert splits['split_seed'] == 20261031
assert summary == dict(eligible=20, failures=0, ineligible=0, solver_status_counts={'OPTIMAL':20}, status='ready_for_split', total=20)
ordered = sorted({r['source_group_id'] for r in rows}, key=lambda group: (sha(f"20261031:{group}".encode()), group))
assert splits['splits']['train']['source_group_ids'] == ordered[:12]
assert splits['splits']['validation']['source_group_ids'] == ordered[12:16]
assert splits['splits']['test']['source_group_ids'] == ordered[16:]
# Adversarial duplicate must be rejected before the first teacher invocation.
import copy
from unittest.mock import patch
from training.generate_teacher_data import generate_teacher_dataset, TeacherDataError
probe = root / 'runs/b_independent_duplicate_probe'
probe.mkdir(parents=True, exist_ok=True)
bad = list(sources.values())
bad = copy.deepcopy(bad)
bad[1]['observation'] = copy.deepcopy(bad[0]['observation'])
bad[1]['observation']['run_id'] = 'independent-duplicate-id'
(probe / 'source.jsonl').write_bytes(b''.join(canon(r)+b'\n' for r in bad))
with patch('training.generate_teacher_data.solve_teacher') as solver:
    try:
        generate_teacher_dataset(source_path=probe/'source.jsonl', output_dir=probe/'output', source_revision=revision, teacher_config_path=root/'configs/teacher.json', budget_ms=1000, expected_count=20)
    except TeacherDataError as error:
        assert error.code == 'DUPLICATE_OBSERVATION_CONTENT'
    else:
        raise AssertionError('Duplicate content unexpectedly accepted')
    assert solver.call_count == 0
assert not (probe/'output').exists()
duplicates = [group for group in semantic.values() if len(group) > 1]
cross = [group for group in duplicates if len({item['split'] for item in group}) > 1]
report = dict(duplicate_rejected_before_teacher=True, independent_split_order_verified=True, candidate=revision, artifact_sha256=hashes, recomputed_count=len(details),
              label_matches=20, nominal_split_counts={'train': 12, 'validation': 4, 'test': 4},
              nominal_split_disjoint=True, unique_semantic_observations=len(semantic),
              duplicates_ignoring_run_and_policy_id=duplicates, cross_split_duplicates=cross,
              normalization='deferred-until-training', training_enabled=False,
              details=details, scope='synthetic teacher data only')
(out / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ('recomputed_count', 'label_matches', 'unique_semantic_observations', 'cross_split_duplicates')}))
