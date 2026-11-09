"""Prepare the review directory for a generated holdout, then index signed receipts."""
import argparse
from pathlib import Path
import json
import shutil
from tempfile import TemporaryDirectory

from backend.cli import _hash
from backend.experiments import build_config
from backend.formal_freeze import file_hash, freeze_binding, read_json, write_json
from backend.formal_v2 import ANALYSIS, ARCHIVE, AUDIT_FILES, DEV, MODEL, PILOT, ROOT, verify
from backend.simulator.engine import create_state, observe


def scenario_key(scene):
    content = dict(scene)
    content.pop('scenario_id', None)
    if content.get('channel'):
        content['channel'] = dict(content['channel'])
        content['channel'].pop('seed', None)
    return _hash(content)


def observation_key(observation):
    return _hash({key:value for key,value in observation.items()
                  if key not in {'run_id','policy_id','forecast_version'}})


def prepare(candidate_path, destination):
    if destination.exists():
        raise ValueError('Review directory must be new')
    candidate = verify(candidate_path)
    binding = freeze_binding(candidate_path, MODEL, ANALYSIS)
    archive = read_json(ARCHIVE)['trajectories']
    pilot = [json.loads(line) for line in PILOT.read_text(encoding='utf-8').splitlines()]
    development = read_json(DEV)
    cells = {cell['cell_id']:cell for cell in development['cells']}
    exclusions = {row['content_hash'] for row in archive}
    exclusions.update(scenario_key(row['scenario']) for row in pilot)
    seeds = {row['seed'] for row in archive + pilot}
    for trace in development['trajectories']:
        seed = trace['environment_seed']
        seeds.add(seed)
        exclusions.add(scenario_key(build_config(cells[trace['cell_id']], seed)['scenario']))
    old = ROOT/'data/teacher/sources/a_n3_20_v2.jsonl'
    old_observations = {observation_key(json.loads(line)['observation'])
                        for line in old.read_text(encoding='utf-8').splitlines()}
    for trace in candidate['trajectories']:
        scene = read_json(candidate_path.parent/trace['config_path'])['scenario']
        public = observe(create_state(scene)).model_dump(mode='json')
        if (trace['seed'] in seeds or trace['content_hash'] in exclusions
                or observation_key(public) in old_observations):
            raise ValueError('Source overlap at '+trace['trajectory_id'])
    destination.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as scratch:
        stage = Path(scratch)/'review'
        sources = {}
        for path in (ARCHIVE, DEV, PILOT, old, *(ROOT/name for name in AUDIT_FILES)):
            name = 'sources/'+path.relative_to(ROOT).as_posix()
            target = stage/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
            sources[name] = file_hash(target)
        approved = candidate['generation_receipts']['A']['subject']['audit_files_sha256']
        if any(sources['sources/'+name] != digest for name, digest in approved.items()):
            raise ValueError('Copied audit files differ from the pre-generation receipts')
        write_json(stage/'leakage.json',dict(schema_version='formal-leakage-review-v1',
            data_scope='formal',status='pending',candidate_manifest_sha256=file_hash(candidate_path),
            model_artifacts_sha256=binding['model_artifacts_sha256'],source_files=sources,
            excluded_seeds=sorted(seeds),excluded_content_hashes=sorted(exclusions),
            method='Checked retired inputs, reconstructed R5 scenarios, pilot scenarios and seeds; compared initial public observations to 20 legacy teacher observations. Legacy records lack complete scenario seeds. A reviews provenance and splits; C reviews inventory and hashes.'))
        write_json(stage/'binding.json',binding)
        for role in 'ABC':
            write_json(stage/(role+'.json'),dict(schema_version='formal-freeze-receipt-v1',
                role=role,data_scope='formal',status='pending',reviewer=None,reviewed_at=None,
                binding=binding,leakage_sha256=None,notes=''))
        stage.rename(destination)


def index(folder):
    leakage = folder/'leakage.json'
    digest = file_hash(leakage)
    binding = read_json(folder/'binding.json')
    if read_json(leakage)['status'] != 'accepted':
        raise ValueError('Leakage review pending')
    rows = []
    for role in 'ABC':
        path = folder/(role+'.json')
        receipt = read_json(path)
        if (receipt['role'] != role or receipt['binding'] != binding
                or receipt['leakage_sha256'] != digest or receipt['status'] not in ('accepted','accepted_with_notes')):
            raise ValueError('Receipt pending or subject mismatch: '+role)
        rows.append(dict(role=role,path=path.name,sha256=file_hash(path)))
    write_json(folder/'review.json',dict(schema_version='formal-freeze-review-v1',data_scope='formal',
        binding=binding,receipts=rows,leakage=dict(path=leakage.name,sha256=digest)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--candidate', type=Path)
    group.add_argument('--index', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.index:
        index(args.index)
    elif args.output:
        prepare(args.candidate,args.output)
    else:
        parser.error('--candidate requires --output')
