"""Recompute the complete development pilot; no training or result release."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from training.generate_policy_pilot import sample_source, label_state
from training.pilot_scenarios import ROOT, sha256_json
from training.recovery_pilot import VERSION, build_sources, make_splits, classify, semantic_observation


def audit(output):
    checks = 0
    def require(condition, message):
        nonlocal checks
        if not condition: raise ValueError(message)
        checks += 1
    def load(name): return json.loads((output/name).read_text(encoding='utf-8'))
    def rows(name): return [json.loads(s) for s in (output/name).read_text(encoding='utf-8').splitlines()]
    manifest = load('manifest.json')
    for name,digest in manifest['output_sha256'].items():
        require(hashlib.sha256((output/name).read_bytes()).hexdigest()==digest,'output hash: '+name)
    for name,digest in manifest['code_sha256'].items():
        require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,'code hash: '+name)
    for name,digest in load('leakage.json')['exclusion_evidence'].items():
        require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,'exclusion evidence hash: '+name)
    require(manifest['training_enabled'] is False,'training gate')
    sources = rows('sources.jsonl')
    require(sources==build_sources(),'source generation changed')
    splits = make_splits(sources)
    require(load('source_splits.json')['by_source']==splits,'source split mismatch')
    require(Counter(splits.values())=={'train':18,'validation':6,'test':6},'split counts')
    attempts = rows('attempts.jsonl')
    require(len(attempts)==60,'attempt count')
    by_id = {r['state_id']:r for r in attempts}
    require(len(by_id)==60,'duplicate state identity')
    teacher = load('teacher_config.json')
    teacher_sha = hashlib.sha256((output/'teacher_config.json').read_bytes()).hexdigest()
    # The copied pretty JSON bytes may differ from the original config; bind values and original hash separately.
    require(teacher==json.loads((ROOT/'configs/teacher.json').read_text(encoding='utf-8')),'teacher configuration changed')
    teacher_sha = hashlib.sha256((ROOT/'configs/teacher.json').read_bytes()).hexdigest()
    require(teacher_sha==manifest['teacher_config_sha256'],'teacher binding')
    semantic_hashes = set()
    for source in sources:
        records = sample_source(source)
        require(len(records)==2,'capture count')
        for record in records:
            row = by_id[record['state_id']]
            for key in ('source_id','family','seed','capture_index','observation','observation_sha256'):
                require(row[key]==record[key],'state replay: '+key)
            digest = semantic_observation(row['observation'])
            require(digest not in semantic_hashes,'duplicate public state')
            semantic_hashes.add(digest)
            require(row['split']==splits[source['source_id']],'state split leaked')
            require(row['dataset_version']==VERSION,'dataset version')
            result = label_state(record,teacher_config=teacher,teacher_config_sha256=teacher_sha,budget_ms=load('config.json')['teacher_budget_ms'])
            for key in ('candidate_scores','solver_status','gap','label_eligible'):
                require(result[key]==row[key],'teacher replay: '+key)
            require(row['decision_class']==classify(row),'decision classification')
            require(row['label_content_sha256']==sha256_json({k:v for k,v in row.items() if k not in {'label_content_sha256','elapsed_ms'}}),'label content hash')
    eligible = [r for r in attempts if r['label_eligible']]
    require(rows('samples.jsonl')==eligible,'samples differ from eligible attempts')
    require(rows('diagnostics.jsonl')==[r for r in attempts if not r['label_eligible']],'diagnostic partition')
    summary = load('summary.json')
    require(summary['decision_counts']==dict(Counter(r['decision_class'] for r in attempts)),'summary counts')
    require(summary['sources']==30 and summary['states']==60 and summary['eligible']==len(eligible),'summary totals')
    require(summary['training_enabled'] is False,'summary training gate')
    require(summary['failures']==[] and load('leakage.json')['status']=='passed','generation failure')
    return dict(status='passed',checks=checks,scope='all_30_sources_60_states_and_teacher_labels_recomputed',training_enabled=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    result = audit(args.input)
    if args.output:
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
