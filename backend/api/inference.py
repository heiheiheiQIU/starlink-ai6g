"""Frozen-package identity and one bounded, supervised scorer per run."""
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
from queue import Empty, Full
import time

from backend.contracts import Observation
from .processes import ProcessGroup, wait_for_start, pid_alive, stop_process


FROZEN_MANIFESTS = {
    'a-n3-mlp-v1': '949370f65165437a95b5858b23103b6cac892913592d1a4b54a3d3d4d27445a8',
}


class InferenceFailure(RuntimeError):
    def __init__(self, code):
        super().__init__(code); self.code = code


def inspect_model(config=None):
    from backend.policies import learned
    cfg = learned._config(config)
    package = Path(cfg['package_dir'])
    try:
        manifest_bytes=(package/'manifest.json').read_bytes()
        manifest_hash=hashlib.sha256(manifest_bytes).hexdigest()
        if manifest_hash != FROZEN_MANIFESTS.get(cfg['model_version']):
            raise ValueError('Unrecognized frozen manifest')
        manifest = json.loads(manifest_bytes)
        if manifest['schema_version'] != 'policy-model-manifest-v1': raise ValueError('Invalid model schema')
        if (manifest['model_version'] != cfg['model_version'] or
                manifest['feature_schema_version'] != cfg['feature_schema_version']):
            raise ValueError('Model metadata mismatch')
        files = manifest['artifacts_sha256']
        if set(files) != {'weights.npz','normalization.json','training_summary.json','model_card.md'}:
            raise ValueError('Incomplete model package')
        hashes = {}
        for name, digest in files.items():
            raw = (package/name).read_bytes()
            hashes[name] = hashlib.sha256(raw).hexdigest()
            if hashes[name] != digest: raise ValueError('Model package hash mismatch')
        hashes['manifest.json'] = manifest_hash
        if hashes['weights.npz'] != cfg['weights_sha256'] or hashes['normalization.json'] != cfg['normalization_sha256']:
            raise ValueError('Runtime model hash mismatch')
        learned._bundle(cfg)  # Validate shapes, dtype, finite arrays and train normalization.
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise InferenceFailure('MODEL_UNAVAILABLE') from error
    return dict(model_hash=cfg['weights_sha256'], model_version=cfg['model_version'],
                feature_schema_version=cfg['feature_schema_version'], artifacts_sha256=hashes,
                normalization_sha256=cfg['normalization_sha256'])


def _score_loop(requests, responses, config, scorer, gate, parent_pid):
    wait_for_start(gate, parent_pid)
    responses.cancel_join_thread()
    started = time.perf_counter()
    try:
        from backend.policies import learned
        learned._bundle(config)
        responses.put(('ready', (time.perf_counter()-started)*1000), timeout=1)
    except BaseException:
        responses.put(('load_error', None), timeout=1); return
    while True:
        request = requests.get()
        if request is None: return
        token, observation = request
        try:
            observed = Observation.model_validate(observation)
            scores = scorer(observed) if scorer is not None else learned.score_actions(observed, config=config)
            values = [s.model_dump() if hasattr(s, 'model_dump') else s for s in scores]
            responses.put((token, True, values), timeout=1)
        except BaseException:
            responses.put((token, False, None), timeout=1)


class InferenceClient:
    def __init__(self, requests, responses, failed, pid, identity, budget_ms):
        self.requests=requests; self.responses=responses; self.failed=failed
        self.pid=pid; self.identity=identity; self.budget_ms=budget_ms; self.sequence=0

    def __call__(self, observation):
        if self.failed.is_set(): raise InferenceFailure('MODEL_UNAVAILABLE')
        self.requests.cancel_join_thread()  # A killed reader must not stall worker shutdown.
        self.sequence += 1
        observed = Observation.model_validate(observation).model_dump(mode='json')
        digest = hashlib.sha256(json.dumps(observed, sort_keys=True, separators=(',',':')).encode()).hexdigest()
        token = (self.identity, self.sequence, digest)
        deadline = time.monotonic()+self.budget_ms/1000
        try:
            self.requests.put((token, observed), timeout=max(0.0, deadline-time.monotonic()))
            while time.monotonic() < deadline:
                if not pid_alive(self.pid): raise InferenceFailure('MODEL_UNAVAILABLE')
                try: reply = self.responses.get(timeout=min(.01, max(0.0, deadline-time.monotonic())))
                except Empty: continue
                if len(reply) != 3 or reply[0] != token: raise InferenceFailure('MODEL_UNAVAILABLE')
                if not reply[1]: raise InferenceFailure('MODEL_UNAVAILABLE')
                return reply[2]
            if not pid_alive(self.pid): raise InferenceFailure('MODEL_UNAVAILABLE')
            raise InferenceFailure('MODEL_TIMEOUT')
        except (Empty, Full, EOFError, OSError) as error:
            self.failed.set(); raise InferenceFailure('MODEL_UNAVAILABLE') from error
        except InferenceFailure:
            self.failed.set(); raise


class InferenceSupervisor:
    def __init__(self, *, model_config=None, scorer=None, budget_ms=100.0, identity='standalone', startup_s=15.0):
        if not math.isfinite(budget_ms) or budget_ms <= 0: raise ValueError('Positive finite inference budget required')
        from backend.policies.learned import _config
        self.config = _config(model_config)
        self.metadata = inspect_model(self.config)
        self.scorer=scorer; self.budget_ms=budget_ms; self.identity=identity; self.startup_s=startup_s
        self.context=multiprocessing.get_context('spawn')
        self.requests=self.context.Queue(maxsize=1); self.responses=self.context.Queue(maxsize=1)
        self.failed=self.context.Event(); self.gate=self.context.Event()
        self.group=None; self.process=None; self.client=None; self.exitcode=None; self.load_ms=None

    def start(self):
        self.group=ProcessGroup()
        self.process=self.context.Process(target=_score_loop,args=(self.requests,self.responses,self.config,self.scorer,self.gate,os.getpid()),daemon=True)
        try:
            self.process.start(); self.group.add(self.process); self.gate.set()
            ready=self.responses.get(timeout=self.startup_s)
            if ready[0] != 'ready': raise InferenceFailure('MODEL_UNAVAILABLE')
            self.load_ms=ready[1]
            self.client=InferenceClient(self.requests,self.responses,self.failed,self.process.pid,self.identity,self.budget_ms)
            return self
        except BaseException:
            self.close(); raise

    def reap(self):
        if self.failed.is_set() and self.process is not None and not self.process._closed:
            stop_process(self.process)

    def close(self):
        self.failed.set()
        if self.process is not None and not self.process._closed:
            if self.process.pid is not None:
                stop_process(self.process); self.exitcode=self.process.exitcode
            self.process.close()
        if self.group is not None: self.group.close()
        for queue in (self.requests,self.responses):
            queue.cancel_join_thread(); queue.close()

    def __enter__(self): return self.start()
    def __exit__(self, *args): self.close()
