"""Publish the reviewed formal-v2 batch without changing frozen evidence."""
import argparse
import copy
import csv
import hashlib
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = 'docs/evidence/B/delegated_execution_2026-11-10/'
VERSION = 'formal-v2-release-20261112-v1'
POLICIES = {'edf','value','learned'}
DOMAIN = 'synthetic_out_of_zero_loss_training_domain'
# These pins identify this reviewed batch, not a user-selectable new experiment.
PINNED_FILES = {
    BATCH+'analysis/summary.json': '872a71029783ca4100ed8d4e6cfec79261f9c7eaaca65b10362ce53a9ffdbae9',
    BATCH+'frozen_manifest.json': '3ad4bfeaf5398012bae17cab4bf684fb5a80ce0b5e341bf5e9eda4d179104d30',
    BATCH+'run_index.jsonl': '5d9c58585cd6782c3d898f2fc690829ae3a04956f9844e9ad6c389ea7d408ade',
    BATCH+'formal_v2_delegated_results_20261110.zip': 'efa801d9dde6a9eb340ca0a27b873027248edbcadd7b85c82cdd3847ab5f9e86',
    BATCH+'export/metrics_by_run.csv': '9a82feecaeef219335383cece409f3b4a7f7a84de9ac427807fb82868a8871ee',
    BATCH+'analysis/paired_deltas.csv': '353f7f589739d2d760ffab415aeb3d79cb59317956e3c6d44ad21134cb2efcf9',
    'docs/acceptance/A_formal_results_release_review_2026-11-11.md': 'becfed57695245e201bdaee224d15eb1a7761657bccaf2287e5c1128d8764f13',
    'docs/acceptance/B_formal_results_release_review_2026-11-12.json': '3f000b6b505f2509b5c433a2cfa959e87585ea68c2135d0f809554b4ef280377',
    'docs/acceptance/C_formal_results_release_review_2026-11-11.md': '8eae2d95c0504d18c7caf3d87cc5ee794af4174eefbc39ee1d0932a8fc81d75b',
    'docs/evidence/A/formal_results_2026-11-11/A_formal_results_audit.json': '3e66408b832462111dbdd538aa8fe4e0f782c2461bd68bbd668915e3d36f0fd9',
    'docs/evidence/C/offline_second_machine_2026-11-10/C_receipt.json': '4dec447a2bc6f0aa5aef1591768196f957f340eea5cd9c4c5fee88ce9857de37',
    'artifacts/models/a_n3_policy_v1/weights.npz': 'a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a',
}


