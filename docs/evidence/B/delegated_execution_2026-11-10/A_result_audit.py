"""Independent A-scope numerical audit of raw results; no result signing.

Run with the main checkout .venv/Scripts/python.exe. Reads raw journal/results,
recomputes paired statistics directly with NumPy, never calls analyze_formal.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
import csv
import hashlib
import json
import traceback
import numpy as np

OUT = Path(__file__).resolve().parent
MAIN = OUT.parents[3]
RUN = MAIN.parent/'formal-frozen-verification-20261109/runs/formal_v2_delegated_20261110'
checks = []

def load(path):
    return json.loads(path.read_bytes())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check(name, passed, detail=None):
    checks.append(dict(name=name, passed=bool(passed), detail=detail))
    if not passed:
        raise AssertionError(name+': '+str(detail))

def main():
    summary_path = RUN/'analysis/summary.json'
    journal_path = RUN/'batch/run_index.jsonl'
    manifest_path = RUN/'frozen/manifest.json'
    summary = load(summary_path)
    frozen = load(manifest_path)
    protocol = load(RUN/'frozen/analysis_protocol.json')
    check('bootstrap_protocol_numpy', np.__version__ == protocol['numpy_version'] == '2.1.3')
    check('bootstrap_protocol_parameters', protocol['bootstrap_replicates'] == 10000 and protocol['bootstrap_seed'] == 20261104 and protocol['aggregation'] == 'equal_weight_18_cells_stratified_paired')
    snapshots = {str(p):sha(p) for p in (summary_path,journal_path,manifest_path)}
    check('summary_provenance_journal_hash', summary['provenance']['run_index_sha256'] == sha(journal_path))
    check('summary_provenance_frozen_hash', summary['provenance']['frozen_manifest_sha256'] == sha(manifest_path))
    traces = {r['trajectory_id']:r for r in frozen['trajectories']}
    cells = defaultdict(list)
    for identity,trace in traces.items():
        cells[trace['cell_id']].append(identity)
    check('population_180_18_cells_10', len(traces) == 180 and len(cells) == 18 and all(len(x)==10 for x in cells.values()))
    journal = [json.loads(line) for line in journal_path.read_bytes().splitlines()]
    started, ended = {}, {}
    safety = Counter()
    rates, inference, event_counts = {}, Counter(), Counter()
    for row in journal:
        key = (row['trajectory_id'],row['policy_id'],row['attempt'])
        check('journal_known_identity_'+str(key)+'_'+row['status'], key[0] in traces and key[1] in ['edf','value','learned'] and key[2] in [1,2] and row['cell_id'] == traces[key[0]]['cell_id'] and row['seed'] == traces[key[0]]['seed'] and row['input_hash'] == traces[key[0]]['input_hash'])
        if row['status'] == 'started':
            check('journal_unique_start_'+str(key), key not in started)
            started[key] = row
        else:
            check('journal_unique_terminal_'+str(key), key in started and key not in ended and row['status'] in ['completed','failed','interrupted'])
            ended[key] = row
            folder = RUN/'batch'/row['run_path']
            for name,digest in row['artifacts_sha256'].items():
                check('raw_artifact_hash_'+str(key)+'_'+name, sha(folder/name) == digest)
            if row['status'] != 'completed':
                continue
            result = load(folder/'results.json')
            meta = load(folder/'manifest.json')
            metric = result['by_policy'][0]
            check('raw_result_identity_'+str(key), result['status'] == 'completed' and result['run_id'] == row['run_id'] and metric['policy_id'] == key[1] and result['input_hash'] == row['input_hash'] and result['seed'] == row['seed'] and result['model_hash'] == row['model_hash'])
            rate = metric['weighted_on_time_rate']
            check('raw_rate_valid_'+str(key), type(rate) in [int,float] and np.isfinite(rate) and 0<=rate<=1)
            check('raw_safety_valid_'+str(key), type(metric['energy_violation_count']) is int and metric['energy_violation_count'] >= 0)
            safety[key[1]] += metric['energy_violation_count']
            rates[key] = rate
            if key[1] == 'learned':
                for field in ['requests','fallback_count','successful_model_decisions']:
                    inference[field] += meta['inference'][field]
                events = [json.loads(line) for line in (folder/'events.jsonl').read_bytes().splitlines()]
                event_counts['decision_events'] += sum(e['event_type']=='decision' for e in events)
    selected = {}
    histories = defaultdict(list)
    for key,row in started.items():
        histories[key[:2]].append(key)
    for key,history in histories.items():
        successes = sorted(k for k in history if ended.get(k,{}).get('status') == 'completed')
        if successes:
            selected[key] = rates[successes[0]]
    expected_keys = {(t,p) for t in traces for p in ['edf','value','learned']}
    missing = sorted(expected_keys-set(histories))
    failed = sorted(set(histories)-set(selected))
    unended = sorted(set(started)-set(ended))
    failed_attempts = sum(r['status'] != 'completed' for r in ended.values())
    completeness = dict(journal_records=len(journal), attempts=len(started), completed=len(selected), missing=len(missing), failed=len(failed), failed_attempts=failed_attempts, unended=len(unended))
    check('completeness_540_completed_zero_missing_failed', len(selected)==540 and not missing and not failed and not unended and failed_attempts==0, completeness)
    check('summary_completeness_matches_raw', summary['completed_policy_runs']==len(selected) and summary['missing_policy_runs']==len(missing) and summary['failed_policy_runs']==len(failed) and summary['failed_attempts']==failed_attempts)
    comparisons = {}
    csv_rows = list(csv.DictReader((RUN/'analysis/paired_deltas.csv').open(encoding='utf-8')))
    actual_csv = {(r['comparison'],r['trajectory_id']):float(r['delta']) for r in csv_rows}
    check('paired_delta_csv_unique_360', len(actual_csv)==len(csv_rows)==360)
    for index,baseline in enumerate(['edf','value']):
        name = 'learned-'+baseline
        rng = np.random.default_rng(20261104+index)
        means, bootstraps, differences, cell_results = [], [], [], []
        original = summary['comparisons'][name]
        for cell,identities in sorted(cells.items()):
            values = np.array([selected[(t,'learned')]-selected[(t,baseline)] for t in sorted(identities)])
            differences.extend(values.tolist())
            means.append(float(values.mean()))
            # 10 draws within each cell; paired trajectories remain paired.
            sampled = values[rng.integers(0,10,size=(10000,10))].mean(axis=1)
            bootstraps.append(sampled)
            interval = np.quantile(sampled,[.025,.975],method='linear').tolist()
            row = next(r for r in original['cells'] if r['cell_id']==cell)
            check('cell_recomputed_'+name+'_'+cell, row['n']==10 and row['missing']==0 and row['mean_delta']==means[-1] and row['ci95']==interval)
            cell_results.append(dict(cell_id=cell,n=10,mean_delta=means[-1],ci95=interval))
            for t,difference in zip(sorted(identities),values):
                check('paired_delta_csv_raw_'+name+'_'+t, actual_csv[(name,t)]==difference)
        mean = float(np.mean(means))
        interval = np.quantile(np.array(bootstraps).mean(axis=0),[.025,.975],method='linear').tolist()
        wins = sum(d>0 for d in differences)
        ties = sum(d==0 for d in differences)
        losses = sum(d<0 for d in differences)
        check('overall_recomputed_'+name, original['paired_count']==len(differences)==180 and original['overall']['mean_delta']==mean and original['overall']['ci95']==interval, dict(mean=mean,ci95=interval))
        comparisons[name] = dict(paired_count=180,mean_delta=mean,ci95=interval,wins=wins,ties=ties,losses=losses,bootstrap_seed=20261104+index,bootstrap_replicates=10000,cells=cell_results)
    safety_dict = {p:safety[p] for p in ['edf','value','learned']}
    check('safety_zero_all_policies', safety_dict==summary['safety_energy_violation_segments']==dict(edf=0,value=0,learned=0))
    check('inference_0_fallback_of_2160', inference['requests']==summary['inference']['requests']==2160 and inference['fallback_count']==summary['inference']['fallback_count']==0 and inference['successful_model_decisions']==2160 and event_counts['decision_events']==summary['inference']['decision_latency_count']==2160)
    ledger = list(csv.DictReader((RUN/'analysis/failure_ledger.csv').open(encoding='utf-8')))
    check('failure_ledger_empty', len(ledger)==failed_attempts==0)
    for name,digest in summary['artifacts_sha256'].items():
        check('analysis_output_hash_'+name, sha(RUN/'analysis'/name)==digest)
    check('source_inputs_unchanged_during_audit', all(sha(Path(p))==h for p,h in snapshots.items()))
    return dict(completeness=completeness, comparisons=comparisons, safety_energy_violation_segments=safety_dict,inference=dict(inference),decision_event_count=event_counts['decision_events'],inputs_sha256=snapshots,limitations=['Numerical audit reads the raw run results and journal; it does not rerun the simulator or retrain the model.','Safety counts are negative unclipped energy-ledger segments, not independent episodes.','Bootstrap intervals are pointwise; no familywise or deployment-generalization claim.','This machine audit is not a human A signature or a formal result release signature.'])

if __name__ == '__main__':
    report = dict(schema_version='delegated-A-result-audit-v1',reviewer='codex-delegated-A-result-audit',reviewer_type='independent_codex_agent_machine_review',authorization_text='能不能替ac进行检查，直接推进下一步',release_signature=False,started_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),audit_script_sha256=sha(Path(__file__)),checks=checks)
    try:
        report.update(main(),status='passed')
    except Exception:
        report.update(status='failed',error=traceback.format_exc())
    report['check_count']=len(checks)
    report['finished_at']=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    (OUT/'A_result_audit.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    (OUT/'A_result_audit.log').write_text('\n'.join(f"{'PASS' if r['passed'] else 'FAIL'} {r['name']}" for r in checks)+'\n'+report.get('error','')+f"\nstatus={report['status']}; checks={len(checks)}\n",encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['checks','comparisons']},ensure_ascii=False,indent=2))
    raise SystemExit(0 if report['status']=='passed' else 1)
