"""Receiver regression: genuine damaged ZIP must be a controlled model error."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

import pytest

REPO = Path(__file__).resolve().parents[4]
SOURCE = Path(os.environ.get('B_LEARNED_SOURCE', str(REPO/'runs/b_learned_intake_20261101/source')))
sys.path.insert(0, str(SOURCE))
from backend.contracts import Observation
from backend.policies.learned import LearnedPolicyError, score_actions


def test_damaged_zip_is_controlled_model_format(tmp_path):
    package = tmp_path/'model'
    shutil.copytree(SOURCE/'artifacts/models/a_n3_policy_v1', package)
    # Valid ZIP signature followed by a damaged archive, not plain non-ZIP text.
    raw = b'PK\x03\x04broken archive payload'
    (package/'weights.npz').write_bytes(raw)
    config = json.loads((SOURCE/'configs/learned_policy.json').read_bytes())
    config.update(package_dir=str(package), weights_sha256=hashlib.sha256(raw).hexdigest())
    row = json.loads((SOURCE/'data/teacher/a_n3_20_v2/samples.jsonl').read_text(encoding='utf-8').splitlines()[0])
    with pytest.raises(LearnedPolicyError) as error:
        score_actions(Observation.model_validate(row['observation']), config=config)
    assert error.value.code == 'MODEL_FORMAT'
