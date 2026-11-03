import time

import pytest

from backend.api.inference import InferenceFailure, InferenceSupervisor, inspect_model
from tests.test_policies import obs


def hanging_score(observation):
    time.sleep(60)


def crashing_score(observation):
    import os
    os._exit(17)


def test_supervised_frozen_inference_and_close_reaps_process():
    with InferenceSupervisor() as supervisor:
        process = supervisor.process
        scores = supervisor.client(obs())
        assert len(scores) == 3
        assert supervisor.metadata['model_hash'] == inspect_model()['model_hash']
        assert process.is_alive()
    assert supervisor.exitcode is not None and process._closed


def test_start_uses_validated_config_snapshot_not_changed_config_file(tmp_path):
    import json
    from backend.policies.learned import _config
    path=tmp_path/'runtime.json';path.write_text(json.dumps(_config(None)))
    supervisor=InferenceSupervisor(model_config=path)
    path.write_text(json.dumps({'enabled':False}))
    with supervisor:
        assert len(supervisor.client(obs()))==3


@pytest.mark.parametrize('scorer,reason', [(hanging_score, 'MODEL_TIMEOUT'), (crashing_score, 'MODEL_UNAVAILABLE')])
def test_bounded_failed_inference_is_killed_and_not_reused(scorer, reason):
    # Windows process teardown is not guaranteed to finish inside a 30ms score budget.
    with InferenceSupervisor(scorer=scorer, budget_ms=30 if reason=='MODEL_TIMEOUT' else 1000) as supervisor:
        before = time.monotonic()
        with pytest.raises(InferenceFailure) as failure:
            supervisor.client(obs())
        assert failure.value.code == reason
        assert time.monotonic()-before < 1.5
        supervisor.reap()
        assert not supervisor.process.is_alive()
        with pytest.raises(InferenceFailure): supervisor.client(obs())


def test_service_death_kills_running_and_inference_processes(tmp_path):
    import json
    import os
    from pathlib import Path
    import signal
    import subprocess
    import sys
    from backend.api.processes import pid_alive
    root=Path(__file__).resolve().parents[1]
    children=[]
    with (tmp_path/'parent.log').open('wb') as log:
        parent=subprocess.Popen([sys.executable,'-m','tests.inference_parent_probe',str(tmp_path)],
                                cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:
            for _ in range(200):
                if (tmp_path/'pids.json').exists():
                    children=json.loads((tmp_path/'pids.json').read_text());break
                assert parent.poll() is None, (tmp_path/'parent.log').read_text(errors='replace')
                time.sleep(.05)
            assert len(children)==2 and all(pid_alive(p) for p in children)
            parent.kill();parent.wait(5)
            for _ in range(100):
                if all(not pid_alive(p) for p in children): break
                time.sleep(.05)
            assert all(not pid_alive(p) for p in children)
        finally:
            if parent.poll() is None: parent.kill();parent.wait(5)
            for pid in children:
                if pid_alive(pid): os.kill(pid, signal.SIGTERM)

