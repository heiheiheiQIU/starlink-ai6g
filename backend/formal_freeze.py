"""Immutable formal envelope around the unchanged input candidate.

Receipts establish traceability, not cryptographic proof of a human signature.
Only the actual reviewers may author production acceptance receipts.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile

import numpy as np

from backend.api.inference import inspect_model
from backend.formal_inputs import verify_inputs
from backend.policies.learned import _config

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ('edf', 'value', 'learned')
EXPECTED_ANALYSIS = dict(
    schema_version='formal-analysis-protocol-v1', metric='weighted_on_time_rate',
    policies=list(POLICIES), comparisons=['learned-edf', 'learned-value'],
    bootstrap_replicates=10000, bootstrap_seed=20261104, confidence=.95,
    interval='percentile', aggregation='equal_weight_18_cells_stratified_paired',
    sampling_unit='trajectory_within_cell', numpy_version='2.1.3',
    sort_order='cell_id,trajectory_id,policy_id,attempt',
    multiplicity='pointwise_intervals_no_familywise_claim', max_retries=1,
    retry_selection='first_success_keep_all_attempts',
    missing_policy='incomplete_no_imputation_no_cell_dropping',
    domain='synthetic_out_of_zero_loss_training_domain', release_gate='ABC_result_receipts_required')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                  indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def local_file(root, name):
    """Only ordinary relative paths below root; reject aliases and junctions."""
    if not isinstance(name, str) or '\\' in name or ':' in name:
        raise ValueError('Invalid relative artifact path')
    rel = PurePosixPath(name)
    if rel.is_absolute() or not rel.parts or any(p in ('.', '..') for p in rel.parts) or str(rel) != name:
        raise ValueError('Invalid relative artifact path')
    root = Path(root).resolve()
    path = root.joinpath(*rel.parts)
    if path.resolve() != path or not path.is_file():
        raise ValueError(f'Missing or aliased artifact: {name}')
    return path


def validate_analysis_protocol(protocol):
    if protocol != EXPECTED_ANALYSIS or np.__version__ != protocol.get('numpy_version'):
        raise ValueError('Unsupported analysis protocol or NumPy version')
    return protocol


def source_hashes():
    paths = sorted((ROOT/'backend').rglob('*.py')) + sorted((ROOT/'training').glob('*.py'))
    paths += [ROOT/'experiments/analyze_formal.py'] if (ROOT/'experiments/analyze_formal.py').exists() else []
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_text(encoding='utf-8-sig').encode()).hexdigest()
            for p in paths}


def _binding(candidate, model_config, analysis_protocol, metadata):
    sources = source_hashes()
    # Source hashes are authoritative for uncommitted builds and no-Git releases.
    revision = None
    if (ROOT/'.git').exists():
        try:
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
            revision = result.stdout.strip() if result.returncode == 0 else None
        except OSError:
            pass
    return dict(candidate_manifest_sha256=file_hash(candidate), model_config_sha256=file_hash(model_config),
                analysis_protocol_sha256=file_hash(analysis_protocol), model_artifacts_sha256=metadata['artifacts_sha256'],
                source_sha256=sources, code_revision=revision)


def freeze_binding(candidate_manifest: Path, model_config: Path, analysis_protocol: Path) -> dict:
    verify_inputs(candidate_manifest)
    validate_analysis_protocol(read_json(analysis_protocol))
    return _binding(candidate_manifest, model_config, analysis_protocol, inspect_model(model_config))


def _review(review_path, binding, candidate):
    review = read_json(review_path)
    scope = review.get('data_scope')
    if (review.get('schema_version') != 'formal-freeze-review-v1' or scope not in ('formal', 'test_fixture')
            or review.get('binding') != binding):
        raise ValueError('Review subject does not match freeze binding')
    rows = review.get('receipts', [])
    if len(rows) != 3 or {r.get('role') for r in rows} != set('ABC'):
        raise ValueError('A/B/C receipts required')
    leak = review['leakage']
    copies = {}; reviewers = set()
    for row in rows:
        path = local_file(review_path.parent, row['path'])
        if file_hash(path) != row['sha256']: raise ValueError('Receipt hash mismatch')
        receipt = read_json(path)
        if (receipt.get('schema_version') != 'formal-freeze-receipt-v1'
                or receipt.get('role') != row['role'] or receipt.get('status') not in ('accepted', 'accepted_with_notes')
                or receipt.get('binding') != binding or receipt.get('data_scope') != scope
                or receipt.get('leakage_sha256') != leak['sha256']
                or not receipt.get('reviewer') or not receipt.get('reviewed_at') or not receipt.get('notes')):
            raise ValueError('Receipt pending, incomplete, or wrong subject')
        reviewers.add(receipt['reviewer'])
        copies[f'receipts/{row["role"]}.json'] = path
    if len(reviewers) != 3: raise ValueError('Independent reviewers required')
    path = local_file(review_path.parent, leak['path'])
    evidence = read_json(path)
    if (file_hash(path) != leak['sha256'] or evidence.get('schema_version') != 'formal-leakage-review-v1'
            or evidence.get('status') != 'accepted' or evidence.get('data_scope') != scope
            or evidence.get('candidate_manifest_sha256') != binding['candidate_manifest_sha256']
            or evidence.get('model_artifacts_sha256') != binding['model_artifacts_sha256']
            or not evidence.get('source_files') or not evidence.get('method')):
        raise ValueError('Leakage review missing or wrong subject')
    for name, digest in evidence['source_files'].items():
        source = local_file(path.parent, name)
        if file_hash(source) != digest: raise ValueError('Leakage source hash mismatch')
        copies['receipts/'+name] = source
    rows = candidate['trajectories']
    if {r['seed'] for r in rows} & set(evidence['excluded_seeds']): raise ValueError('Training seed collision')
    if {r['content_hash'] for r in rows} & set(evidence['excluded_content_hashes']): raise ValueError('Training content collision')
    copies['receipts/leakage.json'] = path
    return scope, copies


def frozen_model_config(root):
    config = read_json(Path(root)/'model_config.json')
    config['package_dir'] = str(Path(root).resolve()/'model')
    return config


def freeze_inputs(candidate_manifest: Path, review_path: Path, model_config: Path,
                  analysis_protocol: Path, output: Path) -> dict:
    output = Path(output)
    if output.exists(): raise ValueError('Output must be new')
    binding = freeze_binding(candidate_manifest, model_config, analysis_protocol)
    candidate = verify_inputs(candidate_manifest)
    scope, copies = _review(review_path, binding, candidate)
    model_dir = Path(_config(model_config)['package_dir'])
    copies.update({f'model/{name}': model_dir/name for name in binding['model_artifacts_sha256']})
    copies.update({'model_config.json': model_config, 'analysis_protocol.json': analysis_protocol})
    for path in candidate_manifest.parent.rglob('*'):
        if path.is_file():
            name = path.relative_to(candidate_manifest.parent).as_posix()
            copies['candidate/'+name] = local_file(candidate_manifest.parent, name)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.freeze-', dir=output.parent))
    try:
        for name, source in copies.items():
            dest = staging/name; dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        review = read_json(review_path)
        for row in review['receipts']: row['path'] = f'receipts/{row["role"]}.json'
        review['leakage']['path'] = 'receipts/leakage.json'
        write_json(staging/'review.json', review)
        files = {p.relative_to(staging).as_posix(): file_hash(p) for p in sorted(staging.rglob('*')) if p.is_file()}
        manifest = dict(schema_version='formal-frozen-manifest-v1', status='frozen', data_scope=scope,
                        binding=binding, trajectories=candidate['trajectories'], artifacts_sha256=files)
        write_json(staging/'manifest.json', manifest)
        verify_frozen(staging/'manifest.json')
        staging.rename(output)
        return manifest
    finally:
        if staging.exists() and staging.resolve().parent == output.parent.resolve() and staging.name.startswith('.freeze-'):
            shutil.rmtree(staging)


def verify_frozen(manifest_path: Path) -> dict:
    manifest_path = Path(manifest_path); root = manifest_path.parent
    manifest = read_json(manifest_path)
    if (manifest.get('schema_version') != 'formal-frozen-manifest-v1' or manifest.get('status') != 'frozen'
            or set(manifest) != {'schema_version', 'status', 'data_scope', 'binding', 'trajectories', 'artifacts_sha256'}):
        raise ValueError('Expected frozen envelope')
    files = manifest['artifacts_sha256']
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} - {'manifest.json'}
    required = {'candidate/manifest.json', 'candidate/protocol.json', 'model_config.json', 'analysis_protocol.json',
                'review.json', 'receipts/A.json', 'receipts/B.json', 'receipts/C.json', 'receipts/leakage.json'}
    required |= {'model/'+name for name in ('weights.npz', 'normalization.json', 'training_summary.json', 'model_card.md', 'manifest.json')}
    required |= {'candidate/'+r['config_path'] for r in manifest['trajectories']}
    leakage = read_json(local_file(root, 'receipts/leakage.json'))
    required |= {'receipts/'+name for name in leakage.get('source_files', {})}
    if set(files) != actual or actual != required: raise ValueError('Frozen artifact set mismatch')
    for name, digest in files.items():
        if file_hash(local_file(root, name)) != digest: raise ValueError(f'Frozen artifact hash mismatch: {name}')
    candidate = verify_inputs(root/'candidate/manifest.json')
    if candidate['trajectories'] != manifest['trajectories']: raise ValueError('Frozen trajectory mismatch')
    validate_analysis_protocol(read_json(root/'analysis_protocol.json'))
    metadata = inspect_model(frozen_model_config(root))
    binding = manifest['binding']
    expected = dict(candidate_manifest_sha256=file_hash(root/'candidate/manifest.json'),
                    model_config_sha256=file_hash(root/'model_config.json'),
                    analysis_protocol_sha256=file_hash(root/'analysis_protocol.json'),
                    model_artifacts_sha256=metadata['artifacts_sha256'], source_sha256=source_hashes(),
                    code_revision=binding.get('code_revision'))
    if binding != expected: raise ValueError('Frozen binding/source mismatch')
    scope, _ = _review(root/'review.json', binding, candidate)
    if scope != manifest['data_scope']: raise ValueError('Frozen scope mismatch')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--model-config', type=Path, default=ROOT/'configs/learned_policy.json')
    parser.add_argument('--analysis-protocol', type=Path, default=ROOT/'experiments/formal_v1/analysis_protocol.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.verify:
        result = verify_frozen(args.verify)
    elif args.candidate and args.review and args.output:
        result = freeze_inputs(args.candidate, args.review, args.model_config, args.analysis_protocol, args.output)
    else: parser.error('Use --verify or --candidate --review --output')
    print(json.dumps(dict(status=result['status'], data_scope=result['data_scope'], trajectories=len(result['trajectories']))))


if __name__ == '__main__': main()
