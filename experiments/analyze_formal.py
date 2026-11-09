"""Deterministic paired bootstrap; unsigned results always remain incomplete."""
import argparse
from collections import defaultdict
import csv
import math
from pathlib import Path

import numpy as np

from backend.formal_experiments import read_run_index
from backend.formal_freeze import (POLICIES, file_hash, read_json, validate_analysis_protocol,
                                   verify_frozen, write_json)


def classify(mean, interval):
    if mean is None or interval is None: return '未完成'
    if mean > 0 and interval[0] > 0: return '胜'
    if mean < 0 and interval[1] < 0: return '负'
    return '未检出稳定差异'


def summarize_pairs(trajectories, rows, protocol):
    validate_analysis_protocol(protocol)
    traces = {t['trajectory_id']: t for t in trajectories}
    cells = defaultdict(list)
    for identity, trace in sorted(traces.items()): cells[trace['cell_id']].append(identity)
    if len(traces) != len(trajectories) or len(traces) != 180 or len(cells) != 18 or any(len(v) != 10 for v in cells.values()):
        raise ValueError('Expected 18 cells with 10 unique trajectories each')
    attempts = {}; histories = defaultdict(list)
    for row in rows:
        identity, policy, attempt = row['trajectory_id'], row['policy_id'], row['attempt']
        key = (identity, policy, attempt)
        if (identity not in traces or policy not in POLICIES or type(attempt) is not int or attempt not in (1, 2)
                or row['cell_id'] != traces[identity]['cell_id'] or key in attempts
                or row['status'] not in ('completed', 'failed', 'interrupted', 'started')):
            raise ValueError('Invalid or duplicate attempt identity')
        if row['status'] == 'completed':
            rate = row.get('weighted_on_time_rate')
            if type(rate) not in (float, int) or not math.isfinite(rate) or not 0 <= rate <= 1:
                raise ValueError('Completed run requires a finite rate in [0,1]')
        attempts[key] = row; histories[(identity, policy)].append(row)
    selected = {}
    for key, history in histories.items():
        history.sort(key=lambda r: r['attempt'])
        if history[0]['attempt'] != 1 or (len(history) == 2 and history[0]['status'] in ('completed', 'started')):
            raise ValueError('Invalid retry sequence')
        success = [r for r in history if r['status'] == 'completed']
        if success: selected[key] = success[0]
    comparisons = {}
    for comparison_index, baseline in enumerate(('edf', 'value')):
        rng = np.random.default_rng(protocol['bootstrap_seed']+comparison_index)
        cell_results, samples, deltas = [], [], []
        for cell, identities in sorted(cells.items()):
            values = []
            for identity in sorted(identities):
                learned = selected.get((identity, 'learned')); other = selected.get((identity, baseline))
                if learned is not None and other is not None:
                    delta = learned['weighted_on_time_rate']-other['weighted_on_time_rate']
                    values.append(delta)
                    deltas.append(dict(comparison='learned-'+baseline, cell_id=cell, trajectory_id=identity, delta=delta))
            mean = float(np.mean(values)) if values else None
            ci = None
            if len(values) == 10:
                array = np.asarray(values, dtype=float)
                bootstrap = array[rng.integers(0, 10, size=(protocol['bootstrap_replicates'], 10))].mean(axis=1)
                samples.append(bootstrap)
                ci = np.quantile(bootstrap, [.025, .975], method='linear').tolist()
            cell_results.append(dict(cell_id=cell, n=len(values), missing=10-len(values), mean_delta=mean, ci95=ci))
        all_cells_have_pairs = all(r['n'] > 0 for r in cell_results)
        mean = float(np.mean([r['mean_delta'] for r in cell_results])) if all_cells_have_pairs else None
        ci = np.quantile(np.asarray(samples).mean(axis=0), [.025, .975], method='linear').tolist() if len(samples) == 18 else None
        comparisons['learned-'+baseline] = dict(cells=cell_results, paired_count=len(deltas), deltas=deltas,
            overall=dict(mean_delta=mean, ci95=ci, aggregation=protocol['aggregation']),
            statistical_verdict=classify(mean, ci), formal_verdict='未完成')
    return dict(schema_version='formal-analysis-summary-v1', expected_policy_runs=540,
                completed_policy_runs=len(selected), missing_policy_runs=540-len(histories),
                failed_policy_runs=len(histories)-len(selected),
                failed_attempts=sum(r['status'] != 'completed' for r in attempts.values()),
                result_signoff='pending', domain=protocol['domain'], multiplicity=protocol['multiplicity'],
                comparisons=comparisons)


