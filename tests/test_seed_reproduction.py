"""Run the seed verifier in a clean source copy with no pre-created runs."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.parametrize('outside_cwd', [False, True])
def test_seed_verifier_clean_copy_and_repeat(tmp_path, outside_cwd):
    source = Path(__file__).resolve().parents[1]
    release = tmp_path / 'release'
    release.mkdir()
    for name in ('backend', 'tests', 'configs', 'scripts'):
        shutil.copytree(source / name, release / name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(source / 'pyproject.toml', release / 'pyproject.toml')
    assert not (release / 'runs').exists()
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, str(release / 'scripts/verify_seed_p2.py')],
            cwd=tmp_path if outside_cwd else release,
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        record = json.loads((release / 'runs/seed_p2_reproduction/actual/verification.json').read_text())
        assert record['seed'] == 7
        assert record['zip_seed_checked'] and record['artifact_hashes_verified']
        assert record['request_unmodified']
