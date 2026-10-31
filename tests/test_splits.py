import hashlib
import copy
import json
import shutil
import uuid
from pathlib import Path

import pytest

from training.policy_features import GLOBAL_FEATURE_NAMES, CANDIDATE_FEATURE_NAMES
from training.generate_teacher_data import observation_content_sha256

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def dataset():
    folder = ROOT / 'runs' / ('split-test-' + uuid.uuid4().hex)
    folder.mkdir(parents=True)
    rows = []
    for i in range(20):
        for j in range(2):
            observation = {'run_id': f'run-{i}-{j}', 'policy_id': 'teacher',
                           'cache_bytes': i * 100 + j}
            rows.append(dict(sample_id=f's{i}-{j}', scenario_id=f'case{i}-{j}',
                             source_group_id=f'source-{i}', observation=observation,
                             observation_content_sha256=observation_content_sha256(observation),
                             label_eligible=True, solver_status='OPTIMAL', gap=0.0))
    def write():
        raw = ''.join(json.dumps(row) + '\n' for row in rows).encode()
        (folder / 'samples.jsonl').write_bytes(raw)
        summary = json.dumps(dict(status='ready_for_split', total=len(rows), eligible=len(rows), ineligible=0, failures=0)).encode()
        (folder / 'summary.json').write_bytes(summary)
        (folder / 'manifest.json').write_text(json.dumps({'output_sha256': {'samples.jsonl': hashlib.sha256(raw).hexdigest(), 'summary.json': hashlib.sha256(summary).hexdigest()}}), encoding='utf-8')
    write()
    yield folder, rows, write
    shutil.rmtree(folder)


def test_determinism_disjoint_and_complete(dataset):
    from training.splits import build_split_manifest
    folder, rows, _ = dataset
    a = build_split_manifest(folder / 'samples.jsonl', folder / 'a.json', split_seed=42)
    build_split_manifest(folder / 'samples.jsonl', folder / 'b.json', split_seed=42)
    b = build_split_manifest(folder / 'samples.jsonl', folder / 'c.json', split_seed=43)
    assert (folder / 'a.json').read_bytes() == (folder / 'b.json').read_bytes()
    assert a['splits'] != b['splits']
    expected_order = sorted({r['source_group_id'] for r in rows}, key=lambda group:
                            hashlib.sha256(f'42:{group}'.encode('utf-8')).hexdigest())
    for name, start, count in (('train', 0, 12), ('validation', 12, 4), ('test', 16, 4)):
        split = a['splits'][name]
        assert split['source_group_ids'] == expected_order[start:start + count]
        assert len(split['source_group_ids']) == split['source_group_count'] == count
        assert len(split['scenario_ids']) == split['scenario_count'] == count * 2
        assert len(split['sample_ids']) == split['sample_count'] == count * 2
        assert len(split['observation_content_sha256']) == split['observation_content_count'] == count * 2
    for split in a['splits'].values():
        assert set(split['sample_ids']) == {
            r['sample_id'] for r in rows if r['source_group_id'] in split['source_group_ids']}
    sample_to_split = {sample: name for name, split in a['splits'].items()
                       for sample in split['sample_ids']}
    for i in range(20):
        assert sample_to_split[f's{i}-0'] == sample_to_split[f's{i}-1']
    for field in ('source_group_ids', 'scenario_ids', 'sample_ids',
                  'observation_content_sha256'):
        sets = [set(a['splits'][name][field]) for name in ('train', 'validation', 'test')]
        assert all(not sets[i] & sets[j] for i in range(3) for j in range(i + 1, 3))
        row_field = {'source_group_ids': 'source_group_id', 'scenario_ids': 'scenario_id',
                     'sample_ids': 'sample_id',
                     'observation_content_sha256': 'observation_content_sha256'}[field]
        assert set.union(*sets) == {r[row_field] for r in rows}


@pytest.mark.parametrize('change', [
    'duplicate', 'fewer', 'more', 'ineligible', 'status', 'gap', 'blocked',
    'hash', 'tamper',
])
def test_invalid_input_rejected(dataset, change):
    from training.splits import build_split_manifest
    folder, rows, write = dataset
    if change == 'duplicate': rows[1]['sample_id'] = rows[0]['sample_id']
    if change == 'fewer': rows[:] = [r for r in rows if r['source_group_id'] != 'source-19']
    if change == 'more':
        observation = {'run_id': 'extra-run', 'policy_id': 'teacher', 'cache_bytes': 9999}
        rows.append(dict(rows[0], sample_id='extra', scenario_id='extra',
                         source_group_id='extra', observation=observation,
                         observation_content_sha256=observation_content_sha256(observation)))
    if change == 'ineligible': rows[0]['label_eligible'] = False
    if change == 'status': rows[0]['solver_status'] = 'FEASIBLE'
    if change == 'gap': rows[0]['gap'] = 0.1
    write()
    if change == 'blocked':
        summary = folder / 'summary.json'
        summary.write_text(json.dumps(dict(status='blocked')), encoding='utf-8')
        manifest = folder / 'manifest.json'
        data = json.loads(manifest.read_text(encoding='utf-8'))
        data['output_sha256']['summary.json'] = hashlib.sha256(summary.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(data), encoding='utf-8')
    if change == 'hash':
        manifest = folder / 'manifest.json'
        manifest.write_text(json.dumps({'output_sha256': {'samples.jsonl': 'bad'}}), encoding='utf-8')
    if change == 'tamper':
        with (folder / 'samples.jsonl').open('ab') as stream: stream.write(b' ')
    with pytest.raises(ValueError):
        build_split_manifest(folder / 'samples.jsonl', folder / 'out.json', split_seed=42)


