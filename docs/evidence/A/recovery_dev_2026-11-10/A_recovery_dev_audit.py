"""Read-only, standard-library A audit of the frozen B development pilot.

No B audit, generator, solver or simulator code is imported or executed. Passing
means evidence consistency and development coverage only, never training approval.
"""
import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

EXPECTED_SOURCE_COUNT = 30
EXPECTED_STATE_COUNT = 60
EXPECTED_SPLITS = {"train": 18, "validation": 6, "test": 6}
EXPECTED_SEEDS = set(range(710000, 710030))
REQUIRED_FAMILIES = {"wait_then_send", "last_chance", "task_conflict", "must_wait"}
VERSION = 'b-recovery-dev-v1'
FORMAL_MANIFEST = 'docs/evidence/B/formal_v2_candidate_2026-11-09/candidate/manifest.json'
FORMAL_ZIP = 'docs/evidence/B/delegated_execution_2026-11-10/formal_v2_delegated_results_20261110.zip'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def content_hash(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode('utf-8'))


def semantic_hash(observation):
    """Ignore provenance IDs while retaining all physical public values."""
    value = copy.deepcopy(observation)
    for key in ('run_id', 'policy_id', 'forecast_version'):
        value.pop(key, None)
    for key in ('model_version', 'uncertainty_method'):
        value.get('health', {}).pop(key, None)
    for window in value.get('forecast_windows', []):
        for key in ('forecast_version', 'window_id'):
            window.pop(key, None)
    for task in value.get('tasks', []):
        for key in ('task_id', 'business_class', 'data_location'):
            task.pop(key, None)
    return content_hash(value)


def public_observation(scenario, now=0.0, source_id='r2_minimal_validation'):
    """Independent public projection, limited to initial/idle-only captures.

    Historical exclusion scenarios use time zero; pilot captures contain one
    idle command. This deliberately does not implement transmissions or teachers.
    """
    health = copy.deepcopy(max((h for h in scenario['health_observations']
                               if h['available_at_s'] <= now), key=lambda h: h['available_at_s']))
    if now and scenario.get('protocol'):
        elapsed = now - max(0.0, health['observed_at_s'])
        if elapsed > 0:
            powers = scenario['powers']
            change = (powers['solar_W'] - powers['base_W'] - powers['compute_W']) * elapsed / 3600
            lower = min(health['capacity_lower_Wh'], max(0.0, health['energy_lower_Wh'] + change))
            estimate = min(health['capacity_Wh_est'], max(0.0, health['soc_est'] * health['capacity_Wh_est'] + change))
            health['soc_est'] = estimate / health['capacity_Wh_est']
            health['soc_lower'] = min(health['soc_est'], lower / health['capacity_lower_Wh']) if health['capacity_lower_Wh'] else 0.0
            health['energy_lower_Wh'] = health['soc_lower'] * health['capacity_lower_Wh']
            health['reason_codes'] = list(dict.fromkeys([*health['reason_codes'], 'ENERGY_PROPAGATED']))
    tasks = [copy.deepcopy(t) for t in sorted(scenario['tasks'], key=lambda t: (t['arrival_s'], t['task_id']))
             if t['arrival_s'] <= now <= t['deadline_s'] and t['remaining_bytes'] > 0]
    return dict(schema_version='1.0', run_id=source_id, policy_id='pilot-source', sim_time_s=now,
                tasks=tasks, forecast_windows=scenario['forecast_windows'], health=health, inflight=None,
                cache_bytes=sum(t['remaining_bytes'] for t in tasks), forecast_version=scenario['forecast_version'])


