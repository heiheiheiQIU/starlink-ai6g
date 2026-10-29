"""Single-server process supervisor and bounded read/export operations."""
import io
import json
import multiprocessing
import re
import threading
import time
import zipfile
from pathlib import Path
from uuid import uuid4

from backend.cli import RunConfig, _write_json
from backend.contracts import EventsPage, EventsQuery, Event, RunRequest, RunStatusResponse
from .worker import execute_run, fail_run, write_status, read_text


class ServiceError(Exception):
    def __init__(self,http_status,code,message,**details):
        self.status=http_status; self.body=dict(code=code,message=message,details=details)


def checked_file(folder, name):
    relative=Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Invalid artifact path')
    base=folder.resolve();path=folder/relative
    for part in [path,*path.parents]:
        if part==folder.parent: break
        if part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()):
            raise ValueError('Linked artifact is not allowed')
        if part==folder: break
    if not path.resolve().is_relative_to(base): raise ValueError('Artifact outside run')
    return path


class RunService:
    def __init__(self,root,*,worker=execute_run,timeout_s=120.0):
        if timeout_s<=0: raise ValueError('Positive worker timeout required')
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.worker=worker;self.timeout_s=timeout_s;self.jobs={};self.lock=threading.RLock()
        self.stopping=threading.Event();self.monitor=None

    def start(self):
        # Single service owns this root; unfinished records from an earlier stop fail honestly.
        for folder in self.root.iterdir():
            if folder.is_dir() and re.fullmatch(r'run_[0-9a-f]{32}',folder.name):
                try: checked_file(folder,'status.json')
                except ValueError: continue  # Never recover through an external link.
                try: state=self.status(folder.name)
                except (ServiceError,ValueError,OSError):
                    fail_run(folder,'INCOMPLETE_RUN_RECORD')
                    continue
                if state['status'] in ('queued','running'): fail_run(folder,'SERVICE_RESTARTED')
        self.monitor=threading.Thread(target=self._watch,daemon=True);self.monitor.start()

    def _watch(self):
        while not self.stopping.wait(.05):
            with self.lock: self.reap()

    def reap(self):
        for identity,(process,started) in list(self.jobs.items()):
            folder=self.root/identity
            expired=time.monotonic()-started>self.timeout_s
            if expired and process.is_alive(): process.terminate();process.join(3)
            if expired or not process.is_alive():
                process.join(3)
                state=json.loads(read_text(folder/'status.json'))
                if state['status'] not in ('completed','failed','cancelled'):
                    fail_run(folder,'WORKER_TIMEOUT' if expired else 'WORKER_EXITED')
                process.close();del self.jobs[identity]

    def close(self):
        self.stopping.set()
        if self.monitor: self.monitor.join(2)
        with self.lock:
            for identity,(process,_) in list(self.jobs.items()):
                if process.is_alive(): process.terminate()
                process.join(3)
                folder=self.root/identity
                if self.status(identity)['status'] not in ('completed','failed','cancelled'):
                    fail_run(folder,'SERVICE_STOPPED')
                process.close()
            self.jobs.clear()

    def submit(self,payload):
        request=RunRequest.model_validate(payload)
        if any(p not in ('edf','value') for p in request.policy_ids):
            raise ValueError('Only edf/value are supported in this release')
        config=RunConfig.model_validate(request.config)
        if config.actions or config.policy_runtime is not None:
            raise ValueError('Automatic API runs require empty actions and no supplied runtime')
        scenario=config.scenario
        if scenario.channel is not None and scenario.channel.seed!=request.seed:
            raise ValueError('channel.seed must equal request.seed')
        if (config.evaluation_end_s>240 or len(scenario.tasks)>128 or
            max(len(scenario.true_windows),len(scenario.forecast_windows))>128):
            raise ValueError('API limits: 240 seconds, 128 tasks, 128 windows per profile')
        with self.lock:
            self.reap()
            if self.jobs: raise ServiceError(429,'CAPACITY_BUSY','One run is already active')
            identity='run_'+uuid4().hex;folder=self.root/identity;folder.mkdir()
            data=request.model_dump()
            _write_json(folder/'config.json',data)
            write_status(folder,'queued',progress=0.0)
            process=multiprocessing.get_context('spawn').Process(target=self.worker,args=(folder,data),daemon=True)
            try: process.start()
            except BaseException:
                fail_run(folder,'WORKER_START_FAILED')
                raise ServiceError(500,'INTERNAL_RUN_ERROR','Worker could not start')
            self.jobs[identity]=(process,time.monotonic())
            return dict(run_id=identity,status='queued',schema_version='1.0')

    def folder(self,identity):
        if not re.fullmatch(r'run_[0-9a-f]{32}',identity):
            raise ServiceError(404,'RUN_NOT_FOUND','Run not found')
        path=self.root/identity
        try: checked_file(path,'status.json')
        except ValueError: raise ServiceError(404,'RUN_NOT_FOUND','Run not found')
        if not (path/'status.json').is_file(): raise ServiceError(404,'RUN_NOT_FOUND','Run not found')
        return path

    def status(self,identity):
        folder=self.folder(identity)
        return RunStatusResponse.model_validate_json(read_text(folder/'status.json')).model_dump()

    def completed(self,identity):
        status=self.status(identity)
        if status['status']!='completed':
            raise ServiceError(409,'RUN_NOT_COMPLETE','Run is not complete',status=status['status'])
        return self.folder(identity)

    def events(self,identity,after,limit):
        query=EventsQuery(after=after,limit=limit);folder=self.folder(identity)
        path=checked_file(folder,'events.jsonl');rows=[]
        if path.exists():
            # Release the file before JSON validation so Windows publication is not blocked by parsing.
            for line in read_text(path).splitlines():
                row=Event.model_validate_json(line)
                if row.event_id>query.after: rows.append(row)
                if len(rows)>query.limit: break
        batch=rows[:query.limit]
        return EventsPage(run_id=identity,events=batch,next_after=batch[-1].event_id if batch else after,
                          has_more=len(rows)>query.limit).model_dump()

    def export(self,identity):
        folder=self.completed(identity)
        request=RunRequest.model_validate_json(checked_file(folder,'config.json').read_text(encoding='utf-8'))
        names=['config.json','manifest.json','status.json','events.jsonl','results.json']
        for policy in request.policy_ids:
            names += [f'{policy}/{n}' for n in ('config.json','manifest.json','status.json','results.json',
                'events.jsonl','execution.log','energy_ledger.json')]
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as package:
            for name in names: package.writestr(name,checked_file(folder,name).read_bytes())
        return output.getvalue()
