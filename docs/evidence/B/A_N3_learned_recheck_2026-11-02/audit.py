"""B's independent frozen inference, normalization and failure audit."""
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sys
import tempfile
from time import perf_counter, sleep

import numpy as np

source = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(source))
from backend.contracts import Observation, InFlight
from backend.policies.learned import score_actions, LearnedPolicyError, _load_bundle
from backend.policies.runner import ScorerGateway
from training.policy_features import encode_observation

load = lambda path: json.loads((source/path).read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()
package = source/'artifacts/models/a_n3_policy_v1'
rows = [json.loads(line) for line in (source/'data/teacher/a_n3_20_v2/samples.jsonl').read_bytes().splitlines()]
splits = load('data/teacher/a_n3_20_v2/splits.json')['splits']
normalization = json.loads((package/'normalization.json').read_bytes())
summary = json.loads((package/'training_summary.json').read_bytes())
observations = [Observation.model_validate(r['observation']) for r in rows]
encoded = {r['sample_id']: encode_observation(o) for r, o in zip(rows, observations)}
train_ids = splits['train']['sample_ids']
assert len(train_ids)==12 and len(rows)==20
for kind, values in [('global', [encoded[i].global_features for i in train_ids]),
                     ('candidate', [c for i in train_ids for c in encoded[i].candidate_features])]:
    values = np.asarray(values, dtype=np.float64)
    mean, scale = values.mean(axis=0), values.std(axis=0)
    scale[scale == 0] = 1
    np.testing.assert_allclose(mean, normalization[kind+'_mean'], rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(scale, normalization[kind+'_scale'], rtol=1e-12, atol=1e-12)
assert normalization['source_split']=='train'
seed = min(summary['seeds'], key=lambda s: (summary['seeds'][s]['metrics']['validation']['total_loss'], int(s)))
assert int(seed)==summary['selected_seed']==20261033
assert summary['test_evaluated_after_selection'] is True
details = []
for row, observation in zip(rows, observations):
    before = observation.model_dump_json()
    scores = score_actions(observation)
    expected = {(task.task_id, mode) for task in observation.tasks for mode in ('robust','fast')} | {(None,'idle')}
    assert len(scores)==len(expected) and {(s.task_id,s.mode) for s in scores}==expected
    assert all(np.isfinite(s.score) for s in scores)
    assert observation.model_dump_json()==before
    details.append(dict(sample_id=row['sample_id'], candidates=len(scores), finite=True, input_unchanged=True))
obs = observations[0]
masked = obs.model_copy(deep=True)
task = masked.tasks[0]
masked.inflight = InFlight.model_validate(dict(task_id=task.task_id, block_id=0, payload_bytes=min(task.remaining_bytes,1024),
    mode='fast', sent_at_s=0., timeout_at_s=2., retries=0))
masked = Observation.model_validate(masked.model_dump())
assert all(s.score==-1 for s in score_actions(masked) if s.mode!='idle')
empty = obs.model_copy(deep=True)
empty.tasks=[]; empty.cache_bytes=0; empty.inflight=None
assert [(s.task_id,s.mode) for s in score_actions(empty)]==[(None,'idle')]
probe = source/'runs/B_learned_failure_probe'
probe.mkdir(parents=True,exist_ok=True)
probe = Path(tempfile.mkdtemp(prefix='audit_',dir=probe))
runtime = load('configs/learned_policy.json')
failures = {}
for mode in ('missing','hash','format','nan'):
    target=probe/mode
    shutil.copytree(package,target)
    config=dict(runtime,package_dir=str(target))
    if mode=='missing': (target/'weights.npz').unlink()
    elif mode=='hash': config['weights_sha256']='f'*64
    elif mode=='format':
        (target/'weights.npz').write_bytes(b'not a NumPy archive')
        config['weights_sha256']=sha((target/'weights.npz').read_bytes())
    else:
        with np.load(target/'weights.npz',allow_pickle=False) as archive:
            arrays={name:archive[name].copy() for name in archive.files}
        arrays['layer1_bias'][0]=np.nan
        np.savez(target/'weights.npz',**arrays)
        config['weights_sha256']=sha((target/'weights.npz').read_bytes())
    try: score_actions(obs,config=config)
    except LearnedPolicyError as error: failures[mode]=error.code
    else: raise AssertionError(mode)
assert failures==dict(missing='MODEL_MISSING',hash='MODEL_HASH',format='MODEL_FORMAT',nan='MODEL_NONFINITE')
invalid=obs.model_copy(deep=True); invalid.sim_time_s=-1
try: score_actions(invalid)
except LearnedPolicyError as error: assert error.code=='INVALID_OBSERVATION'
else: raise AssertionError('Invalid input accepted')
def broken(_): raise RuntimeError('Independent scorer failure')
def slow(_): sleep(.05); return score_actions(obs)
fallbacks={}
for name, scorer, budget, reason in [('exception',broken,100,'MODEL_UNAVAILABLE'),('timeout',slow,5,'MODEL_TIMEOUT')]:
    decision=ScorerGateway(scorer,budget_ms=budget).decide(obs)
    assert decision.fallback and reason in decision.action.reason_codes
    fallbacks[name]=dict(fallback=True,reason=reason)
sleep(.06)  # Let the bounded test callback finish; this is not production process isolation.
_load_bundle.cache_clear()
start=perf_counter();score_actions(obs);cold=(perf_counter()-start)*1000
times=[]
for _ in range(1000):
    start=perf_counter();score_actions(obs);times.append((perf_counter()-start)*1000)
report=dict(candidate='1c90246376b91fb789154b22530b25bab2142b7e', observations=details,
    train_normalization_independently_recomputed=True, selection_by_validation_verified=True,
    test_once_evidence='Source control-flow and frozen summary reviewed; historical execution count not independently provable from artifacts',
    structural_inflight_mask_verified=True, empty_candidates_idle_verified=True,
    failures=failures, invalid_input_controlled=True, fallbacks=fallbacks,
    latency_ms=dict(cold_load_first_score=cold,warm_calls=1000,median=float(np.median(times)),p95=float(np.percentile(times,95)),maximum=max(times)),
    environment=dict(python=platform.python_version(),numpy=np.__version__,pydantic=importlib.metadata.version('pydantic')),
    scope='Synthetic frozen small-sample inference and interface behavior; not policy runner/API integration or generalization')
(out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:report[key] for key in ('train_normalization_independently_recomputed','failures','fallbacks','latency_ms')}))
