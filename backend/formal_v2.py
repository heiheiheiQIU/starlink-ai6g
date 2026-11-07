"""Register the holdout before producing inputs. No policy runs in this module."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.api.inference import inspect_model
from backend.cli import _hash, _json_bytes
from backend.formal_freeze import ROOT, file_hash, local_file, read_json, source_hashes, validate_analysis_protocol
from backend.formal_inputs import _config, _content_hash, _validate_protocol

REGISTRATION = ROOT/'experiments/formal_v2/registration.json'
DESIGN = ROOT/'experiments/formal_v1/protocol.json'
ARCHIVE = ROOT/'experiments/formal_v1/input_manifest.json'
ANALYSIS = ROOT/'experiments/formal_v1/analysis_protocol.json'
MODEL = ROOT/'configs/learned_policy.json'
PILOT = ROOT/'data/teacher/a_n4_pilot_v1/sources.jsonl'
DEV = ROOT/'experiments/test_matrix.json'
TEMPLATE = ROOT/'configs/scenarios/r3_normal.json'
SCHEMA = 'formal-input-manifest-v2'


def isolation():
    reg = read_json(REGISTRATION)
    archived = read_json(ARCHIVE)['trajectories']
    retired = {row['seed'] for row in archived}
    dev = {row['environment_seed'] for row in read_json(DEV)['trajectories']}
    pilot = {json.loads(line)['seed'] for line in PILOT.read_text(encoding='utf-8').splitlines()}
    registered = set(range(reg['seed_start'], reg['seed_end']+1))
    overlap = registered & (retired | dev | pilot)
    if (reg['version'] != 'formal_v2' or reg['policy_ids'] != ['edf','value','learned']
            or (reg['cells'], reg['trajectories_per_cell']) != (18,10)
            or len(registered) != 180 or retired != set(range(200000,200180)) or overlap):
        raise ValueError('Invalid registration or overlapping seed range')
    return dict(registered_count=180, registered_range=[min(registered), max(registered)],
                retired_count=len(retired), retired_range=[min(retired),max(retired)],
                development_count=len(dev), pilot_count=len(pilot), overlap=sorted(overlap),
                old_teacher_namespace='Observation sources have no full scenario seeds; A source review required')


def subject():
    validate_analysis_protocol(read_json(ANALYSIS))
    return dict(stage='before_formal_v2_generation', seed_audit=isolation(),
                registration_sha256=file_hash(REGISTRATION), design_sha256=file_hash(DESIGN),
                archive_sha256=file_hash(ARCHIVE), model_config_sha256=file_hash(MODEL),
                model=inspect_model(MODEL), analysis_protocol_sha256=file_hash(ANALYSIS),
                code_sha256=_hash(source_hashes()), template_sha256=file_hash(TEMPLATE),
                source_inputs={p.relative_to(ROOT).as_posix():file_hash(p) for p in
                    (PILOT, DEV, ROOT/'data/teacher/sources/a_n3_20_v2.jsonl')})


def check_receipts(receipts):
    expected = subject()
    if set(receipts) != set('ABC'):
        raise ValueError('Three independent pre-generation receipts are required')
    reviewers = set()
    for role, receipt in receipts.items():
        if (receipt.get('role') != role or receipt.get('subject') != expected
                or receipt.get('status') != 'accepted' or not receipt.get('notes')
                or not receipt.get('reviewer')):
            raise ValueError('Invalid pre-generation receipt for '+role)
        reviewers.add(receipt['reviewer'])
    if len(reviewers) != 3:
        raise ValueError('Three independent reviewers required')


def expected_inputs():
    reg = read_json(REGISTRATION)
    design = read_json(DESIGN)
    _validate_protocol(design)
    cells = {cell['cell_id']:cell for cell in design['cells']}
    template = read_json(TEMPLATE)
    seen = {row['content_hash'] for row in read_json(ARCHIVE)['trajectories']}
    for index, old in enumerate(design['trajectories']):
        trace = dict(trajectory_id=old['trajectory_id'].replace('formal_v1_', 'formal_v2_', 1),
                     cell_id=old['cell_id'], seed=reg['seed_start']+index)
        cfg = _config(design, cells[trace['cell_id']], trace, template)
        digest = _content_hash(cfg)
        if digest in seen:
            raise ValueError('Repeated content in engineering or holdout matrix')
        seen.add(digest)
        row = dict(**trace, config_path='configs/'+trace['trajectory_id']+'.json',
                   config_sha256=_hash(cfg), input_hash=_hash(cfg['scenario']), content_hash=digest)
        yield row, cfg


def verify(path):
    manifest = read_json(path)
    if manifest.get('schema_version') != SCHEMA or manifest.get('status') != 'candidate_pending_review':
        raise ValueError('Expected v2 candidate')
    check_receipts(manifest['generation_receipts'])
    root = path.parent
    if local_file(root,'protocol.json').read_bytes() != REGISTRATION.read_bytes():
        raise ValueError('Holdout registration mismatch')
    rows = []
    for row, _ in expected_inputs():
        if file_hash(local_file(root,row['config_path'])) != row['config_sha256']:
            raise ValueError('Holdout config hash mismatch')
        rows.append(row)
    expected_files = {r['config_path'] for r in rows} | {'manifest.json','protocol.json'}
    actual_files = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual_files != expected_files or manifest['trajectories'] != rows:
        raise ValueError('Holdout inventory mismatch')
    return manifest


def materialize(receipt_dir, output):
    if output.exists():
        raise ValueError('Output must be new')
    receipts = {role:read_json(receipt_dir/(role+'.json')) for role in 'ABC'
                if (receipt_dir/(role+'.json')).is_file()}
    check_receipts(receipts)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as scratch:
        stage = Path(scratch)/'candidate'
        (stage/'configs').mkdir(parents=True)
        (stage/'protocol.json').write_bytes(REGISTRATION.read_bytes())
        rows = []
        for row, config in expected_inputs():
            (stage/row['config_path']).write_bytes(_json_bytes(config))
            rows.append(row)
        manifest = dict(schema_version=SCHEMA, status='candidate_pending_review',
                        generation_receipts=receipts, trajectories=rows)
        (stage/'manifest.json').write_bytes(_json_bytes(manifest))
        verify(stage/'manifest.json')
        stage.rename(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--subject', action='store_true')
    group.add_argument('--receipts', type=Path)
    group.add_argument('--verify', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.subject:
        print(json.dumps(subject(), ensure_ascii=False, indent=2))
    elif args.verify:
        print('verified trajectories:', len(verify(args.verify)['trajectories']))
    elif args.output:
        materialize(args.receipts, args.output)
    else:
        parser.error('--receipts requires --output')
