"""Independent audit acceptance and fail-closed mutation tests (stdlib only)."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('A_recovery_dev_audit.py')
SNAPSHOT = Path(os.environ.get('A_RECOVERY_SNAPSHOT', Path(tempfile.gettempdir()) / 'starlink-a-recovery-audit'))
PILOT = Path('docs/evidence/B/recovery_dev_2026-11-10/pilot')
COMMIT = 'a2e0be4b579b5d4cb797bdc826c077e551d985f6'


class AuditTests(unittest.TestCase):
    def run_audit(self, pilot, root=SNAPSHOT):
        result = subprocess.run([sys.executable, str(SCRIPT), '--pilot-dir', str(pilot),
                                 '--repo-root', str(root), '--source-commit', COMMIT],
                                capture_output=True, text=True)
        return result

    def test_snapshot_passes_deterministically_with_explicit_gaps(self):
        first = self.run_audit(SNAPSHOT / PILOT)
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        second = self.run_audit(SNAPSHOT / PILOT)
        self.assertEqual(first.stdout, second.stdout)
        result = json.loads(first.stdout)
        self.assertEqual(result['source_count'], 30)
        self.assertEqual(result['state_count'], 60)
        self.assertEqual(result['source_split_counts'], dict(train=18, validation=6, test=6))
        self.assertEqual(result['decision_counts'], dict(tied=8, send_strictly_better=30,
                                                       no_feasible_send=22, wait_strictly_better=0))
        self.assertEqual(result['coverage_counts'], dict(non_zero_loss=0, in_flight=0, long_horizon=0))
        self.assertFalse(result['training_approved'])
        self.assertTrue(result['gaps'])

    def test_corruption_is_rejected_even_when_output_hash_is_resealed(self):
        cases = [
            ('raw_hash', 'samples.jsonl', None),
            ('source_identity', 'sources.jsonl', lambda rows: rows[0].update(source_id='wrong')),
            ('source_hash', 'sources.jsonl', lambda rows: rows[0]['scenario'].update(initial_energy_Wh=99)),
            ('seed_duplicate', 'sources.jsonl', lambda rows: rows[1].update(seed=rows[0]['seed'])),
            ('split', 'attempts.jsonl', lambda rows: rows[0].update(split='test')),
            ('state_identity', 'attempts.jsonl', lambda rows: rows[0].update(state_id='wrong')),
            ('observation', 'attempts.jsonl', lambda rows: rows[0]['observation'].update(cache_bytes=0)),
            ('label_hash', 'attempts.jsonl', lambda rows: rows[0].update(label_content_sha256='0'*64)),
            ('solver', 'attempts.jsonl', lambda rows: rows[0].update(solver_status='TIME_LIMIT')),
            ('teacher', 'attempts.jsonl', lambda rows: rows[0].update(teacher_config_sha256='0'*64)),
            ('duplicate_semantics', 'attempts.jsonl', lambda rows: rows[1].update(observation=copy.deepcopy(rows[0]['observation']))),
        ]
        for name, filename, mutate in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                pilot = Path(directory) / 'pilot'
                shutil.copytree(SNAPSHOT / PILOT, pilot)
                path = pilot / filename
                if mutate is None:
                    path.write_bytes(path.read_bytes() + b' ')
                else:
                    rows = [json.loads(line) for line in path.read_text().splitlines()]
                    mutate(rows)
                    path.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
                    manifest = json.loads((pilot / 'manifest.json').read_text())
                    manifest['output_sha256'][filename] = hashlib.sha256(path.read_bytes()).hexdigest()
                    (pilot / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
                result = self.run_audit(pilot)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report['status'], 'failed')
                self.assertFalse(report['training_approved'])

    def test_exclusion_evidence_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = json.loads((SNAPSHOT / PILOT / 'manifest.json').read_text(encoding='utf-8'))
            leakage = json.loads((SNAPSHOT / PILOT / 'leakage.json').read_text(encoding='utf-8'))
            for name in list(manifest['code_sha256']) + ['configs/teacher.json'] + list(leakage['exclusion_evidence']):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(SNAPSHOT / name, target)
            path = root / 'docs/evidence/B/formal_v2_candidate_2026-11-09/candidate/manifest.json'
            path.write_text('{}')
            result = self.run_audit(SNAPSHOT / PILOT, root)
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertIn('SHA256 mismatch: docs/evidence/B/formal_v2_candidate', report['error'])
            self.assertFalse(report['training_approved'])

    def test_resealed_solver_and_teacher_tampering_reaches_the_named_check(self):
        for field, value, message in [('solver_status', 'TIME_LIMIT', 'Solver status'),
                                       ('teacher_config_sha256', '0'*64, 'Teacher binding'),
                                       ('decision_class', 'wait_strictly_better', 'Decision class')]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                pilot = Path(directory) / 'pilot'
                shutil.copytree(SNAPSHOT / PILOT, pilot)
                path = pilot / 'attempts.jsonl'
                rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
                rows[0][field] = value
                payload = {k: v for k, v in rows[0].items() if k not in ('elapsed_ms', 'label_content_sha256')}
                rows[0]['label_content_sha256'] = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()
                path.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
                manifest = json.loads((pilot / 'manifest.json').read_text(encoding='utf-8'))
                manifest['output_sha256']['attempts.jsonl'] = hashlib.sha256(path.read_bytes()).hexdigest()
                (pilot / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
                result = self.run_audit(pilot)
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, json.loads(result.stdout)['error'])

    def test_malformed_evidence_still_returns_failed_json(self):
        with tempfile.TemporaryDirectory() as directory:
            pilot = Path(directory)
            (pilot / 'manifest.json').write_text('[]', encoding='utf-8')
            result = self.run_audit(pilot)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)['status'], 'failed')

    def test_invalid_declared_sha256_fails_at_format_gate(self):
        declarations = ('output', 'code', 'teacher', 'exclusion')
        invalid_values = (None, 0, False, [], {}, 'a'*63, 'a'*65, 'g'*64)
        for declaration in declarations:
            for invalid in invalid_values:
                with self.subTest(declaration=declaration, invalid=invalid), tempfile.TemporaryDirectory() as directory:
                    pilot = Path(directory) / 'pilot'
                    shutil.copytree(SNAPSHOT / PILOT, pilot)
                    manifest = json.loads((pilot / 'manifest.json').read_text(encoding='utf-8'))
                    if declaration == 'output':
                        manifest['output_sha256']['samples.jsonl'] = invalid
                    elif declaration == 'code':
                        manifest['code_sha256']['training/recovery_pilot.py'] = invalid
                    elif declaration == 'teacher':
                        manifest['teacher_config_sha256'] = invalid
                    else:
                        path = pilot / 'leakage.json'
                        leakage = json.loads(path.read_text(encoding='utf-8'))
                        leakage['exclusion_evidence']['data/teacher/a_n3_20/samples.jsonl'] = invalid
                        path.write_text(json.dumps(leakage), encoding='utf-8')
                        manifest['output_sha256']['leakage.json'] = hashlib.sha256(path.read_bytes()).hexdigest()
                    (pilot / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
                    result = self.run_audit(pilot)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    report = json.loads(result.stdout)
                    self.assertEqual(report['status'], 'failed')
                    self.assertFalse(report['training_approved'])
                    self.assertIn('Invalid SHA256 declaration:', report['error'])

    def test_valid_uppercase_sha256_declarations_are_still_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            pilot = Path(directory) / 'pilot'
            shutil.copytree(SNAPSHOT / PILOT, pilot)
            manifest = json.loads((pilot / 'manifest.json').read_text(encoding='utf-8'))
            for mapping in ('output_sha256', 'code_sha256'):
                manifest[mapping] = {name: sha.upper() for name, sha in manifest[mapping].items()}
            manifest['teacher_config_sha256'] = manifest['teacher_config_sha256'].upper()
            path = pilot / 'leakage.json'
            leakage = json.loads(path.read_text(encoding='utf-8'))
            leakage['exclusion_evidence'] = {name: sha.upper() for name, sha in leakage['exclusion_evidence'].items()}
            path.write_text(json.dumps(leakage), encoding='utf-8')
            manifest['output_sha256']['leakage.json'] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
            (pilot / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            result = self.run_audit(pilot)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'passed')


if __name__ == '__main__':
    unittest.main()
