"""Read-only independent C review of the completed delegated formal batch."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta

OUT = Path(__file__).resolve().parent
FROZEN_ROOT = Path('D:/人工智能挑战赛/formal-frozen-verification-20261109')
RUN = FROZEN_ROOT/'runs/formal_v2_delegated_20261110'
REV = '48157a8f4a1cdd7770685b79deb3fe4524b1bf7d'
MODEL = 'a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a'
sys.dont_write_bytecode = True
sys.path.insert(0, str(FROZEN_ROOT))


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def csv_rows(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    report = dict(schema_version='delegated-C-result-audit-v1', reviewer='codex-delegated-C-result-review',
                  reviewed_at=datetime.now(timezone(timedelta(hours=8))).isoformat(), status='running', checks={},
                  failures=[], human_release_signature=False, run_root=str(RUN),
                  limitation='Machine integrity audit only; no human C signature or formal result release approval.')
    logs = []

    def check(name, condition, value=True):
        report['checks'][name] = value
        if not condition:
            report['failures'].append(name)
            raise AssertionError(name)
        logs.append('PASS '+name+': '+json.dumps(value, ensure_ascii=False, sort_keys=True))

    try:
        from backend.formal_freeze import verify_frozen
        from backend.formal_experiments import read_run_index
        manifest_path = RUN/'frozen/manifest.json'
        index_path = RUN/'batch/run_index.jsonl'
        frozen = verify_frozen(manifest_path)
        rows = read_run_index(manifest_path, index_path)
        check('frozen_validator_and_read_run_index', len(rows) == 540, dict(validated_completed_attempts=len(rows)))
        check('original_code_and_model', frozen['binding']['code_revision'] == REV and frozen['binding']['model_artifacts_sha256']['weights.npz'] == MODEL)
        journal = [json.loads(line) for line in index_path.read_text(encoding='utf-8').splitlines()]
        statuses = Counter(row['status'] for row in journal)
        check('journal_exact_record_counts', len(journal) == 1080 and statuses == {'started': 540, 'completed': 540}, dict(records=len(journal), statuses=dict(statuses)))
        keys = {(row['trajectory_id'], row['policy_id']) for row in rows}
        expected = {(trace['trajectory_id'], policy) for trace in frozen['trajectories'] for policy in ('edf', 'value', 'learned')}
        check('exact_180_by_3_keys', keys == expected and len(keys) == len(rows) == 540, len(keys))
        check('no_hidden_retries_or_failures', all(row['attempt'] == 1 and row['status'] == 'completed' for row in rows))
        counts = Counter((row['cell_id'], row['policy_id']) for row in rows)
        check('all_cells_10_per_policy', len(counts) == 54 and set(counts.values()) == {10}, {'|'.join(k):v for k,v in counts.items()})
        dirs = {p.relative_to(RUN/'batch').as_posix() for p in (RUN/'batch/runs').glob('*/*/attempt_*')}
        check('no_unindexed_attempt_directories', dirs == {row['run_path'] for row in rows}, len(dirs))
        traces = {row['trajectory_id']: row for row in frozen['trajectories']}
        results = {}
        artifacts = 0
        source_checks = 0
        for row in rows:
            folder = RUN/'batch'/row['run_path']
            actual_artifacts = {p.relative_to(folder).as_posix(): sha(p) for p in folder.rglob('*') if p.is_file()}
            if actual_artifacts != row['artifacts_sha256']:
                raise ValueError('Independent artifact mismatch '+row['run_path'])
            artifacts += len(actual_artifacts)
            meta = read(folder/'manifest.json')
            result = read(folder/'results.json')
            config = read(folder/'config.json')
            trace = traces[row['trajectory_id']]
            scenario_bytes = canonical(config['scenario'])
            config_hash = hashlib.sha256(canonical(config)).hexdigest()
            if hashlib.sha256(scenario_bytes).hexdigest() != trace['input_hash'] or config_hash != result['config_hash'] or config_hash != meta['config_hash']:
                raise ValueError('Independent input/config mismatch '+row['run_path'])
            if meta['code_revision'] != REV or result['code_revision'] != REV or config['seed'] != trace['seed'] or config['scenario']['channel']['seed'] != trace['seed'] or meta['seed'] != trace['seed']:
                raise ValueError('Code/seed mismatch '+row['run_path'])
            for name, raw_sha in meta['source_sha256'].items():
                source = FROZEN_ROOT/name
                normalized = hashlib.sha256(source.read_text(encoding='utf-8-sig').encode()).hexdigest()
                if sha(source) != raw_sha or normalized != frozen['binding']['source_sha256'][name]:
                    raise ValueError('Independent source mismatch '+name)
                source_checks += 1
            if row['policy_id'] == 'learned':
                if meta['model_hash'] != MODEL or result['model_hash'] != MODEL or meta['model']['model_version'] != 'a-n3-mlp-v1' or config['policy_runtime']['model']['model_hash'] != MODEL:
                    raise ValueError('Original Learned not retained')
            results[(row['trajectory_id'], row['policy_id'])] = result
        check('independent_all_child_artifacts_and_identity', True, dict(runs=540, artifact_hashes=artifacts, source_hash_checks=source_checks, original_learned_runs=180))
        receipts = {role: read(RUN/f'frozen/receipts/{role}.json') for role in 'ABC'}
        identities = {role: receipt['reviewer'] for role,receipt in receipts.items()}
        check('real_delegated_review_identities', identities['A'].startswith('codex-delegated-A') and identities['C'] == 'codex-delegated-C-inventory-review' and len(set(identities.values())) == 3 and receipts['A']['delegation']['human_member_A_signature'] is False and receipts['C']['delegation']['human_member_C_signature'] is False, identities)
        summary = read(RUN/'analysis/summary.json')
        check('analysis_input_provenance', summary['provenance']['frozen_manifest_sha256'] == sha(manifest_path) and summary['provenance']['run_index_sha256'] == sha(index_path) and summary['provenance']['binding'] == frozen['binding'])
        for name, expected_sha in summary['artifacts_sha256'].items():
            if sha(RUN/'analysis'/name) != expected_sha:
                raise ValueError('Analysis artifact mismatch '+name)
        comparisons = summary['comparisons']
        check('analysis_18_by_10_no_missing', set(comparisons) == {'learned-edf', 'learned-value'} and all(len(c['cells']) == 18 and c['paired_count'] == 180 and all(cell['n'] == 10 and cell['missing'] == 0 for cell in c['cells']) for c in comparisons.values()))
        paired = csv_rows(RUN/'analysis/paired_deltas.csv')
        for pair in paired:
            baseline = pair['comparison'].split('-')[1]
            learned = results[(pair['trajectory_id'], 'learned')]['by_policy'][0]['weighted_on_time_rate']
            other = results[(pair['trajectory_id'], baseline)]['by_policy'][0]['weighted_on_time_rate']
            if abs(float(pair['delta'])-(learned-other)) > 1e-12:
                raise ValueError('Paired delta mismatch')
        check('all_360_paired_deltas_recomputed', len(paired) == 360 and len({(p['comparison'],p['trajectory_id']) for p in paired}) == 360, len(paired))
        check('empty_failure_ledger', len(csv_rows(RUN/'analysis/failure_ledger.csv')) == 0)
        metrics = csv_rows(RUN/'export/metrics_by_run.csv')
        check('export_exact_540_unique_run_metrics', len(metrics) == 540 and {(r['trajectory_id'],r['policy_id']) for r in metrics} == keys, len(metrics))
        null_counts = Counter()
        reason_counts = Counter()
        for metric in metrics:
            result = results[(metric['trajectory_id'], metric['policy_id'])]
            by_policy = result['by_policy'][0]
            for key in ('seed', 'input_hash', 'model_hash', 'run_id'):
                expected_value = result[key]
                if metric[key] != ('' if expected_value is None else str(expected_value)):
                    raise ValueError('Export identity mismatch '+key)
            reasons = json.loads(metric['metric_reasons'])
            if reasons != by_policy['metric_reasons']:
                raise ValueError('Export metric reason mismatch')
            for key, value in by_policy.items():
                if key == 'metric_reasons' or key not in metric:
                    continue
                expected_value = '' if value is None else str(value)
                if metric[key] != expected_value:
                    raise ValueError('Export metric mismatch '+key)
                if value is None:
                    null_counts[key] += 1
                    if key not in ('model_hash',) and not reasons.get(key):
                        raise ValueError('Unexplained null metric '+key)
            reason_counts.update(reasons.values())
        check('export_metrics_and_null_reasons_match_all_children', True, dict(null_counts=dict(null_counts), reason_counts=dict(reason_counts)))
        export_index = read(RUN/'export/SHA256SUMS.json')
        check('all_export_hashes', all(sha(RUN/'export'/name) == expected_sha for name,expected_sha in export_index.items()), len(export_index))
        stage_evidence = {}
        for stage, expected_count in [('smoke',3), ('cell',30), ('coverage',81), ('full',540), ('analysis',None)]:
            meta = read(RUN/f'stage_logs/{stage}.json')
            raw_bytes = (RUN/f'stage_logs/{stage}.log').read_bytes()
            try:
                raw = raw_bytes.decode('utf-8')
                log_encoding = 'utf-8'
            except UnicodeDecodeError:
                raw = raw_bytes.decode('gb18030')
                log_encoding = 'gb18030 (Windows subprocess locale)'
            if meta['exit_code'] != 0 or meta['code_revision'] != REV or meta['stage'] != stage:
                raise ValueError('Stage metadata mismatch '+stage)
            if expected_count is not None:
                parsed = json.loads(raw)
                if parsed['completed_policy_runs'] != expected_count or parsed['failed_policy_runs'] != 0:
                    raise ValueError('Stage count mismatch '+stage)
            stage_evidence[stage] = dict(log_sha256=sha(RUN/f'stage_logs/{stage}.log'), metadata_sha256=sha(RUN/f'stage_logs/{stage}.json'), completed=expected_count, exit_code=0, encoding=log_encoding)
        check('original_stage_logs', True, stage_evidence)
        check('result_release_still_pending', summary['result_signoff'] == 'pending' and all(comp['formal_verdict'] == '未完成' for comp in comparisons.values()), summary['result_signoff'])
        report['statistical_results_observed'] = {name: dict(overall=comp['overall'], statistical_verdict=comp['statistical_verdict']) for name,comp in comparisons.items()}
        report['subject_hashes'] = dict(frozen_manifest=sha(manifest_path), run_index=sha(index_path), analysis_summary=sha(RUN/'analysis/summary.json'), metrics=sha(RUN/'export/metrics_by_run.csv'))
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        report['exception'] = f'{type(error).__name__}: {error}'
        logs.append('FAIL '+report['exception'])
    report['script_sha256'] = sha(Path(__file__))
    (OUT/'C_result_audit.json').write_bytes(canonical(report))
    (OUT/'C_result_audit.log').write_text('\n'.join(logs)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(status=report['status'],checks=len(report['checks']), failures=report['failures'], exception=report.get('exception')),ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
