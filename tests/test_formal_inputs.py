import json
from pathlib import Path

import pytest

from backend.formal_inputs import materialize_inputs, verify_inputs


PROTOCOL = Path('experiments/formal_v1/protocol.json')


def test_180_unique_reproducible_inputs_and_pending_gate(tmp_path):
    first = materialize_inputs(PROTOCOL, tmp_path/'first')
    second = materialize_inputs(PROTOCOL, tmp_path/'second')
    assert first == second
    rows = first['trajectories']
    assert len(rows) == 180
    assert len({r['cell_id'] for r in rows}) == 18
    assert all(sum(r['cell_id'] == cell for r in rows) == 10 for cell in {r['cell_id'] for r in rows})
    for key in ('trajectory_id', 'seed', 'input_hash', 'content_hash'):
        assert len({r[key] for r in rows}) == 180
    assert {r['seed'] for r in rows} == set(range(200000, 200180))
    assert not {r['seed'] for r in rows} & set(range(10000, 10180))
    assert verify_inputs(tmp_path/'first/manifest.json') == first
    with pytest.raises(ValueError, match='pending'):
        verify_inputs(tmp_path/'first/manifest.json', require_frozen=True)
    assert first['model'] is None


@pytest.mark.parametrize('mutation', ['missing_cell', 'duplicate_seed', 'old_seed'])
def test_invalid_protocol_rejected_before_publication(tmp_path, mutation):
    protocol = json.loads(PROTOCOL.read_text())
    if mutation == 'missing_cell':
        protocol['cells'].pop()
    elif mutation == 'duplicate_seed':
        protocol['trajectories'][1]['seed'] = protocol['trajectories'][0]['seed']
    else:
        protocol['trajectories'][0]['seed'] = 10000
    path = tmp_path/'protocol.json'
    path.write_text(json.dumps(protocol))
    with pytest.raises(ValueError):
        materialize_inputs(path, tmp_path/'out')
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('mutation', ['config', 'manifest', 'path'])
def test_tampering_rejected(tmp_path, mutation):
    manifest = materialize_inputs(PROTOCOL, tmp_path/'out')
    path = tmp_path/'out/manifest.json'
    if mutation == 'config':
        config = tmp_path/'out'/manifest['trajectories'][0]['config_path']
        config.write_text(config.read_text()+' ')
    else:
        if mutation == 'manifest':
            manifest['trajectories'].pop()
        else:
            manifest['trajectories'][0]['config_path'] = '../escape.json'
        path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        verify_inputs(path)


def test_no_overwrite_and_training_seed_collision(tmp_path):
    materialize_inputs(PROTOCOL, tmp_path/'out')
    with pytest.raises(ValueError):
        materialize_inputs(PROTOCOL, tmp_path/'out')
    with pytest.raises(ValueError, match='collision'):
        materialize_inputs(PROTOCOL, tmp_path/'other', excluded_seeds={200000})
    assert not (tmp_path/'other').exists()


def test_content_collision_rejected_and_runner_identity_matches(tmp_path):
    from backend.policies.runner import run_policy

    manifest = materialize_inputs(PROTOCOL, tmp_path/'inputs')
    row = manifest['trajectories'][0]
    with pytest.raises(ValueError, match='content collision'):
        materialize_inputs(PROTOCOL, tmp_path/'collision', excluded_content_hashes={row['content_hash']})
    config = json.loads((tmp_path/'inputs'/row['config_path']).read_text())
    for policy in ('edf', 'value'):
        result = run_policy(config, tmp_path/policy, policy_id=policy)
        assert result['input_hash'] == row['input_hash']
        assert result['seed'] == row['seed']
