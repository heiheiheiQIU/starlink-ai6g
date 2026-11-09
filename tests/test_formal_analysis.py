import copy
import json
from pathlib import Path

import pytest


def input_rows(delta=.1):
    trajectories = []
    rows = []
    for cell in range(18):
        for index in range(10):
            identity = f't{cell:02d}_{index:02d}'
            trajectories.append(dict(trajectory_id=identity, cell_id=f'cell_{cell:02d}'))
            for policy, rate in [('edf', .4), ('value', .3), ('learned', .4+delta)]:
                rows.append(dict(trajectory_id=identity, cell_id=f'cell_{cell:02d}', policy_id=policy,
                                 status='completed', attempt=1, weighted_on_time_rate=rate))
    return trajectories, rows


def protocol():
    return json.loads(Path('experiments/formal_v1/analysis_protocol.json').read_text())


@pytest.mark.parametrize('delta,want', [(.1, '胜'), (-.1, '负'), (0, '未检出稳定差异')])
def test_known_paired_differences_and_unsigned_public_verdict(delta, want):
    from experiments.analyze_formal import summarize_pairs
    summary = summarize_pairs(*input_rows(delta), protocol())
    comparison = summary['comparisons']['learned-edf']
    assert comparison['overall']['mean_delta'] == pytest.approx(delta)
    assert comparison['overall']['ci95'] == pytest.approx([delta, delta])
    assert comparison['statistical_verdict'] == want
    assert comparison['formal_verdict'] == '未完成'
    assert comparison['paired_count'] == 180
    assert summary['missing_policy_runs'] == 0


def test_zero_endpoint_and_crossing_interval_are_not_equivalence():
    from experiments.analyze_formal import classify
    for mean, interval in [(0, [-.1, .1]), (.01, [0, .02]), (-.01, [-.02, 0]), (0, [0, 0])]:
        assert classify(mean, interval) == '未检出稳定差异'


def test_input_order_does_not_change_fixed_seed_statistics():
    from experiments.analyze_formal import summarize_pairs
    traces, rows = input_rows()
    for row in rows:
        if row['policy_id'] == 'learned': row['weighted_on_time_rate'] = .1+int(row['trajectory_id'][-2:])*.07
    first = summarize_pairs(traces, rows, protocol())
    assert summarize_pairs(list(reversed(traces)), list(reversed(rows)), protocol()) == first


@pytest.mark.parametrize('bad', ['duplicate', 'nan', 'null', 'unknown', 'out_of_range'])
def test_invalid_success_records_are_rejected(bad):
    from experiments.analyze_formal import summarize_pairs
    traces, rows = input_rows()
    if bad == 'duplicate': rows.append(copy.deepcopy(rows[0]))
    elif bad == 'unknown': rows[0]['trajectory_id'] = 'absent'
    else: rows[0]['weighted_on_time_rate'] = {'nan': float('nan'), 'null': None, 'out_of_range': 2}[bad]
    with pytest.raises(ValueError): summarize_pairs(traces, rows, protocol())


def test_missing_cell_remains_in_denominator_and_verdict_incomplete():
    from experiments.analyze_formal import summarize_pairs
    traces, rows = input_rows()
    rows = [r for r in rows if r['cell_id'] != 'cell_00']
    summary = summarize_pairs(traces, rows, protocol())
    pair = summary['comparisons']['learned-edf']
    assert summary['missing_policy_runs'] == 30
    assert len(pair['cells']) == 18
    assert pair['cells'][0]['n'] == 0 and pair['cells'][0]['missing'] == 10
    assert pair['overall']['mean_delta'] is None
    assert pair['statistical_verdict'] == '未完成'


def test_unequal_available_sample_counts_do_not_change_equal_cell_weight():
    from experiments.analyze_formal import summarize_pairs
    traces, rows = input_rows(0)
    rows = [r for r in rows if r['cell_id'] != 'cell_00' or r['trajectory_id'] == 't00_00']
    for row in rows:
        if row['cell_id'] == 'cell_00': row['weighted_on_time_rate'] = 1 if row['policy_id'] == 'learned' else 0
    pair = summarize_pairs(traces, rows, protocol())['comparisons']['learned-edf']
    assert pair['overall']['mean_delta'] == pytest.approx(1/18)
    assert pair['overall']['ci95'] is None
    assert pair['statistical_verdict'] == '未完成'


def test_failure_and_retry_are_not_independent_samples():
    from experiments.analyze_formal import summarize_pairs
    traces, rows = input_rows()
    original = rows[0]
    rows[0] = dict(original, status='failed', weighted_on_time_rate=None)
    rows.append(dict(original, attempt=2))
    summary = summarize_pairs(traces, rows, protocol())
    assert summary['completed_policy_runs'] == 540
    assert summary['failed_attempts'] == 1
    assert summary['comparisons']['learned-edf']['paired_count'] == 180


def test_analyzer_reads_actual_run_artifacts_and_exports_incomplete(tmp_path):
    from backend.formal_freeze import freeze_inputs
    from backend.formal_experiments import run_formal
    from experiments.analyze_formal import analyze_runs
    from tests.test_formal_freeze import make_review
    freeze_inputs(*make_review(tmp_path), tmp_path/'frozen')
    manifest = tmp_path/'frozen/manifest.json'
    run_formal(manifest, tmp_path/'batch', trajectory_ids=['formal_v1_cell_00_trace_00'])
    result = analyze_runs(manifest, tmp_path/'batch/run_index.jsonl', tmp_path/'analysis')
    assert result['data_scope'] == 'test_fixture'
    assert result['completed_policy_runs'] == 3
    assert result['comparisons']['learned-edf']['formal_verdict'] == '未完成'
    assert (tmp_path/'analysis/paired_deltas.csv').exists()
    assert (tmp_path/'analysis/failure_ledger.csv').exists()
    assert result['inference']['requests'] > 0
    assert result['provenance']['run_index_sha256']
    assert len(result['comparisons']['learned-edf']['cells']) == 18
