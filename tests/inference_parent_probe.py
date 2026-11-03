"""Disposable subprocess used to verify OS containment after service death."""
import json
from pathlib import Path
import sys
import time

from backend.api.service import RunService
from tests.test_api import held_worker, request


if __name__ == '__main__':
    output=Path(sys.argv[1])
    service=RunService(output/'runs', worker=held_worker)
    service.start()
    identity=service.submit(request(['learned']))['run_id']
    children=[service.jobs[identity][0].pid, service.inference_jobs[identity].process.pid]
    (output/'pids.json').write_text(json.dumps(children), encoding='utf-8')
    time.sleep(90)
