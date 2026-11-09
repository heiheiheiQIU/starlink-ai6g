"""Export verified run metrics and indexed event excerpts for result review."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

from backend.formal_experiments import read_run_index
from backend.formal_freeze import file_hash


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, output = args.run_root.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    journal = read_run_index(root/'frozen/manifest.json', root/'batch/run_index.jsonl')
    selected = {}
    for row in journal:
        key = row['trajectory_id'], row['policy_id']
        if row['status'] == 'completed' and key not in selected:
            selected[key] = row
    metrics = []
    cases = {}
    totals = {}
    for key, row in sorted(selected.items()):
        folder = root/'batch'/row['run_path']
        result = read(folder/'results.json')
        values = result['by_policy'][0]
        events = [json.loads(line) for line in (folder/'events.jsonl').read_text(encoding='utf-8').splitlines()]
        decisions = [e for e in events if e['event_type'] == 'decision']
        reasons = Counter(e['reason_code'] for e in events if e['reason_code'])
        policy = row['policy_id']
        stats = totals.setdefault(policy, Counter())
        stats.update(dict(runs=1, decisions=len(decisions),
                          idle_decisions=sum(e['data']['action']['mode'] == 'idle' for e in decisions),
                          fallback_decisions=sum(e['data']['fallback'] for e in decisions),
                          ack_timeouts=reasons['ACK_TIMEOUT'], duplicate_blocks=reasons['DUPLICATE_BLOCK']))
        exported_metrics = {k: v for k, v in values.items() if k not in ('policy_id', 'model_hash')}
        exported_metrics['metric_reasons'] = json.dumps(values['metric_reasons'], ensure_ascii=False, sort_keys=True)
        metrics.append(dict(trajectory_id=key[0], cell_id=row['cell_id'], seed=row['seed'],
            run_id=row['run_id'], attempt=row['attempt'], policy_id=policy,
            input_hash=row['input_hash'], model_hash=row['model_hash'],
            **exported_metrics,
            decisions=len(decisions),
            idle_decisions=sum(e['data']['action']['mode'] == 'idle' for e in decisions),
            fallback_decisions=sum(e['data']['fallback'] for e in decisions),
            ack_timeouts=reasons['ACK_TIMEOUT'], duplicate_blocks=reasons['DUPLICATE_BLOCK']))
        for event in events:
            category = None
            if event['reason_code'] == 'ACK_TIMEOUT' and 'ack_retry' not in cases:
                category = 'ack_retry'
            if event['event_type'] == 'decision' and policy == 'learned':
                failed = [c for c in event['data']['constraint_checks'] if c['code'] == 'ENERGY_RESERVE' and not c['passed']]
                if failed and 'guard_rejection' not in cases:
                    category = 'guard_rejection'
                if event['data']['fallback'] and 'model_fallback' not in cases:
                    if any(c in ('MODEL_TIMEOUT', 'MODEL_UNAVAILABLE', 'INVALID_SCORE')
                           for c in event['data']['action']['reason_codes']):
                        category = 'model_fallback'
                if event['data']['action']['mode'] == 'idle' and not event['data']['fallback'] and 'learned_idle' not in cases:
                    category = 'learned_idle'
            if category:
                nearby = [e for e in events if max(1, event['event_id']-3) <= e['event_id'] <= event['event_id']+12]
                cases[category] = dict(scope='registered_inputs_delegated_review_execution',
                    run_id=row['run_id'], policy_id=policy, seed=row['seed'],
                    trajectory_id=row['trajectory_id'], input_hash=row['input_hash'],
                    source_file=(Path('batch')/row['run_path']/'events.jsonl').as_posix(),
                    source_sha256=file_hash(folder/'events.jsonl'),
                    anchor_event_id=event['event_id'], event_range=[nearby[0]['event_id'], nearby[-1]['event_id']],
                    events=nearby)
    fields = list(metrics[0]) if metrics else []
    with (output/'metrics_by_run.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(metrics)
    write(output/'policy_event_totals.json', totals)
    write(output/'event_cases.json', cases)
    write(output/'case_availability.json', dict(actual_cases=list(cases),
        model_fault_injection='Historical injected corruption evidence remains separately labelled engineering evidence.',
        formal_model_fault_observed='model_fallback' in cases))
    write(output/'SHA256SUMS.json', {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in output.iterdir() if p.is_file()})
    print(json.dumps(dict(verified_completed_runs=len(selected), cases=list(cases))))


if __name__ == '__main__':
    main()
