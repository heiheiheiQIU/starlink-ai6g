"""Read-side Windows sharing violations on public status and worker reaping."""
import multiprocessing
from pathlib import Path
import time

import pytest

from backend.api.service import RunService
from backend.api.worker import write_status


def _exit_worker():
    pass


def _completed_service(tmp_path):
    service = RunService(tmp_path)
    identity = 'run_' + 'e' * 32
    folder = tmp_path / identity
    folder.mkdir()
    write_status(folder, 'completed', progress=1.0)
    return service, identity, folder


def _lock_three_reads(monkeypatch, target):
    original = Path.read_text
    attempts = []

    def locked(path, *args, **kwargs):
        if path == target:
            attempts.append(path)
            if len(attempts) <= 3:
                raise PermissionError('Windows sharing violation')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', locked)
    return attempts


def test_status_recovers_after_multiple_read_locks(tmp_path, monkeypatch):
    service, identity, folder = _completed_service(tmp_path)
    attempts = _lock_three_reads(monkeypatch, folder / 'status.json')
    assert service.status(identity)['status'] == 'completed'
    assert len(attempts) == 4


def test_reap_recovers_after_multiple_read_locks(tmp_path, monkeypatch):
    service, identity, folder = _completed_service(tmp_path)
    process = multiprocessing.get_context('spawn').Process(target=_exit_worker)
    process.start()
    process.join(10)
    assert process.exitcode == 0
    service.jobs[identity] = (process, time.monotonic())
    attempts = _lock_three_reads(monkeypatch, folder / 'status.json')
    try:
        service.reap()
        assert identity not in service.jobs
        assert len(attempts) == 4
        assert service.status(identity)['status'] == 'completed'
    finally:
        if identity in service.jobs:
            process.close()


def test_persistent_read_lock_has_finite_retry_budget(tmp_path, monkeypatch):
    from backend.api import worker
    target = tmp_path / 'status.json'
    target.write_text('{}', encoding='utf-8')
    clock = [0.0]
    attempts = []

    def denied(path, *args, **kwargs):
        attempts.append(path)
        raise PermissionError('Persistent Windows sharing violation')

    monkeypatch.setattr(Path, 'read_text', denied)
    monkeypatch.setattr(worker.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(worker.time, 'sleep', lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    with pytest.raises(PermissionError, match='Persistent Windows'):
        worker.read_text(target)
    assert 2 <= clock[0] <= 2.02
    assert 2 < len(attempts) <= 202
