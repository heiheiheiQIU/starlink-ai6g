import json
from pathlib import Path
import pytest
from backend.cli import RunConfig, run_experiment
from backend.contracts import RunResult
from tests.test_protocol import config, send, loss_config


def run_config(data=None, actions=None, end=7.0):
    return dict(schema_version='1.0',kind='manual_validation',scenario=data or config(deadline=5.0),
        evaluation_end_s=end,actions=actions if actions is not None else [dict(time_s=0.0,action=send().model_dump())])


def test_completed_run_six_files_hashes_and_reproducible_scientific_outputs(tmp_path):
    left,right=tmp_path/'left',tmp_path/'right'
    for folder in (left,right):
        result=run_experiment(run_config(),folder,run_id='reproducible')
        RunResult.model_validate(result)
        assert result['by_policy'][0]['weighted_on_time_rate']==1.0
        assert {p.name for p in folder.iterdir()} >= {'config.json','manifest.json','status.json','events.jsonl','results.json','execution.log'}
        assert json.loads((folder/'status.json').read_text())['status']=='completed'
        manifest=json.loads((folder/'manifest.json').read_text())
        assert manifest['kind']=='manual_validation' and manifest['source']=='synthetic'
        assert manifest['model_hash'] is None
        import hashlib
        for name,digest in manifest['artifacts_sha256'].items():
            assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest
    for name in ('events.jsonl','results.json','energy_ledger.json'):
        assert (left/name).read_bytes()==(right/name).read_bytes()
    with pytest.raises(ValueError): run_experiment(run_config(),left)


def test_failure_keeps_failed_status_and_no_formal_results(tmp_path,monkeypatch):
    import backend.cli as cli
    def fail(*args): raise RuntimeError('injected evaluation failure')
    monkeypatch.setattr(cli,'evaluate',fail)
    output=tmp_path/'failed'
    with pytest.raises(RuntimeError): run_experiment(run_config(),output)
    status=json.loads((output/'status.json').read_text())
    assert status['status']=='failed' and status['error']['code']=='INTERNAL_RUN_ERROR'
    assert not (output/'results.json').exists()
    assert 'failed' in (output/'execution.log').read_text()


def test_config_rejects_wrong_stage_unordered_actions_and_zero_horizon():
    for mutation in ('stage','actions','end','control'):
        value=run_config()
        if mutation=='stage': value['scenario'].pop('protocol')
        elif mutation=='actions': value['actions']*=2
        elif mutation=='end': value['evaluation_end_s']=0.0
        else: value['scenario']['protocol']['control_bps']=1.0
        with pytest.raises(ValueError): RunConfig.model_validate(value)


def test_cli_module_actual_command(tmp_path):
    import subprocess,sys
    path=tmp_path/'input.json'; path.write_text(json.dumps(run_config()),encoding='utf-8')
    output=tmp_path/'output'
    process=subprocess.run([sys.executable,'-m','backend.cli','run','--config',str(path),'--output',str(output)],
                            capture_output=True,text=True)
    assert process.returncode==0,process.stderr
    assert json.loads((output/'results.json').read_text())['status']=='completed'


def test_keyboard_interrupt_after_results_leaves_failed_status(tmp_path,monkeypatch):
    import backend.cli as cli
    original=cli._write_json
    def interrupted(path,value):
        if path.name=='manifest.json': raise KeyboardInterrupt()
        original(path,value)
    monkeypatch.setattr(cli,'_write_json',interrupted)
    output=tmp_path/'interrupted'
    with pytest.raises(KeyboardInterrupt): run_experiment(run_config(),output)
    assert json.loads((output/'status.json').read_text())['status']=='failed'
    assert not (output/'results.json').exists()
    assert (output/'results.partial.json').exists()
