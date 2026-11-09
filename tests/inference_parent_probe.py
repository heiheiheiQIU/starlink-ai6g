"""Disposable subprocess used to verify OS containment after service death."""
import json
from pathlib import Path
import sys
import time

from backend.api.service import RunService
from tests.test_api import held_worker, request


if __name__ == '__main__':
    output=Path(sys.argv[1])
    if len(sys.argv)>2:
        from backend.api.processes import ProcessGroup
        import multiprocessing
        original=ProcessGroup.add
        count=[0]
        target=1 if sys.argv[2]=='inference' else 2
        def pause_before_assignment(group, process):
            count[0]+=1
            if count[0]==target:
                time.sleep(.75)
                (output/'pids.json').write_text(json.dumps([p.pid for p in multiprocessing.active_children()]),encoding='utf-8')
                time.sleep(90)
            original(group,process)
        ProcessGroup.add=pause_before_assignment
    service=RunService(output/'runs', worker=held_worker)
    service.start()
    identity=service.submit(request(['learned']))['run_id']
    children=[service.jobs[identity][0].pid, service.inference_jobs[identity].process.pid]
    (output/'pids.json').write_text(json.dumps(children), encoding='utf-8')
    time.sleep(90)
