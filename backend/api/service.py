"""Single-server process supervisor and bounded read/export operations."""
import io
import hashlib
import json
import multiprocessing
import os
import re
import threading
import time
import zipfile
from pathlib import Path
from uuid import uuid4

from backend.cli import RunConfig, _write_json
from backend.contracts import EventsPage, EventsQuery, Event, RunRequest, RunStatusResponse
from .worker import execute_run, fail_run, write_status, read_text
from .inference import InferenceSupervisor
from .processes import ProcessGroup, run_owned, stop_process


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
    def __init__(self,root,*,worker=execute_run,timeout_s=120.0,model_config=None,inference_factory=InferenceSupervisor):
        if timeout_s<=0: raise ValueError('Positive worker timeout required')
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.worker=worker;self.timeout_s=timeout_s;self.jobs={};self.lock=threading.RLock()
        self.stopping=threading.Event();self.monitor=None
        self.model_config=model_config;self.inference_factory=inference_factory
        self.inference_jobs={};self.process_groups={}
        self.terminal_overrides={};self.last_supervision_error=None

    def start(self):
        # Single service owns this root; unfinished records from an earlier stop fail honestly.
        for folder in [*self.root.iterdir(), *self.root.glob('sandbox/*')]:
            if folder.is_dir() and re.fullmatch(r'(?:sandbox_)?run_[0-9a-f]{32}',folder.name):
                try: checked_file(self.root,folder.relative_to(self.root))
                except ValueError: continue  # Never recover through an external link.
                try: state=self.status(folder.name)
                except (ServiceError,ValueError,OSError):
                    fail_run(folder,'INCOMPLETE_RUN_RECORD')
                    continue
                if state['status'] in ('queued','running'): fail_run(folder,'SERVICE_RESTARTED')
        self.monitor=threading.Thread(target=self._watch,daemon=True);self.monitor.start()

    def _watch(self):
        while not self.stopping.wait(.05):
            with self.lock:
                try: self.reap()
                except (OSError,ValueError,RuntimeError,ServiceError) as error:
                    self.last_supervision_error=type(error).__name__

    def _release_inference(self, identity):
        supervisor=self.inference_jobs.pop(identity,None)
        if supervisor is not None: supervisor.close()
        group=self.process_groups.pop(identity,None)
        if group is not None: group.close()

    def reap(self):
        for supervisor in self.inference_jobs.values(): supervisor.reap()
        for identity,(process,started) in list(self.jobs.items()):
            folder=checked_file(self.root,Path('sandbox' if identity.startswith('sandbox_') else '')/identity)
            expired=time.monotonic()-started>self.timeout_s
            if expired and process.is_alive(): stop_process(process)
            if expired or not process.is_alive():
                process.join(3)
                try:
                    state=json.loads(read_text(folder/'status.json'))
                    if state['status'] not in ('completed','failed','cancelled'):
                        fail_run(folder,'WORKER_TIMEOUT' if expired else 'WORKER_EXITED')
                except (OSError,ValueError) as error:
                    self.last_supervision_error=type(error).__name__
                    terminal=RunStatusResponse(run_id=identity,status='failed',progress=None,active_policies=[],
                        error=dict(code='INTERNAL_RUN_ERROR',message='Run status is unavailable',details={'reason':'STATUS_UNAVAILABLE'}))
                    self.terminal_overrides[identity]=terminal.model_dump()
                    try: fail_run(folder,'STATUS_UNAVAILABLE')
                    except OSError: pass
                finally:
                    self._release_inference(identity)
                    process.close();del self.jobs[identity]

    def close(self):
        self.stopping.set()
        if self.monitor: self.monitor.join(2)
        with self.lock:
            for identity,(process,_) in list(self.jobs.items()):
                stop_process(process)
                folder=checked_file(self.root,Path('sandbox' if identity.startswith('sandbox_') else '')/identity)
                try:
                    if self.status(identity)['status'] not in ('completed','failed','cancelled'):
                        fail_run(folder,'SERVICE_STOPPED')
                finally:
                    self._release_inference(identity)
                    process.close();del self.jobs[identity]
            self.jobs.clear()
            for identity in list(self.inference_jobs): self._release_inference(identity)

    def submit(self,payload):
        request=RunRequest.model_validate(payload)
        if any(p not in ('edf','value','learned') for p in request.policy_ids):
            raise ValueError('Supported policies: edf, value, learned')
        sandbox = request.config.get('kind') == 'sandbox_axes'
        if sandbox:
            from backend.sandbox import SandboxRequest, compile_sandbox_axes
            axes = SandboxRequest.model_validate(request.config)
            compiled = compile_sandbox_axes(axes.axes, request.seed)
        else:
            compiled = request.config
        config=RunConfig.model_validate(compiled)
        if config.seed is not None and config.seed!=request.seed:
            raise ValueError('config.seed must equal request.seed')
        if config.actions or config.policy_runtime is not None:
            raise ValueError('Automatic API runs require empty actions and no supplied runtime')
        scenario=config.scenario
        if scenario.channel is not None and scenario.channel.seed!=request.seed:
            raise ValueError('channel.seed must equal request.seed')
        if (config.evaluation_end_s>240 or len(scenario.tasks)>128 or
            max(len(scenario.true_windows),len(scenario.forecast_windows))>128):
            raise ValueError('API limits: 240 seconds, 128 tasks, 128 windows per profile')
        if 'learned' in request.policy_ids:
            from .inference import inspect_model
            try: inspect_model(self.model_config)
            except (ValueError,RuntimeError,OSError) as error:
                raise ServiceError(422,'INVALID_CONFIG','Frozen learned model package is unavailable',reason='MODEL_UNAVAILABLE') from error
        with self.lock:
            self.reap()
            if self.jobs: raise ServiceError(429,'CAPACITY_BUSY','One run is already active')
            identity=('sandbox_run_' if sandbox else 'run_')+uuid4().hex
            folder=checked_file(self.root,Path('sandbox' if sandbox else '')/identity)
            folder.mkdir(parents=True)
            data=request.model_dump()
            _write_json(folder/'config.json',data)
            if sandbox:
                from backend.cli import _hash
                from backend import sandbox as compiler
                _write_json(folder/'compiled_config.json',compiled)
                _write_json(folder/'sandbox.json',dict(source='synthetic/sandbox',
                    compiler_version=axes.compiler_version, axes=axes.axes.model_dump(),
                    config_hash=_hash(compiled),
                    compiler_sha256=hashlib.sha256(Path(compiler.__file__).read_bytes()).hexdigest()))
            write_status(folder,'queued',progress=0.0)
            context=multiprocessing.get_context('spawn');gate=context.Event()
            process=None
            try:
                supervisor=None
                if 'learned' in request.policy_ids:
                    supervisor=self.inference_factory(model_config=self.model_config,identity=identity).start()
                    self.inference_jobs[identity]=supervisor
                args=(folder,data)
                if self.worker is execute_run and supervisor is not None:
                    args=(*args,supervisor.client,supervisor.metadata,supervisor.load_ms)
                group=ProcessGroup();self.process_groups[identity]=group
                process=context.Process(target=run_owned,args=(self.worker,args,gate,os.getpid()),daemon=True)
                process.start();group.add(process);gate.set()
            except BaseException:
                if process is not None and process.pid is not None:
                    stop_process(process);process.close()
                self._release_inference(identity)
                fail_run(folder,'WORKER_START_FAILED')
                raise ServiceError(500,'INTERNAL_RUN_ERROR','Worker could not start')
            self.jobs[identity]=(process,time.monotonic())
            return dict(run_id=identity,status='queued',schema_version='1.0')

    def folder(self,identity):
        if not re.fullmatch(r'(?:sandbox_)?run_[0-9a-f]{32}',identity):
            raise ServiceError(404,'RUN_NOT_FOUND','Run not found')
        path=checked_file(self.root,Path('sandbox' if identity.startswith('sandbox_') else '')/identity)
        try: checked_file(path,'status.json')
        except ValueError: raise ServiceError(404,'RUN_NOT_FOUND','Run not found')
        if not (path/'status.json').is_file(): raise ServiceError(404,'RUN_NOT_FOUND','Run not found')
        return path

    def status(self,identity):
        if identity in self.terminal_overrides: return self.terminal_overrides[identity].copy()
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
        if request.config.get('kind') == 'sandbox_axes':
            names += ['compiled_config.json','sandbox.json']
        for policy in request.policy_ids:
            names += [f'{policy}/{n}' for n in ('config.json','manifest.json','status.json','results.json',
                'events.jsonl','execution.log','energy_ledger.json')]
        contents={name:checked_file(folder,name).read_bytes() for name in names}
        root_manifest=json.loads(contents['manifest.json'])
        if not isinstance(root_manifest,dict) or not isinstance(root_manifest.get('artifacts_sha256'),dict):
            raise ValueError('Invalid root manifest')
        expected=set(names)-{'manifest.json','status.json'}
        if set(root_manifest['artifacts_sha256'])!=expected: raise ValueError('Incomplete export manifest')
        for name,digest in root_manifest['artifacts_sha256'].items():
            if hashlib.sha256(contents[name]).hexdigest()!=digest: raise ValueError('Corrupt export artifact')
        for policy in request.policy_ids:
            manifest=json.loads(contents[policy+'/manifest.json'])
            if not isinstance(manifest,dict) or not isinstance(manifest.get('artifacts_sha256'),dict):
                raise ValueError('Invalid child manifest')
            expected={'config.json','events.jsonl','results.json','execution.log','energy_ledger.json'}
            if set(manifest['artifacts_sha256'])!=expected: raise ValueError('Incomplete child manifest')
            for name,digest in manifest['artifacts_sha256'].items():
                if hashlib.sha256(contents[policy+'/'+name]).hexdigest()!=digest: raise ValueError('Corrupt child artifact')
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as package:
            for name in names: package.writestr(name,contents[name])
        return output.getvalue()
