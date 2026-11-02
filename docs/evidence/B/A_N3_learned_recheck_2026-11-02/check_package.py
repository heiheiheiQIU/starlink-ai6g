"""Read-only package identity/format intake; does not run model code or training."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

repo = Path(__file__).resolve().parents[4]
snapshot = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
revision = '1c90246376b91fb789154b22530b25bab2142b7e'
package = snapshot / 'artifacts/models/a_n3_policy_v1'
verification = json.loads((snapshot/'docs/evidence/A/A_N3_training_2026-10-31/verification.json').read_bytes())
manifest = json.loads((package/'manifest.json').read_bytes())
runtime = json.loads((snapshot/'configs/learned_policy.json').read_bytes())
sha = lambda data: hashlib.sha256(data).hexdigest()
files = {}
for name, expected in verification['package_sha256'].items():
    path = package/name
    raw = path.read_bytes()
    assert sha(raw) == expected, name
    relative = path.relative_to(snapshot).as_posix()
    assert raw == subprocess.check_output(['git', '-C', str(repo), 'show', revision+':'+relative])
    files[name] = dict(sha256=sha(raw), bytes=len(raw))
assert len(files) == 5
for name, digest in manifest['artifacts_sha256'].items():
    assert files[name]['sha256'] == digest
assert runtime['weights_sha256'] == files['weights.npz']['sha256']
assert runtime['normalization_sha256'] == files['normalization.json']['sha256']
configs = {}
for name, expected in [('learned_policy.json', verification['runtime_config_sha256']),
                       ('policy_train.json', verification['training_config_sha256'])]:
    configs[name] = sha((snapshot/'configs'/name).read_bytes())
    assert configs[name] == expected
assert configs['policy_train.json'] == manifest['config_sha256']
shapes = {'layer1_weight': (32, 23), 'layer1_bias': (32,),
          'layer2_weight': (16, 32), 'layer2_bias': (16,),
          'utility_weight': (1, 16), 'utility_bias': (1,),
          'feasibility_weight': (1, 16), 'feasibility_bias': (1,)}
arrays = {}
with np.load(package/'weights.npz', allow_pickle=False) as archive:
    assert set(archive.files) == set(shapes) == set(manifest['array_names'])
    for name, shape in shapes.items():
        value = archive[name]
        assert value.shape == shape and value.dtype == np.float32 and np.isfinite(value).all()
        arrays[name] = dict(shape=list(shape), dtype=str(value.dtype), finite=True)
frozen = {}
for name, expected in [('backend/contracts.py', verification['frozen_interfaces']['contracts_sha256']),
                       ('configs/schema.json', verification['frozen_interfaces']['schema_sha256']),
                       ('data/teacher/a_n3_20_v2/samples.jsonl', verification['data']['samples_sha256']),
                       ('data/teacher/a_n3_20_v2/splits.json', verification['data']['split_sha256'])]:
    frozen[name] = sha((snapshot/name).read_bytes())
    assert frozen[name] == expected
identity = json.loads((repo/'docs/evidence/B/API_lock_2026-11-01/patch_identity.json').read_bytes())
for path, hashes in identity['paths'].items():
    assert sha((snapshot/path).read_bytes()) == hashes['after_sha256'], path
report = dict(candidate=revision, pr=8, status='static_intake_passed_pending_functional_review',
              package=files, configs=configs, arrays=arrays, frozen=frozen,
              API_patch_identity_matches=True, functional_tests_run=False, model_accepted=False)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(files_verified=len(files), arrays_verified=len(arrays), API_patch_matches=True,
                     status=report['status'])))