def audit(pilot, root, source_commit):
    result = dict(status='failed', source_commit=source_commit, training_enabled=False,
                  training_approved=False, file_sha256={}, checks={}, gaps=[])
    hashes = result['file_sha256']

    def read(base, name, expected=None):
        path = (base / name).resolve()
        require(path.is_relative_to(base.resolve()), 'Evidence path escapes root: ' + name)
        raw = path.read_bytes()
        sha = digest(raw)
        hashes[('pilot/' if base == pilot else 'repo/') + name] = sha
        require(expected is None or expected == sha, 'SHA256 mismatch: ' + name)
        return raw

    def load(base, name, expected=None):
        return json.loads(read(base, name, expected))

    def rows(raw):
        return [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]

    try:
        require(re.fullmatch(r'[0-9a-f]{40}', source_commit) is not None, 'Expected full source commit SHA')
        manifest = load(pilot, 'manifest.json')
        require(manifest['dataset_version'] == VERSION and manifest['training_enabled'] is False,
                'Manifest dataset/training binding')
        expected_outputs = {'attempts.jsonl', 'config.json', 'diagnostics.jsonl', 'leakage.json',
                            'samples.jsonl', 'source_splits.json', 'sources.jsonl', 'summary.json', 'teacher_config.json'}
        require(set(manifest['output_sha256']) == expected_outputs, 'Missing/unexpected pilot output binding')
        outputs = {name: read(pilot, name, sha) for name, sha in manifest['output_sha256'].items()}
        for name, sha in manifest['code_sha256'].items():
            read(root, name, sha)
        require(bool(manifest['code_sha256']), 'Missing code evidence')
        teacher_raw = read(root, 'configs/teacher.json', manifest['teacher_config_sha256'])
        teacher = json.loads(teacher_raw)
        require(teacher == json.loads(outputs['teacher_config.json']), 'Teacher config content binding')
        result['checks']['manifest_hashes'] = 'passed'
        sources = rows(outputs['sources.jsonl'])
        states = rows(outputs['attempts.jsonl'])
        config = json.loads(outputs['config.json'])
        summary = json.loads(outputs['summary.json'])
        splits = json.loads(outputs['source_splits.json'])['by_source']
        leakage = json.loads(outputs['leakage.json'])
        require(config['training_enabled'] is False and summary['training_enabled'] is False, 'Training must remain disabled')
        require(config['dataset_version'] == summary['dataset_version'] == VERSION, 'Dataset version')
        require(config['source_count'] == EXPECTED_SOURCE_COUNT and config['states_per_source'] == 2
                and config['source_split_counts'] == EXPECTED_SPLITS and config['seed_start'] == 710000, 'Pilot configuration counts')
        require(len(sources) == EXPECTED_SOURCE_COUNT and len(states) == EXPECTED_STATE_COUNT, 'Source/state count')
        by_source = {s['source_id']: s for s in sources}
        require(len(by_source) == len(sources) and set(by_source) == {f'recovery_{i:02d}' for i in range(30)}, 'Source identity')
        require(set(splits) == set(by_source) and dict(Counter(splits.values())) == EXPECTED_SPLITS, 'Source splits')
        require({s['seed'] for s in sources} == EXPECTED_SEEDS, 'Unique source seeds')
        source_hashes = set()
        for source in sources:
            scenario = source['scenario']
            require(scenario['scenario_id'] == source['source_id'] and scenario['channel']['seed'] == source['seed'], 'Scenario identity/seed')
            identity = copy.deepcopy(scenario)
            identity.pop('scenario_id')
            identity['channel'].pop('seed')
            sha = content_hash(identity)
            require(sha == source['content_sha256'] and sha not in source_hashes, 'Source content hash/uniqueness')
            source_hashes.add(sha)
            require(source['capture_after_steps'] == [0, 1] and len(source['evolution_steps']) == 1, 'Capture protocol')
            command = source['evolution_steps'][0]
            require(command['dt_s'] == 2.0 and command['action'] == dict(mode='idle', task_id=None,
                    fallback=False, reason_codes=[], scheduled_bytes=0), 'Independent projection requires declared idle command')
        require({s['family'] for s in sources} == REQUIRED_FAMILIES, 'Required families')
        result['checks']['source_identity_split_uniqueness'] = 'passed'

        prior_seeds, prior_content, prior_semantics = set(), set(), set()
        evidence = leakage['exclusion_evidence']
        needed = {FORMAL_MANIFEST, FORMAL_ZIP} | {p.relative_to(root).as_posix() for p in (root / 'data/teacher').rglob('*.jsonl')}
        require(set(evidence) == needed, 'Exclusion evidence completeness')
        excluded = {name: read(root, name, sha) for name, sha in evidence.items()}
        for name, raw in excluded.items():
            if not name.endswith('.jsonl'):
                continue
            for row in rows(raw):
                if 'seed' in row:
                    prior_seeds.add(row['seed'])
                if 'content_sha256' in row:
                    prior_content.add(row['content_sha256'])
                if isinstance(row.get('scenario'), dict):
                    prior_semantics.add(semantic_hash(public_observation(row['scenario'])))
                if isinstance(row.get('observation'), dict):
                    prior_semantics.add(semantic_hash(row['observation']))
        with zipfile.ZipFile(root / FORMAL_ZIP) as package:
            for row in json.loads(excluded[FORMAL_MANIFEST])['trajectories']:
                member = 'frozen/candidate/' + row['config_path']
                raw = package.read(member)
                hashes['zip/' + member] = digest(raw)
                require(digest(raw) == row['config_sha256'], 'Formal exclusion member hash')
                prior_seeds.add(row['seed'])
                prior_content.add(row['content_hash'])
                prior_semantics.add(semantic_hash(public_observation(json.loads(raw)['scenario'])))
        ranges = [[10000, 10179], [200000, 200179], [410000, 410029], [600000, 600179]]
        require(leakage['excluded_seed_ranges_inclusive'] == ranges, 'Excluded seed ranges')
        for start, end in ranges:
            prior_seeds.update(range(start, end + 1))
        require(not (EXPECTED_SEEDS & prior_seeds) and not (source_hashes & prior_content), 'Prior source leakage')

        seen_ids, seen_obs, seen_semantics = set(), set(), set()
        decisions = Counter({k: 0 for k in ('wait_strictly_better', 'tied', 'send_strictly_better', 'no_feasible_send')})
        coverage = dict(non_zero_loss=0, in_flight=0, long_horizon=0)
        for row in states:
            source = by_source[row['source_id']]
            require(row['capture_index'] in (0, 1) and row['state_id'] == f"{source['source_id']}:{row['capture_index']}"
                    and row['state_id'] not in seen_ids, 'State identity/uniqueness')
            seen_ids.add(row['state_id'])
            require(row['seed'] == source['seed'] and row['family'] == source['family'] and row['split'] == splits[source['source_id']], 'State source/split binding')
            obs = row['observation']
            sha = content_hash(obs)
            require(sha == row['observation_sha256'] and sha not in seen_obs, 'Observation content hash/uniqueness')
            seen_obs.add(sha)
            require(obs == public_observation(source['scenario'], float(row['capture_index'] * 2), source['source_id']), 'State public observation/source evolution')
            semantic = semantic_hash(obs)
            require(semantic not in seen_semantics and semantic not in prior_semantics, 'Semantic observation leakage')
            seen_semantics.add(semantic)
            require(row['label_content_sha256'] == content_hash({k: v for k, v in row.items() if k not in ('elapsed_ms', 'label_content_sha256')}), 'Label content hash')
            require(row['solver_status'] == 'OPTIMAL' and row['gap'] == 0.0 and row['label_eligible'] is True
                    and row['exclusion_reasons'] == [], 'Solver status/eligibility')
            require(row['teacher_config_sha256'] == manifest['teacher_config_sha256'] and row['teacher_version'] == teacher['version']
                    and row['diagnostics']['teacher_version'] == teacher['version'] and row['dataset_version'] == VERSION, 'Teacher binding')
            require(all(c['limited'] is None for c in row['diagnostics']['candidates']), 'Limited solver candidate')
            scores = row['candidate_scores']
            keys = {(s['task_id'], s['mode']) for s in scores}
            require(len(keys) == len(scores) and keys == {(None, 'idle')} | {(t['task_id'], mode) for t in obs['tasks'] for mode in ('robust', 'fast')}, 'Candidate identity/completeness')
            require(all(type(s['feasible']) is bool and isinstance(s['score'], (float, int)) and math.isfinite(s['score']) for s in scores), 'Candidate score validity')
            idle = next(s for s in scores if s['mode'] == 'idle')
            require(idle['feasible'], 'Idle must be feasible')
            sends = [s['score'] for s in scores if s['mode'] != 'idle' and s['feasible']]
            delta = max(sends) - idle['score'] if sends else None
            decision = ('no_feasible_send' if delta is None else 'send_strictly_better' if delta > 1e-9
                        else 'wait_strictly_better' if delta < -1e-9 else 'tied')
            require(decision == row['decision_class'], 'Decision class')
            decisions[decision] += 1
            scenario = source['scenario']
            loss = scenario.get('channel', {}).get('ack_loss_prob', 0) > 0 or any(
                p['robust_loss_prob'] > 0 or p['fast_loss_prob'] > 0
                for w in scenario['true_windows'] + obs['forecast_windows'] for p in w['loss_profile'])
            coverage['non_zero_loss'] += int(loss)
            coverage['in_flight'] += int(obs['inflight'] is not None)
            horizon = max([obs['sim_time_s']] + [t['deadline_s'] for t in obs['tasks']] + [w['end_s'] for w in obs['forecast_windows']]) - obs['sim_time_s']
            coverage['long_horizon'] += int(horizon > teacher['horizon_s'])
        require(rows(outputs['samples.jsonl']) == states and not rows(outputs['diagnostics.jsonl']), 'Samples/attempts/diagnostics partition')
        require(summary['sources'] == len(sources) and summary['states'] == len(states)
                and summary['eligible'] == len(states) and summary['ineligible'] == 0 and summary['failures'] == []
                and summary['source_split_counts'] == EXPECTED_SPLITS
                and summary['state_split_counts'] == dict(Counter(r['split'] for r in states))
                and summary['decision_counts'] == {k: v for k, v in decisions.items() if v}
                and summary['family_counts'] == dict(Counter(s['family'] for s in sources))
                and summary['solver_status_counts'] == {'OPTIMAL': len(states)}, 'Summary independent reconciliation')
        require(leakage['status'] == 'passed' and leakage['prior_observations'] == len(prior_semantics)
                and all(leakage[k] == 0 for k in ('seed_overlap', 'source_content_overlap', 'semantic_observation_overlap')), 'Leakage declaration reconciliation')
        result['checks'].update(state_identity='passed', source_level_split='passed', unique_seed='passed',
                                unique_content_hash='passed', semantic_observation_leakage='passed',
                                label_content_hash='passed', solver_status='passed', teacher_binding='passed',
                                exclusion_evidence_hashes='passed', summary_reconciliation='passed')
        result.update(status='passed', source_count=len(sources), state_count=len(states),
                      source_split_counts=dict(Counter(splits.values())), state_split_counts=dict(Counter(r['split'] for r in states)),
                      family_counts=dict(Counter(s['family'] for s in sources)), decision_counts=dict(decisions),
                      coverage_counts=coverage, prior_observation_count=len(prior_semantics),
                      coverage_definitions=dict(long_horizon='remaining public task/window horizon > teacher horizon_s (240 seconds)',
                                                non_zero_loss='any source true/public forecast loss or ACK loss > 0',
                                                in_flight='public observation inflight is non-null'))
        for name, count in {**coverage, 'wait_strictly_better': decisions['wait_strictly_better']}.items():
            if count == 0:
                result['gaps'].append(name + ': no covered states')
        result['gaps'].append('Consistency audit only; teacher scores are not independently solved; training remains unapproved')
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile, StopIteration) as error:
        result['error'] = f'{type(error).__name__}: {error}'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot-dir', type=Path, required=True)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = audit(args.pilot_dir.resolve(), args.repo_root.resolve(), args.source_commit)
    output = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.write_bytes(output.encode('utf-8'))
    print(output, end='')
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
