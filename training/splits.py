"""Deterministic, scenario-disjoint partition of verified teacher data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile


def build_split_manifest(samples_path: Path, output_path: Path, *, split_seed: int,
                         split_counts: tuple[int, int, int] = (12, 4, 4)) -> dict[str, object]:
    samples_path, output_path = Path(samples_path), Path(output_path)
    raw = samples_path.read_bytes()
    summary_raw = (samples_path.parent / 'summary.json').read_bytes()
    summary = json.loads(summary_raw)
    manifest = json.loads((samples_path.parent / 'manifest.json').read_bytes())
    hashes = manifest.get('output_sha256', {})
    digest = hashlib.sha256(raw).hexdigest()
    if hashes.get('samples.jsonl') != digest or hashes.get('summary.json') != hashlib.sha256(summary_raw).hexdigest():
        raise ValueError('Source hash mismatch')
    if summary.get('status') != 'ready_for_split':
        raise ValueError('Dataset is not ready for split')
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if (summary.get('total') != len(rows) or summary.get('eligible') != len(rows)
            or summary.get('ineligible') != 0 or summary.get('failures') != 0):
        raise ValueError('Summary counts do not match source')
    sample_ids = set()
    scenarios = {}
    for row in rows:
        sample, scenario = row.get('sample_id'), row.get('scenario_id')
        if not isinstance(sample, str) or not sample.strip() or not isinstance(scenario, str) or not scenario.strip():
            raise ValueError('Invalid identifiers')
        if sample in sample_ids:
            raise ValueError('Duplicate sample ID')
        if row.get('label_eligible') is not True or row.get('solver_status') != 'OPTIMAL' or row.get('gap') != 0.0:
            raise ValueError('Ineligible record')
        sample_ids.add(sample)
        scenarios.setdefault(scenario, []).append(sample)
    if len(split_counts) != 3 or any(type(n) is not int or n < 0 for n in split_counts) or len(scenarios) != sum(split_counts):
        raise ValueError('Unexpected scenario count')
    ordered = sorted(scenarios, key=lambda s: (hashlib.sha256(f'{split_seed}:{s}'.encode('utf-8')).hexdigest(), s))
    splits = {}
    offset = 0
    for name, count in zip(('train', 'validation', 'test'), split_counts):
        ids = ordered[offset:offset + count]
        samples = sorted(sample for scenario in ids for sample in scenarios[scenario])
        splits[name] = {'scenario_ids': ids, 'sample_ids': samples,
                        'scenario_count': len(ids), 'sample_count': len(samples)}
        offset += count
    intersections = {}
    for left, right in (('train', 'validation'), ('train', 'test'), ('validation', 'test')):
        intersections[f'{left}_{right}'] = {field: sorted(set(splits[left][field]) & set(splits[right][field])) for field in ('scenario_ids', 'sample_ids')}
    result = {'split_algorithm_version': 'scenario-sha256-v1', 'split_seed': split_seed,
              'source_jsonl_sha256': digest, 'splits': splits, 'intersections': intersections}
    content = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.splits-', dir=output_path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, output_path)
        except FileExistsError:
            if output_path.read_bytes() != content:
                raise ValueError('Refusing to overwrite differing split manifest')
    finally:
        os.unlink(temp)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=Path, default=Path('data/teacher/a_n3_20/samples.jsonl'))
    parser.add_argument('--output', type=Path, default=Path('data/teacher/a_n3_20/splits.json'))
    parser.add_argument('--seed', type=int, default=20261030)
    args = parser.parse_args()
    build_split_manifest(args.samples, args.output, split_seed=args.seed)


if __name__ == '__main__':
    main()
