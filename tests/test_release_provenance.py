"""Release copies nested in another checkout must not inherit its revision."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.parametrize('entry',['cli','teacher'])
def test_nested_release_does_not_claim_parent_revision(tmp_path,entry):
    if shutil.which('git') is None:pytest.skip('Nested Git repository test requires Git')
    subprocess.run(['git','init',str(tmp_path)],check=True,capture_output=True)
    subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                    '-c','commit.gpgsign=false','commit','--allow-empty','-m','parent fixture'],
                   cwd=tmp_path,check=True,capture_output=True)
    root=Path(__file__).resolve().parents[1]
    release=tmp_path/'release';release.mkdir()
    shutil.copytree(root/'backend',release/'backend',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(root/'configs',release/'configs')
    env=os.environ.copy();env.pop('GIT_CEILING_DIRECTORIES',None)
    if entry=='cli':
        command=['backend.cli','run','--config','configs/scenarios/r3_normal.json','--output','output']
    else:command=['backend.policies.teacher','--preflight','--output','output']
    process=subprocess.run([sys.executable,'-m',*command],cwd=release,env=env,capture_output=True,text=True)
    assert process.returncode==0,process.stderr
    manifest=json.loads((release/'output/manifest.json').read_text())
    assert manifest['code_revision'].startswith('unversioned-source-sha256:')
    if entry=='cli':
        assert json.loads((release/'output/results.json').read_text())['code_revision']==manifest['code_revision']