@pytest.mark.parametrize(('change', 'message'), [
    ('forged_content_hash', 'Observation content hash mismatch'),
    ('duplicate_content', 'Duplicate observation content'),
    ('scenario_cross_group', 'Scenario spans source groups'),
])
def test_identity_boundary_rejected_for_the_specific_reason(dataset, change, message):
    from training.splits import build_split_manifest
    folder, rows, write = dataset
    if change == 'forged_content_hash':
        rows[0]['observation_content_sha256'] = '0' * 64
    elif change == 'duplicate_content':
        rows[-1]['observation'] = copy.deepcopy(rows[0]['observation'])
        rows[-1]['observation']['run_id'] = 'different-run-id'
        rows[-1]['observation']['policy_id'] = 'different-policy-id'
        rows[-1]['observation_content_sha256'] = observation_content_sha256(rows[-1]['observation'])
    else:
        rows[-1]['scenario_id'] = rows[0]['scenario_id']
    write()
    with pytest.raises(ValueError, match=message):
        build_split_manifest(folder / 'samples.jsonl', folder / 'out.json', split_seed=42)


def test_config_matches_features():
    config = json.loads((ROOT / 'configs/policy_train.json').read_text(encoding='utf-8'))
    assert config == {
        'schema_version': 'policy-train-config-v1',
        'dataset_path': 'data/teacher/a_n3_20/samples.jsonl',
        'dataset_summary_path': 'data/teacher/a_n3_20/summary.json',
        'dataset_manifest_path': 'data/teacher/a_n3_20/manifest.json',
        'split_manifest_path': 'data/teacher/a_n3_20/splits.json',
        'teacher_version': 'bounded-forecast-r4-v1',
        'teacher_budget_ms': 1000,
        'feature_schema_version': 'policy-features-v1',
        'global_feature_names': list(GLOBAL_FEATURE_NAMES),
        'candidate_feature_names': list(CANDIDATE_FEATURE_NAMES),
        'split_algorithm_version': 'scenario-sha256-v1',
        'split_seed': 20261030,
        'split_counts': {'train': 12, 'validation': 4, 'test': 4},
        'eligible_solver_status': 'OPTIMAL',
        'required_gap': 0.0,
        'normalization': 'deferred-until-training',
        'training_enabled': False,
    }
    assert config['training_enabled'] is False


def test_link_failure_does_not_publish_and_cleans_staging(dataset, monkeypatch):
    import training.splits as splits

    folder, _, _ = dataset
    destination = folder / 'out.json'
    staged = []

    def fail_link(source, target):
        staged.append(Path(source))
        assert Path(source).is_file()
        assert Path(target) == destination
        raise OSError('injected link failure')

    monkeypatch.setattr(splits.os, 'link', fail_link)
    with pytest.raises(OSError, match='injected link failure'):
        splits.build_split_manifest(folder / 'samples.jsonl', destination, split_seed=42)
    assert len(staged) == 1
    assert not destination.exists()
    assert not staged[0].exists()
    assert not list(folder.glob('.splits-*'))


def test_existing_output_is_immutable(dataset):
    from training.splits import build_split_manifest
    folder, _, _ = dataset
    target = folder / 'out.json'
    build_split_manifest(folder / 'samples.jsonl', target, split_seed=42)
    before = target.read_bytes()
    build_split_manifest(folder / 'samples.jsonl', target, split_seed=42)
    with pytest.raises(ValueError):
        build_split_manifest(folder / 'samples.jsonl', target, split_seed=43)
    assert target.read_bytes() == before


def test_cli_passes_explicit_split_counts(monkeypatch):
    import sys
    import training.splits as splits

    calls = []
    monkeypatch.setattr(splits, 'build_split_manifest', lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(sys, 'argv', ['training.splits', '--samples', 'samples.jsonl', '--output', 'splits.json',
                                     '--seed', '20261030', '--train-count', '12', '--validation-count', '4',
                                     '--test-count', '4'])
    splits.main()
    assert calls == [((Path('samples.jsonl'), Path('splits.json')), {'split_seed': 20261030, 'split_counts': (12, 4, 4)})]