def canonical(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')


def require(condition,message):
    if not condition: raise ValueError(message)


def build_release(root=ROOT):
    root = Path(root)
    raw = {}
    for name,digest in PINNED_FILES.items():
        try: raw[name] = (root/name).read_bytes()
        except OSError as error: raise ValueError('missing evidence: '+name) from error
        require(hashlib.sha256(raw[name]).hexdigest()==digest,'evidence hash mismatch: '+name)
    summary = json.loads(raw[BATCH+'analysis/summary.json'])
    audit = json.loads(raw['docs/evidence/A/formal_results_2026-11-11/A_formal_results_audit.json'])
    b_review = json.loads(raw['docs/acceptance/B_formal_results_release_review_2026-11-12.json'])
    require(b_review['release_generation_approved'] is True and b_review['ruling']=='accepted_with_notes','B generation approval missing')
    require(audit['machine_audit']['status']=='passed','A machine audit failed')
    require(audit['release_approved'] is False,'Machine audit cannot replace review approval')
    for field in ('completed_policy_runs','expected_policy_runs'):
        require(summary[field]==540,'Incomplete batch')
    require(all(summary[k]==0 for k in ('missing_policy_runs','failed_policy_runs','failed_attempts')),'Failed or missing runs')
    require(set(summary['policy_ids'])==POLICIES and summary['data_scope']=='formal','Wrong batch policies or scope')
    require(summary['domain']==DOMAIN and summary['multiplicity']=='pointwise_intervals_no_familywise_claim','Unreviewed domain')
    require(summary['result_signoff']=='pending','Original signoff was modified')
    require(summary['inference']['requests']==2160 and summary['inference']['fallback_count']==0,'Inference counts changed')
    index = [json.loads(line) for line in raw[BATCH+'run_index.jsonl'].splitlines()]
    started = [r for r in index if r['status']=='started']
    completed = [r for r in index if r['status']=='completed']
    keys = lambda rows: {(r['trajectory_id'],r['policy_id']) for r in rows}
    require(len(index)==1080 and len(started)==len(completed)==540,'Run lifecycle incomplete')
    require(keys(started)==keys(completed) and len(keys(completed))==540 and all(r['attempt']==1 for r in index),'Duplicate or retried runs')
    metrics = list(csv.DictReader(io.StringIO(raw[BATCH+'export/metrics_by_run.csv'].decode('utf-8'))))
    require(len(metrics)==540 and keys(metrics)==keys(completed),'Metric coverage mismatch')
    rates,payloads = {},{}
    for policy in sorted(POLICIES):
        rows = [r for r in metrics if r['policy_id']==policy]
        cells = {}
        for row in rows: cells.setdefault(row['cell_id'],[]).append(row)
        require(len(rows)==180 and len(cells)==18 and all(len(c)==10 for c in cells.values()),'Cell coverage mismatch')
        rates[policy] = math.fsum(math.fsum(float(r['weighted_on_time_rate']) for r in c)/10 for c in cells.values())/18
        payloads[policy] = sum(int(r['success_payload_bytes']) for r in rows)
        require(math.isclose(rates[policy],audit['policy_weighted_on_time_rate'][policy],abs_tol=1e-14),'Audited metric mismatch')
        require(all(int(r['energy_violation_count'])==0 for r in rows),'Safety result changed')
    require(rates['learned']==0 and payloads['learned']==0,'Unexpected Learned result')
    require(set(summary['comparisons'])=={'learned-edf','learned-value'},'Comparison set changed')
    for key,comparison in summary['comparisons'].items():
        require(comparison['paired_count']==180 and len(comparison['cells'])==18,'Incomplete pairs')
        require(all(c['n']==10 and c['missing']==0 for c in comparison['cells']),'Missing cell pairs')
        require(comparison['formal_verdict']=='未完成' and comparison['statistical_verdict']=='负','Original verdict changed')
        mean,ci = comparison['overall']['mean_delta'],comparison['overall']['ci95']
        baseline = key.split('-')[1]
        require(mean<0 and ci[0]<=mean<=ci[1]<0 and math.isclose(mean,rates['learned']-rates[baseline],abs_tol=1e-14),'Wrong comparison direction')
    analysis = copy.deepcopy(summary)
    analysis['result_signoff'] = 'accepted'
    for comparison in analysis['comparisons'].values(): comparison['formal_verdict']='负'
    def source(name): return dict(path=name,sha256=PINNED_FILES[name])
    release = dict(schema_version='formal-result-release-v1',release_version=VERSION,
                   released_on='2026-11-12',release_status='released',
                   release_scope='reviewed_synthetic_negative_results_only',
                   reviews={role:dict(ruling='accepted_with_notes',**source(next(n for n in PINNED_FILES if f'/{role}_formal_results_release_review_' in n))) for role in ('A','B','C')},
                   sources=dict(summary=source(BATCH+'analysis/summary.json'),
                                frozen_manifest=source(BATCH+'frozen_manifest.json'),
                                run_index=source(BATCH+'run_index.jsonl'),
                                result_zip=source(BATCH+'formal_v2_delegated_results_20261110.zip')),
                   verified_evidence_sha256=PINNED_FILES,
                   original_status=dict(result_signoff='pending',formal_verdict='未完成',bytes_unchanged=True),
                   claims=dict(statistical_verdict='负',superiority_claim=False,real_satellite_claim=False,
                               familywise_claim=False,training_enabled=False,hybrid_enabled=False),
                   engineering=dict(C_original_package_acceptance='accepted_with_notes',
                                    C_accepted_package_sha256='8b79351f35447fd8764451bfa0151447316dbd90f16b0be1d8f15bbd212664f4',
                                    scope='C receipt covers the original November 10 package; new delivery version requires separate acceptance'),
                   policy_weighted_on_time_rate=rates,success_payload_bytes=payloads,analysis=analysis)
    return release


def validate_release(release,root=ROOT):
    require(release==build_release(root),'release content, claims, provenance or status mismatch')
    return True


def write_release(output,root=ROOT):
    output = Path(output)
    require(not output.exists(),'Output must be new')
    release = build_release(root)
    validate_release(release,root)
    output.mkdir(parents=True)
    for name,value in [('release.json',release),('analysis.json',release['analysis'])]:
        (output/name).write_bytes(canonical(value))
    sums = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}
    (output/'SHA256SUMS.json').write_bytes(canonical(sums))
    return release


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--verify',type=Path)
    args = parser.parse_args()
    try:
        require(bool(args.output) != bool(args.verify),'Choose --output or --verify')
        if args.output: write_release(args.output)
        else: validate_release(json.loads(args.verify.read_bytes()))
        print('passed: '+VERSION+'; both comparisons negative; original evidence unchanged')
    except (ValueError,KeyError,TypeError,OSError) as error:
        parser.exit(1,'release rejected: '+str(error)+'\n')
