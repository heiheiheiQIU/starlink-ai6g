"""Deterministic, scenario-disjoint partition of verified teacher data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from training.generate_teacher_data import observation_content_sha256


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
    content_hashes = set()
    source_groups = {}
    scenario_groups = {}
    for row in rows:
        sample = row.get('sample_id')
        scenario = row.get('scenario_id')
        source_group = row.get('source_group_id')
        observation = row.get('observation')
        stored_content_hash = row.get('observation_content_sha256')
        identifiers = (sample, scenario, source_group, stored_content_hash)
        if (any(not isinstance(value, str) or not value.strip() for value in identifiers)
                or not isinstance(observation, dict)):
            raise ValueError('Invalid identifiers')
        if sample in sample_ids:
            raise ValueError('Duplicate sample ID')
        if row.get('label_eligible') is not True or row.get('solver_status') != 'OPTIMAL' or row.get('gap') != 0.0:
            raise ValueError('Ineligible record')
        content_hash = observation_content_sha256(observation)
        if stored_content_hash != content_hash:
            raise ValueError('Observation content hash mismatch')
        if content_hash in content_hashes:
            raise ValueError('Duplicate observation content')
        previous_group = scenario_groups.setdefault(scenario, source_group)
        if previous_group != source_group:
            raise ValueError('Scenario spans source groups')
        sample_ids.add(sample)
        content_hashes.add(content_hash)
        source_groups.setdefault(source_group, []).append(row)
    if (len(split_counts) != 3 or any(type(n) is not int or n < 0 for n in split_counts)
            or len(source_groups) != sum(split_counts)):
        raise ValueError('Unexpected source group count')
    ordered = sorted(source_groups, key=lambda group: (
        hashlib.sha256(f'{split_seed}:{group}'.encode('utf-8')).hexdigest(), group))
    splits = {}
    offset = 0
    for name, count in zip(('train', 'validation', 'test'), split_counts):
        ids = ordered[offset:offset + count]
        selected = [row for source_group in ids for row in source_groups[source_group]]
        scenarios = sorted({row['scenario_id'] for row in selected})
        samples = sorted(row['sample_id'] for row in selected)
        hashes = sorted(row['observation_content_sha256'] for row in selected)
        splits[name] = {
            'source_group_ids': ids,
            'scenario_ids': scenarios,
            'sample_ids': samples,
            'observation_content_sha256': hashes,
            'source_group_count': len(ids),
            'scenario_count': len(scenarios),
            'sample_count': len(samples),
            'observation_content_count': len(hashes),
        }
        offset += count
    intersections = {}
    for left, right in (('train', 'validation'), ('train', 'test'), ('validation', 'test')):
        intersections[f'{left}_{right}'] = {
            field: sorted(set(splits[left][field]) & set(splits[right][field]))
            for field in ('source_group_ids', 'scenario_ids', 'sample_ids',
                          'observation_content_sha256')
        }
    result = {'split_algorithm_version': 'source-group-sha256-v2', 'split_seed': split_seed,
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
    parser.add_argument('--train-count', type=int, default=12)
    parser.add_argument('--validation-count', type=int, default=4)
    parser.add_argument('--test-count', type=int, default=4)
    args = parser.parse_args()
    build_split_manifest(args.samples, args.output, split_seed=args.seed,
                         split_counts=(args.train_count, args.validation_count, args.test_count))


if __name__ == '__main__':
    main()
