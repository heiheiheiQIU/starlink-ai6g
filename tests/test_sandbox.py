import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient
from backend.api.main import create_app
from tests.test_api import wait


def test_compiler_deterministic_and_health_consistent():
    from backend.sandbox import compile_sandbox_axes, GOLDEN_AXES
    from backend.cli import RunConfig
    from backend.simulator.engine import create_state, observe
    for axes in GOLDEN_AXES.values():
        config = compile_sandbox_axes(axes, 9)
        assert config == compile_sandbox_axes(axes, 9)
        parsed = RunConfig.model_validate(config)
        health = observe(create_state(parsed.scenario)).health
        assert health.energy_lower_Wh == pytest.approx(health.soc_lower * health.capacity_lower_Wh)
        assert parsed.scenario.channel.seed == 9 and parsed.actions == []


@pytest.mark.parametrize('change', [
    {'task_count': True}, {'task_count': 3}, {'reserve_Wh': -1},
    {'initial_energy_Wh': float('nan')}, {'health': 'unknown'},
    {'deadline_s': 9}, {'extra': 1}, {'reserve_Wh': 21},
])
def test_invalid_axes(change):
    from backend.sandbox import compile_sandbox_axes, GOLDEN_AXES
    with pytest.raises(ValueError):
        compile_sandbox_axes(dict(GOLDEN_AXES['S1'], **change), 7)


@pytest.mark.parametrize('seed', [True, '7', 7.0, -1])
def test_compiler_rejects_non_integer_seed(seed):
    from backend.sandbox import compile_sandbox_axes, GOLDEN_AXES
    with pytest.raises(ValueError):
        compile_sandbox_axes(GOLDEN_AXES['S1'], seed)


def test_sandbox_http_evidence_and_invalid_location(tmp_path):
    from backend.sandbox import GOLDEN_AXES, compile_sandbox_axes
    request = dict(schema_version='1.0', seed=7, policy_ids=['edf','value'],
                   config=dict(kind='sandbox_axes', compiler_version='sandbox-axis-v1', axes=GOLDEN_AXES['S1']))
    with TestClient(create_app(tmp_path)) as client:
        bad = json.loads(json.dumps(request))
        bad['config']['axes']['task_count'] = 3
        response = client.post('/runs', json=bad)
        assert response.status_code == 422
        assert any('task_count' in row['loc'] for row in response.json()['details']['errors'])
        created = client.post('/runs', json=request)
        assert created.status_code == 202, created.text
        identity = created.json()['run_id']
        assert identity.startswith('sandbox_run_')
        assert wait(client, identity)['status'] == 'completed'
        raw = client.get('/runs/'+identity+'/export')
        assert raw.status_code == 200, raw.text
        with zipfile.ZipFile(io.BytesIO(raw.content)) as package:
            assert json.loads(package.read('config.json')) == request
            assert json.loads(package.read('compiled_config.json')) == compile_sandbox_axes(GOLDEN_AXES['S1'],7)
            assert json.loads(package.read('sandbox.json'))['compiler_version'] == 'sandbox-axis-v1'
        events = client.get('/runs/'+identity+'/events').json()['events']
        assert events and events[0]['event_id'] == 1


def test_sandbox_link_cannot_read_recover_or_create_outside(tmp_path):
    import os
    import subprocess
    from backend.api.service import RunService, ServiceError
    from backend.api.worker import write_status
    root = tmp_path/'runs'
    root.mkdir()
    outside = tmp_path/'outside'
    outside.mkdir()
    identity = 'sandbox_run_'+'e'*32
    folder = outside/identity
    folder.mkdir()
    write_status(folder, 'running', active=['edf'])
    link = root/'sandbox'
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        assert os.name == 'nt'
        result = subprocess.run(['cmd','/c','mklink','/J',str(link),str(outside)],capture_output=True)
        assert result.returncode == 0
    service = RunService(root)
    with pytest.raises((ValueError, ServiceError)):
        service.folder(identity)
    service.start()
    service.close()
    assert json.loads((folder/'status.json').read_text())['status'] == 'running'
