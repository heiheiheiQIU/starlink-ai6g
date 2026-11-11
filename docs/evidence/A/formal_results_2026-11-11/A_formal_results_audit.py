"""Independent, read-only formal result audit. Python standard library only.

Semantic checks precede immutable hashes so mutation tests exercise each layer.
No package code is executed and no B/C audit assertions are consumed.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import sys
import zipfile

SOURCE_COMMIT = "a4890579f1d4a2cfb5be9246db6ca46a306fcd39"
RESULT_ZIP_SHA256 = "efa801d9dde6a9eb340ca0a27b873027248edbcadd7b85c82cdd3847ab5f9e86"
SUMMARY_SHA256 = "872a71029783ca4100ed8d4e6cfec79261f9c7eaaca65b10362ce53a9ffdbae9"
FROZEN_CODE_REVISION = "48157a8f4a1cdd7770685b79deb3fe4524b1bf7d"
MODEL_VERSION = "a-n3-mlp-v1"
MODEL_WEIGHTS_SHA256 = "a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a"
FROZEN_MANIFEST_SHA256 = "3ad4bfeaf5398012bae17cab4bf684fb5a80ce0b5e341bf5e9eda4d179104d30"
RUN_INDEX_SHA256 = "5d9c58585cd6782c3d898f2fc690829ae3a04956f9844e9ad6c389ea7d408ade"
DOMAIN = 'synthetic_out_of_zero_loss_training_domain'
POLICIES = ('edf', 'value', 'learned')


def require(condition, label):
    if not condition:
        raise ValueError(label)


def close(a, b, label):
    require(type(a) in (float, int) and math.isfinite(a) and
            math.isclose(a, b, rel_tol=0, abs_tol=2e-14), label)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def quantile(values, q):
    values = sorted(values)
    at = (len(values)-1)*q
    lo = int(at)
    return values[lo] + (values[min(lo+1, len(values)-1)]-values[lo])*(at-lo)


class FrozenPCG64:
    """PCG XSL RR 128/64 and Lemire uint32 bounded sampling.

    The two starting states are NumPy 2.1.3 SeedSequence(seed) PCG64 states
    for the frozen protocol seeds 20261104 and 20261105. They are RNG
    initialization constants, not observed bootstrap samples or CI values.
    Keeping them explicit avoids a runtime dependency on NumPy/SeedSequence.
    """
    STATES = (
        (229694299841262477288223287389018509093, 137480520283303842455270833016181637539),
        (49628236063425968124219692230825568294, 161675534895039952189290665612767333659),
    )

    def __init__(self, comparison):
        self.state, self.inc = self.STATES[comparison]
        self.buffer = None

    def uint32(self):
        if self.buffer is not None:
            value, self.buffer = self.buffer, None
            return value
        self.state = (self.state*47026247687942121848144207491837523525+self.inc) & ((1 << 128)-1)
        x = ((self.state >> 64) ^ self.state) & ((1 << 64)-1)
        rotation = self.state >> 122
        value = ((x >> rotation) | (x << ((-rotation) & 63))) & ((1 << 64)-1)
        self.buffer = value >> 32
        return value & 0xffffffff

    def ten(self):
        while True:
            product = self.uint32()*10
            if product & 0xffffffff >= 6:
                return product >> 32


def recompute_comparison(groups, comparison_index):
    rng = FrozenPCG64(comparison_index)
    draws = [0.0]*10000
    cells = []
    for cell, values in sorted(groups.items()):
        samples = [sum(values[rng.ten()] for _ in range(10))/10 for _ in range(10000)]
        draws = [a+b for a, b in zip(draws, samples)]
        cells.append(dict(cell_id=cell, n=10, missing=0, mean_delta=sum(values)/10,
                          ci95=[quantile(samples, .025), quantile(samples, .975)]))
    return dict(cells=cells, paired_count=180, overall=dict(
        mean_delta=sum(c['mean_delta'] for c in cells)/18,
        ci95=[quantile([v/18 for v in draws], q) for q in (.025, .975)],
        aggregation='equal_weight_18_cells_stratified_paired'),
        formal_verdict='未完成', statistical_verdict='负')


def audit(path, source_commit):
    require(source_commit == SOURCE_COMMIT, 'source_commit mismatch')
    raw = Path(path).read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        require(len(names) == len(set(names)), 'zip.duplicate member')
        require(z.testzip() is None, 'zip.corrupt member')
        # Read in memory only: never extract or execute supplied paths/code.
        data = {n: z.read(n) for n in names}
    def js(name):
        return json.loads(data[name])
    def lines(name):
        return [json.loads(l) for l in data[name].splitlines() if l.strip()]
    def table(name):
        return list(csv.DictReader(io.StringIO(data[name].decode('utf-8'))))
    frozen, summary = js('frozen/manifest.json'), js('analysis/summary.json')
    binding = frozen['binding']
    require(binding.get('code_revision') == FROZEN_CODE_REVISION, 'frozen.code binding')
    require(js('frozen/model/manifest.json')['model_version'] == MODEL_VERSION, 'model.version binding')
    require(sha(data['frozen/model/weights.npz']) == MODEL_WEIGHTS_SHA256, 'model.weights binding')
    require(summary.get('provenance') == dict(frozen_manifest_sha256=FROZEN_MANIFEST_SHA256,
        run_index_sha256=RUN_INDEX_SHA256, binding=binding), 'summary.binding mismatch')
    protocol = js('frozen/analysis_protocol.json')
    require(summary['domain'] == protocol['domain'] == DOMAIN and summary['data_scope'] == 'formal', 'applicability mismatch')
    require(summary['result_signoff'] == 'pending', 'signoff must remain pending')
    for k, expected in [('completed_policy_runs', 540), ('expected_policy_runs', 540),
                        ('failed_attempts', 0), ('failed_policy_runs', 0), ('missing_policy_runs', 0)]:
        require(summary[k] == expected, 'summary.counts '+k)
    require(protocol['bootstrap_seed'] == 20261104 and protocol['bootstrap_replicates'] == 10000
            and protocol['confidence'] == .95 and protocol['interval'] == 'percentile'
            and protocol['aggregation'] == 'equal_weight_18_cells_stratified_paired', 'statistics.protocol')
    traces = {t['trajectory_id']: t for t in frozen['trajectories']}
    require(len(traces) == len(frozen['trajectories']) == 180 and
            Counter(t['cell_id'] for t in traces.values()) == Counter({f'cell_{i:02}': 10 for i in range(18)}), 'runs.trajectories')
    histories = defaultdict(list)
    for row in lines('batch/run_index.jsonl'):
        require(row['trajectory_id'] in traces and row['policy_id'] in POLICIES and
                type(row['attempt']) is int and row['attempt'] == 1, 'runs.identity or retry')
        histories[row['trajectory_id'], row['policy_id']].append(row)
    expected = {(t, p) for t in traces for p in POLICIES}
    require(set(histories) == expected, 'runs.missing identity')
    completed, margins, idle_only, decisions = {}, [], 0, 0
    metrics = table('export/metrics_by_run.csv')
    require(len(metrics) == 540, 'metrics.row_count')
    metric_map = {(m['trajectory_id'], m['policy_id']): m for m in metrics}
    require(set(metric_map) == expected, 'metrics.identities')
    for key, history in sorted(histories.items()):
        require([r['status'] for r in history] == ['started', 'completed'], 'runs.lifecycle duplicate/missing/non-completed')
        row = history[-1]; t, p = key; trace = traces[t]
        for r in history:
            require(all(r[k] == trace[k] for k in ('cell_id', 'input_hash', 'seed')), 'runs.trace binding')
            require(r['run_path'] == f'runs/{t}/{p}/attempt_1', 'runs.path binding')
            require(r['model_hash'] == (MODEL_WEIGHTS_SHA256 if p == 'learned' else None), 'runs.model binding')
        root = 'batch/'+row['run_path']+'/'
        meta, result, status = (js(root+n) for n in ('manifest.json', 'results.json', 'status.json'))
        require(result['status'] == status['status'] == 'completed' and status['error'] is None, 'runs.status')
        for obj in (meta, result, status):
            require(obj['run_id'] == row['run_id'], 'runs.run_id')
        require(meta['code_revision'] == result['code_revision'] == FROZEN_CODE_REVISION, 'runs.code binding')
        require(meta['input_hash'] == result['input_hash'] == trace['input_hash'], 'runs.input binding')
        require(meta['source'] == 'synthetic' and meta['is_real_satellite_measurement'] is False
                and meta['is_policy_benchmark'] is False, 'applicability run flags')
        m = metric_map[key]
        require(m['attempt'] == '1' and m['run_id'] == row['run_id'] and m['input_hash'] == trace['input_hash'], 'metrics.binding')
        rate = float(m['weighted_on_time_rate'])
        require(math.isfinite(rate) and 0 <= rate <= 1, 'metrics.finite rate')
        close(rate, result['by_policy'][0]['weighted_on_time_rate'], 'metrics.rate mismatch')
        completed[key] = rate
        events = lines(root+'events.jsonl')
        require(all(e['run_id'] == row['run_id'] and e['policy_id'] == p for e in events), 'runs.event binding')
        de = [e for e in events if e['event_type'] == 'decision']
        if p == 'learned':
            require(len(de) == 12 and len({e['event_id'] for e in events}) == len(events)
                    and len({e['sim_time_s'] for e in de}) == 12, 'learned.decision missing/duplicate')
            require(meta['model']['model_version'] == MODEL_VERSION and meta['model_hash'] == MODEL_WEIGHTS_SHA256, 'model.run binding')
            for e in de:
                d = e['data']; a = d['action']; scores = d['candidate_scores']
                require(d.get('fallback') is False and a.get('fallback') is False, 'learned.fallback malformed/true')
                require(a['mode'] == 'idle' and a['task_id'] is None and a['scheduled_bytes'] == 0, 'learned.action must be idle')
                require(d['model_version'] == MODEL_VERSION, 'learned.model version')
                require(scores and all(type(s['score']) in (int, float) and math.isfinite(s['score']) for s in scores), 'learned.scores finite')
                idle = [s for s in scores if s['mode'] == 'idle']
                require(len(idle) == 1 and idle[0]['task_id'] is None, 'learned.idle candidate')
                require(idle[0]['score'] == max(s['score'] for s in scores), 'learned.maximum score')
                sends = [s['score'] for s in scores if s['mode'] != 'idle']
                if sends: margins.append(idle[0]['score']-max(sends))
                else: idle_only += 1
                decisions += 1
            require(meta['inference']['requests'] == 12 and meta['inference']['fallback_count'] == 0, 'learned.inference counts')
            require(int(m['decisions']) == int(m['idle_decisions']) == 12 and int(m['fallback_decisions']) == 0, 'metrics.decision counts')
    require(decisions == 2160, 'learned.total decisions')
    require(all(summary['inference'][k] == v for k, v in dict(requests=2160,
            fallback_count=0, fallback_rate=0, decision_latency_count=2160).items()), 'summary.inference counts')
    require(not table('analysis/failure_ledger.csv'), 'runs.failure ledger')
    pairs = table('analysis/paired_deltas.csv')
    require(len(pairs) == 360, 'paired.row count')
    pair_map = {(r['comparison'], r['trajectory_id']): r for r in pairs}
    require(len(pair_map) == 360, 'paired.duplicate')
    comparisons = {}
    for ci, baseline in enumerate(('edf', 'value')):
        comparison = 'learned-'+baseline; groups = defaultdict(list)
        for t in sorted(traces):
            delta = completed[t, 'learned']-completed[t, baseline]
            r = pair_map[comparison, t]
            require(r['cell_id'] == traces[t]['cell_id'], 'paired.cell')
            close(float(r['delta']), delta, 'paired.delta')
            groups[r['cell_id']].append(delta)
        derived = recompute_comparison(groups, ci)
        published = summary['comparisons'][comparison]
        require(published['formal_verdict'] == '未完成' and published['statistical_verdict'] == '负', 'summary.verdict')
        require(published['paired_count'] == 180, 'summary.paired count')
        for actual, original in [(derived['overall'], published['overall'])] + list(zip(derived['cells'], published['cells'])):
            close(actual['mean_delta'], original['mean_delta'], 'summary.comparison mean')
            for a, b in zip(actual['ci95'], original['ci95']): close(a, b, 'summary.comparison CI')
        comparisons[comparison] = derived
    rates = {p: sum(completed[t, p] for t in sorted(traces))/180 for p in POLICIES}
    for p, target in dict(edf=.4653873291265777, value=.5114726389809670, learned=0).items():
        close(rates[p], target, 'metrics.published aggregate')
    # Verify every declared frozen, run and summary artifact checksum as well as
    # the exact immutable outer package; semantic mutation errors remain visible.
    for name, expected_hash in frozen['artifacts_sha256'].items():
        require(sha(data['frozen/'+name]) == expected_hash, 'frozen.artifact '+name)
    with zipfile.ZipFile(io.BytesIO(data['source_48157a8.zip'])) as source:
        for name, expected_hash in binding['source_sha256'].items():
            require(sha(source.read(name)) == expected_hash, 'frozen.source '+name)
    for name, expected_hash in binding['model_artifacts_sha256'].items():
        require(sha(data['frozen/model/'+name]) == expected_hash, 'model.artifact '+name)
    for history in histories.values():
        row = history[-1]
        for name, expected_hash in row['artifacts_sha256'].items():
            require(sha(data['batch/'+row['run_path']+'/'+name]) == expected_hash, 'runs.artifact '+name)
    for name, expected_hash in summary['artifacts_sha256'].items():
        require(sha(data['analysis/'+name]) == expected_hash, 'summary.artifact '+name)
    for name, expected_hash in [('analysis/summary.json', SUMMARY_SHA256),
            ('frozen/manifest.json', FROZEN_MANIFEST_SHA256), ('batch/run_index.jsonl', RUN_INDEX_SHA256)]:
        require(sha(data[name]) == expected_hash, 'binding.sha256 '+name)
    require(sha(raw) == RESULT_ZIP_SHA256, 'zip.sha256 mismatch')
    return dict(source_commit=source_commit, result_zip_sha256=sha(raw), summary_sha256=SUMMARY_SHA256,
        frozen_manifest_sha256=FROZEN_MANIFEST_SHA256, run_index_sha256=RUN_INDEX_SHA256,
        frozen_code_revision=FROZEN_CODE_REVISION, model=dict(version=MODEL_VERSION, weights_sha256=MODEL_WEIGHTS_SHA256),
        runs=dict(completed=540, trajectories=180, cells=18, trajectories_per_cell=10,
                  per_policy={p: 180 for p in POLICIES}, attempt=1, failures=0, missing=0, retries=0),
        policy_weighted_on_time_rate=rates, comparisons=comparisons,
        learned=dict(decisions=decisions, idle_actions=decisions, fallbacks=0,
            score_margin=dict(definition='idle_score_minus_best_send_score', count=len(margins),
                idle_only_decisions=idle_only, minimum=min(margins), median=statistics.median(margins),
                p05=quantile(margins, .05), p95=quantile(margins, .95), maximum=max(margins),
                zero_count=sum(m == 0 for m in margins))),
        applicability=dict(domain=DOMAIN, source='synthetic', is_real_satellite_measurement=False,
            is_policy_benchmark=False, superiority_claim=False,
            multiplicity='pointwise_intervals_no_familywise_claim'),
        machine_audit=dict(status='passed', checks={k: True for k in (
            'immutable_bindings', 'run_lifecycle', 'learned_decisions', 'finite_maximum_scores',
            'metrics_from_540_rows', 'paired_360_rows', 'bootstrap_10000_stratified', 'applicability', 'pending_negative_verdicts')}),
        A_ruling='pending', release_approved=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result-zip', type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.result_zip, args.source_commit)
        payload = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode('utf-8')
        if args.output: args.output.write_bytes(payload)
        else: sys.stdout.buffer.write(payload)
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as error:
        print('audit rejected: '+('zip. '+str(error) if isinstance(error, zipfile.BadZipFile) else str(error)), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
