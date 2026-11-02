import json
from pathlib import Path
import pytest
from backend.experiments import build_config,run_matrix
from backend.cli import RunConfig


def matrix():return json.loads(Path('experiments/test_matrix.json').read_text(encoding='utf-8'))


def test_all_registered_synthetic_configs_are_valid_and_cover_counterexample():
    planned=matrix();cells={c['cell_id']:c for c in planned['cells']}
    assert len(planned['trajectories'])==180
    for trace in planned['trajectories']:
        data=build_config(cells[trace['cell_id']],trace['environment_seed'])
        parsed=RunConfig.model_validate(data)
        assert parsed.scenario.channel.seed==trace['environment_seed']
        health=parsed.scenario.health_observations[0]
        assert health.energy_lower_Wh==pytest.approx(parsed.scenario.initial_energy_Wh)
    subset=json.loads(Path('experiments/optimizer_subset.json').read_text())['trajectory_ids']
    assert len(subset)==54 and len(set(subset))==54
    assert {t['cell_id'] for t in planned['trajectories'] if t['trajectory_id'] in subset}==set(cells)


def test_paired_runs_share_inputs_seed_and_reproduce_scientific_metrics(tmp_path):
    for name in ('left','right'):
        summary=run_matrix(Path('experiments/test_matrix.json'),tmp_path/name,limit=2)
        assert summary['trajectory_count']==2 and summary['policy_run_count']==4
        for folder in (tmp_path/name/'runs').iterdir():
            left=json.loads((folder/'edf/results.json').read_text())
            right=json.loads((folder/'value/results.json').read_text())
            assert left['input_hash']==right['input_hash'] and left['seed']==right['seed']!=0
    a=json.loads((tmp_path/'left/summary.json').read_text())
    b=json.loads((tmp_path/'right/summary.json').read_text())
    assert a==b
    identity=matrix()['trajectories'][0]['trajectory_id']
    left=json.loads((tmp_path/'left/runs'/identity/'edf/results.json').read_text())
    right=json.loads((tmp_path/'right/runs'/identity/'edf/results.json').read_text())
    assert left['run_id']!=right['run_id']
    assert (tmp_path/'left/per_run.csv').exists()
