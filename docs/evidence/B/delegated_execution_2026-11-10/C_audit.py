"""Independent delegated C inventory review; no policy execution.

Run from any directory with the main project's .venv/Scripts/python.exe.
Defaults locate the project from this file; --sign writes ONLY proposed_review/C.json.
The audit report and log are always rewritten beside this script.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sign', action='store_true')
    parser.add_argument('--frozen', type=Path,
                        default=Path('D:/人工智能挑战赛/formal-frozen-verification-20261109'))
    args = parser.parse_args()
    out = Path(__file__).resolve().parent
    root = out.parents[3]
    packet = root/'docs/evidence/B/formal_v2_candidate_2026-11-09'
    final = root/'docs/evidence/B/formal_v2_finalization_2026-11-10'
    review = final/'proposed_review'
    candidate = packet/'candidate'
    revision = '48157a8f4a1cdd7770685b79deb3fe4524b1bf7d'
    leakage_sha = 'e8da2be7968020eb9d1e974ae1cd5b46d3ca89ebec3fab466750bc4df7747018'
    report = dict(schema_version='delegated-C-inventory-audit-v1',
                  reviewer='codex-delegated-C-inventory-review',
                  reviewed_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
                  status='running', checks={}, failures=[],
                  scope='User-authorized agent inventory review, not a human member-C signature.',
                  limitations=['No policy runs or performance claims in this audit.',
                               'Provenance, split and legacy teacher boundary review belongs to delegated A.',
                               'Formal result signoff and release remain subsequent gates.'])
    log = []

    def check(name, condition, value=True):
        report['checks'][name] = value
        if not condition:
            report['failures'].append(name)
            raise AssertionError(name)
        log.append(f'PASS {name}: {json.dumps(value, ensure_ascii=False, sort_keys=True)}')

    try:
        os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(args.frozen.resolve()))
        from backend.cli import RunConfig
        from backend.formal_v2 import verify, MODEL, ANALYSIS
        from backend.formal_freeze import freeze_binding

        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=args.frozen,
                              text=True, capture_output=True, check=True).stdout.strip()
        check('frozen_revision', head == revision, head)
        check('frozen_import_origin', Path(sys.modules['backend.formal_v2'].__file__).resolve().is_relative_to(args.frozen.resolve()))
        manifest = read(candidate/'manifest.json')
        manifest_sha = digest((candidate/'manifest.json').read_bytes())
        check('candidate_manifest_sha256', manifest_sha == '2b0814db44b7c70cd94e44608e34c762ffaa86969ea6f955e4736b7b3cdcd31f', manifest_sha)
        rows = manifest['trajectories']
        check('trajectory_count', len(rows) == 180, len(rows))
        cells = Counter(row['cell_id'] for row in rows)
        check('cell_counts', cells == {f'cell_{i:02d}': 10 for i in range(18)}, dict(cells))
        seeds = {row['seed'] for row in rows}
        check('seed_inventory', seeds == set(range(600000, 600180)), dict(count=len(seeds), minimum=min(seeds), maximum=max(seeds)))
        uniques = {key: len({row[key] for row in rows}) for key in
                   ('trajectory_id', 'config_path', 'config_sha256', 'input_hash', 'content_hash', 'seed')}
        check('unique_identity_counts', all(n == 180 for n in uniques.values()), uniques)
        inventory = {p.relative_to(candidate).as_posix() for p in candidate.rglob('*') if p.is_file()}
        check('exact_candidate_file_inventory', inventory == {row['config_path'] for row in rows} | {'manifest.json', 'protocol.json'}, len(inventory))

        actual_configs = []
        for row in rows:
            path = candidate/row['config_path']
            if not path.resolve().is_relative_to(candidate.resolve()):
                raise ValueError('Candidate config escapes packet')
            raw = path.read_bytes()
            config = json.loads(raw)
            normalized = RunConfig.model_validate(config).model_dump()
            if normalized != config or digest(raw) != row['config_sha256'] or digest(canonical(config)) != row['config_sha256']:
                raise ValueError('Config bytes/schema mismatch: '+row['config_path'])
            scene = config['scenario']
            content = copy.deepcopy(scene)
            content.pop('scenario_id')
            content['channel'].pop('seed')
            if digest(canonical(scene)) != row['input_hash'] or digest(canonical(content)) != row['content_hash']:
                raise ValueError('Input/content hash mismatch: '+row['config_path'])
            if config['seed'] != row['seed'] or scene['channel']['seed'] != row['seed'] or scene['scenario_id'] != row['trajectory_id']:
                raise ValueError('Identity mismatch: '+row['config_path'])
            if config['actions'] != [] or config['policy_runtime'] is not None or config['kind'] != 'rule_validation':
                raise ValueError('Policy contamination: '+row['config_path'])
            actual_configs.append(dict(trajectory_id=row['trajectory_id'], config_path=row['config_path'],
                                       config_sha256=digest(raw), input_hash=digest(canonical(scene)),
                                       content_hash=digest(canonical(content)), seed=config['seed']))
        check('actual_config_files_opened_validated_and_hashed', len(actual_configs) == 180, len(actual_configs))
        report['actual_configs'] = actual_configs

        policies = read(candidate/'protocol.json')['policy_ids']
        runkeys = [(row['cell_id'], row['trajectory_id'], policy) for row in rows for policy in policies]
        check('shared_input_policy_runkeys', policies == ['edf', 'value', 'learned'] and len(runkeys) == len(set(runkeys)) == 540,
              dict(policies=policies, unique_runkeys=len(set(runkeys)), shared_config_and_input_groups=180))
        check('frozen_generator_verify', verify(candidate/'manifest.json') == manifest)
        binding = read(review/'binding.json')
        check('binding_sha256', digest((review/'binding.json').read_bytes()) == 'd2b596d852758c9514f2aa7b735f4cd1f31dbfbee0c23af50619fd51ecad5e2a', digest((review/'binding.json').read_bytes()))
        check('fresh_frozen_binding', freeze_binding(candidate/'manifest.json', MODEL, ANALYSIS) == binding,
              dict(source_file_count=len(binding['source_sha256']), model_artifact_count=len(binding['model_artifacts_sha256'])))
        check('original_and_final_binding_equal', read(packet/'review/binding.json') == binding)

        sha_index = read(packet/'SHA256SUMS.json')
        bad = [name for name, expected in sha_index.items() if digest((packet/name).read_bytes()) != expected]
        check('candidate_sha_index_actual_current_entries', len(sha_index) >= 204 and not bad, dict(entries=len(sha_index), errors=bad))
        final_index = read(final/'SHA256SUMS.json')
        # A/B/C receipts may be actively authored by other delegated agents. Check only immutable subjects here.
        stable = {name: expected for name, expected in final_index.items()
                  if name not in ('proposed_review/A.json', 'proposed_review/B.json', 'proposed_review/C.json', 'status.json')}
        bad = [name for name, expected in stable.items() if digest((final/name).read_bytes()) != expected]
        check('finalization_immutable_sha_index', not bad, dict(entries=len(stable), errors=bad))

        leakage_bytes = (review/'leakage.json').read_bytes()
        leakage = json.loads(leakage_bytes)
        check('final_leakage_exact_sha256', digest(leakage_bytes) == leakage_sha, dict(sha256=digest(leakage_bytes), bytes=len(leakage_bytes)))
        proposal = read(final/'C_leakage_proposal.json')
        base_bytes = (packet/'review/leakage.json').read_bytes()
        base = json.loads(base_bytes)
        check('proposal_base_binding', proposal['candidate_manifest_sha256'] == manifest_sha and proposal['binding_sha256'] == digest((review/'binding.json').read_bytes()) and proposal['base_leakage']['sha256'] == digest(base_bytes) and proposal['base_leakage']['bytes'] == len(base_bytes))
        transformed = copy.deepcopy(base)
        transformed['status'] = 'accepted'
        check('C_proposal_exact_byte_transformation', base['status'] == 'pending' and canonical(transformed) == leakage_bytes and proposal['proposed_final_leakage']['sha256'] == leakage_sha and proposal['proposed_final_leakage']['bytes'] == len(leakage_bytes))
        check('leakage_subject_matches_binding', leakage['candidate_manifest_sha256'] == manifest_sha and leakage['model_artifacts_sha256'] == binding['model_artifacts_sha256'])
        source_results = []
        for name, expected in leakage['source_files'].items():
            frozen_path = args.frozen/name.removeprefix('sources/')
            copies = [(packet/'review'/name).read_bytes(), (review/name).read_bytes(), frozen_path.read_bytes()]
            if not all(digest(blob) == expected for blob in copies):
                raise ValueError('Source copy mismatch: '+name)
            source_results.append(dict(path=name, sha256=expected, bytes=len(copies[0])))
        check('seven_source_files_original_final_and_frozen', len(source_results) == 7, source_results)
        check('excluded_seed_and_content_zero_overlap', not seeds.intersection(leakage['excluded_seeds']) and not {row['content_hash'] for row in rows}.intersection(leakage['excluded_content_hashes']),
              dict(excluded_seed_count=len(set(leakage['excluded_seeds'])), excluded_content_count=len(set(leakage['excluded_content_hashes'])), seed_overlap=0, content_overlap=0))
        authorization = read(out/'authorization.json')
        check('user_authorization_bound_to_subject', authorization['candidate_manifest_sha256'] == manifest_sha and authorization['leakage_sha256'] == leakage_sha and authorization['generation_commit'] == revision and authorization['user_instruction'] == '能不能替ac进行检查，直接推进下一步')
        check('C_receipt_template_subject', read(review/'C.json')['role'] == 'C' and read(review/'C.json')['binding'] == binding)

        report['status'] = 'passed'
        if args.sign:
            receipt = dict(schema_version='formal-freeze-receipt-v1', role='C', data_scope='formal',
                           status='accepted_with_notes', reviewer=report['reviewer'], reviewed_at=report['reviewed_at'],
                           binding=binding, leakage_sha256=leakage_sha,
                           notes='User authorized delegated A/C checks and next-step progression. This separate-context Codex agent independently opened and validated all 180 actual configs, recomputed file/input/content hashes, identities and seeds, confirmed 18x10 balance and 540 shared-input run keys, checked the current 204+ entry SHA index, all seven original/final/frozen source copies, fresh frozen-code binding and exact C-proposed leakage byte transformation. Accepted only for the inventory/hash scope. This is an actual machine review by codex-delegated-C-inventory-review, not a signature by human member-C. Provenance/split/legacy-boundary approval is delegated A scope. Formal result signoff and claim release remain separate subsequent gates.',
                           delegation=dict(kind='user_authorized_agent_substitution',
                                           authorization_path='docs/evidence/B/delegated_execution_2026-11-10/authorization.json',
                                           authorization_sha256=digest((out/'authorization.json').read_bytes()),
                                           user_instruction=authorization['user_instruction'],
                                           agent_role='independent_C_inventory_reviewer',
                                           human_member_C_signature=False,
                                           audit_path='docs/evidence/B/delegated_execution_2026-11-10/C_audit.json'))
            (review/'C.json').write_bytes(canonical(receipt))
            signed = read(review/'C.json')
            check('authored_C_receipt_readback', signed == receipt and signed['reviewer'] != 'member-C')
            report['authored_receipt_sha256'] = digest((review/'C.json').read_bytes())
        else:
            report['receipt_authored_this_run'] = False
    except Exception as error:
        report['status'] = 'failed'
        report['exception'] = f'{type(error).__name__}: {error}'
        log.append('FAIL '+report['exception'])
    report['audit_script_sha256'] = digest(Path(__file__).read_bytes())
    (out/'C_audit.json').write_bytes(canonical(report))
    (out/'C_audit.log').write_text('\n'.join(log)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(status=report['status'], checks=len(report['checks']),
                          failures=report['failures'], exception=report.get('exception'),
                          receipt_sha256=report.get('authored_receipt_sha256')), ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
