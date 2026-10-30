import hashlib
import json
import shutil
import uuid
from pathlib import Path

import pytest

from training.policy_features import GLOBAL_FEATURE_NAMES, CANDIDATE_FEATURE_NAMES

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def dataset():
    folder = ROOT / 'runs' / ('split-test-' + uuid.uuid4().hex)
    folder.mkdir(parents=True)
    rows = [dict(sample_id=f's{i}-{j}', scenario_id=f'case{i}', label_eligible=True,
                 solver_status='OPTIMAL', gap=0.0) for i in range(20) for j in range(2)]
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
    expected_order = sorted({r['scenario_id'] for r in rows}, key=lambda scenario:
                            hashlib.sha256(f'42:{scenario}'.encode('utf-8')).hexdigest())
    for name, start, count in (('train', 0, 12), ('validation', 12, 4), ('test', 16, 4)):
        split = a['splits'][name]
        assert split['scenario_ids'] == expected_order[start:start + count]
        assert len(split['scenario_ids']) == split['scenario_count'] == count
        assert len(split['sample_ids']) == split['sample_count'] == count * 2
    for split in a['splits'].values():
        assert set(split['sample_ids']) == {r['sample_id'] for r in rows if r['scenario_id'] in split['scenario_ids']}
    for field in ('scenario_ids', 'sample_ids'):
        sets = [set(a['splits'][name][field]) for name in ('train', 'validation', 'test')]
        assert all(not sets[i] & sets[j] for i in range(3) for j in range(i + 1, 3))
        assert set.union(*sets) == {r['scenario_id' if field == 'scenario_ids' else 'sample_id'] for r in rows}


@pytest.mark.parametrize('change', ['duplicate', 'fewer', 'more', 'ineligible', 'status', 'gap', 'blocked', 'hash', 'tamper'])
def test_invalid_input_rejected(dataset, change):
    from training.splits import build_split_manifest
    folder, rows, write = dataset
    if change == 'duplicate': rows[1]['sample_id'] = rows[0]['sample_id']
    if change == 'fewer': rows[:] = [r for r in rows if r['scenario_id'] != 'case19']
    if change == 'more': rows.append(dict(rows[0], sample_id='extra', scenario_id='extra'))
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