def _csv(path, fields, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def analyze_runs(manifest_path: Path, run_index: Path, output: Path) -> dict:
    manifest_path, run_index, output = Path(manifest_path), Path(run_index), Path(output)
    if output.exists(): raise ValueError('Output must be new')
    frozen = verify_frozen(manifest_path)
    protocol = read_json(manifest_path.parent/'analysis_protocol.json')
    rows = read_run_index(manifest_path, run_index)
    enriched = []; latencies = []; cold_loads = []; requests = fallbacks = 0
    safety = {p: 0 for p in POLICIES}
    for row in rows:
        item = dict(row)
        if row['status'] == 'completed':
            folder = run_index.parent/row['run_path']
            result = read_json(folder/'results.json'); meta = read_json(folder/'manifest.json')
            metrics = result['by_policy'][0]
            item['weighted_on_time_rate'] = metrics['weighted_on_time_rate']
            count = metrics['energy_violation_count']
            if type(count) is not int or count < 0: raise ValueError('Invalid safety count')
            safety[row['policy_id']] += count
            if row['policy_id'] == 'learned':
                inference = meta['inference']
                n, f = inference['requests'], inference['fallback_count']
                if type(n) is not int or type(f) is not int or not 0 <= f <= n: raise ValueError('Invalid inference counts')
                requests += n; fallbacks += f
                cold = inference.get('cold_load_ms')
                if cold is not None:
                    if not math.isfinite(cold) or cold < 0: raise ValueError('Invalid cold load time')
                    cold_loads.append(cold)
                import json
                for line in (folder/'events.jsonl').read_text(encoding='utf-8').splitlines():
                    event = json.loads(line)
                    if event['event_type'] == 'decision':
                        latency = event['data']['latency_ms']
                        if not math.isfinite(latency) or latency < 0: raise ValueError('Invalid decision latency')
                        latencies.append(latency)
        enriched.append(item)
    summary = summarize_pairs(frozen['trajectories'], enriched, protocol)
    summary.update(data_scope=frozen['data_scope'], policy_ids=list(POLICIES),
        provenance=dict(frozen_manifest_sha256=file_hash(manifest_path), run_index_sha256=file_hash(run_index),
                        binding=frozen['binding']), safety_energy_violation_segments=safety,
        inference=dict(requests=requests, fallback_count=fallbacks, fallback_rate=fallbacks/requests if requests else None,
                       cold_load_ms=cold_loads, decision_latency_count=len(latencies),
                       decision_latency_median_ms=float(np.median(latencies)) if latencies else None,
                       decision_latency_p95_ms=float(np.quantile(latencies, .95)) if latencies else None,
                       scope='local_CPU_end_to_end_decision_not_pure_model_forward'))
    # Re-read before publishing to detect concurrent append/edit during analysis.
    if read_run_index(manifest_path, run_index) != rows: raise ValueError('Run index changed during analysis')
    output.mkdir(parents=True, exist_ok=False)
    deltas = [r for pair in summary['comparisons'].values() for r in pair.pop('deltas')]
    _csv(output/'paired_deltas.csv', ['comparison', 'cell_id', 'trajectory_id', 'delta'], deltas)
    _csv(output/'failure_ledger.csv', ['trajectory_id', 'cell_id', 'policy_id', 'attempt', 'run_id', 'status', 'error_type'],
         [r for r in rows if r['status'] != 'completed'])
    summary['artifacts_sha256'] = {name: file_hash(output/name) for name in ('paired_deltas.csv', 'failure_ledger.csv')}
    write_json(output/'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--run-index', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze_runs(args.manifest, args.run_index, args.output)
    print(f"completed={result['completed_policy_runs']}/540; signoff=pending; formal verdict=未完成")


if __name__ == '__main__': main()
