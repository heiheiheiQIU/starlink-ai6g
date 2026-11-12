"""Real subprocess/ZIP mutation tests; no imported or mocked auditor."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

AUDIT = Path(__file__).with_name('A_formal_results_audit.py')
SOURCE = 'a4890579f1d4a2cfb5be9246db6ca46a306fcd39'
PACKAGE = Path(os.environ.get('A_RESULT_ZIP', str(Path(tempfile.gettempdir()) /
    'starlink-a-formal-results-review/docs/evidence/B/delegated_execution_2026-11-10/formal_v2_delegated_results_20261110.zip')))
EVENTS = 'batch/runs/formal_v2_cell_00_trace_00/learned/attempt_1/events.jsonl'


class AuditCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(PACKAGE) as z:
            cls.members = {n: z.read(n) for n in z.namelist()}

    def cli(self, package, source=SOURCE, output=None):
        args = [sys.executable, str(AUDIT), '--result-zip', str(package), '--source-commit', source]
        if output:
            args += ['--output', str(output)]
        return subprocess.run(args, capture_output=True)

    def test_positive_real_cli_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            outputs = [Path(d)/n for n in ('one.json', 'two.json')]
            for out in outputs:
                result = self.cli(PACKAGE, output=out)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())
            data = json.loads(outputs[0].read_bytes())
            self.assertEqual(data['machine_audit']['status'], 'passed')
            self.assertEqual(data['A_ruling'], 'pending')
            self.assertIs(data['release_approved'], False)
            self.assertEqual(data['learned']['decisions'], 2160)
            self.assertEqual(data['learned']['score_margin']['count'], 2009)
            self.assertEqual(data['learned']['score_margin']['idle_only_decisions'], 151)
            for policy, expected in [('edf', .4653873291265777), ('value', .5114726389809670), ('learned', 0)]:
                self.assertAlmostEqual(data['policy_weighted_on_time_rate'][policy], expected, places=14)
            for name, mean, interval in [
                ('learned-edf', -.4653873291265777, [-.49422782912931634, -.43592598002654237]),
                ('learned-value', -.5114726389809671, [-.5385503136194323, -.4831265616824757]),
            ]:
                comparison = data['comparisons'][name]
                self.assertAlmostEqual(comparison['overall']['mean_delta'], mean, places=14)
                for a, b in zip(comparison['overall']['ci95'], interval):
                    self.assertAlmostEqual(a, b, places=14)
                self.assertEqual(comparison['formal_verdict'], '未完成')
                self.assertEqual(comparison['statistical_verdict'], '负')

    def test_wrong_source(self):
        result = self.cli(PACKAGE, '0'*40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'source_commit', result.stderr)

    def reject(self, name, payload, expected):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)/'mutated.zip'
            with zipfile.ZipFile(target, 'w', zipfile.ZIP_STORED) as z:
                for n, data in self.members.items():
                    z.writestr(n, payload if n == name else data)
            result = self.cli(target)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(expected.encode(), result.stderr, result.stderr.decode())

    def test_binding_mutations(self):
        for name, key, value, error in [
            ('frozen/manifest.json', 'binding', {'code_revision': 'wrong'}, 'frozen.code'),
            ('frozen/model/manifest.json', 'model_version', 'wrong', 'model.version'),
            ('analysis/summary.json', 'provenance', {}, 'summary.binding'),
            ('analysis/summary.json', 'domain', 'real_satellite', 'applicability'),
            ('analysis/summary.json', 'completed_policy_runs', 539, 'summary.counts'),
            ('analysis/summary.json', 'result_signoff', 'approved', 'signoff'),
        ]:
            with self.subTest(name=name, key=key):
                data = json.loads(self.members[name]); data[key] = value
                self.reject(name, json.dumps(data).encode(), error)

    def test_run_mutations(self):
        rows = [json.loads(l) for l in self.members['batch/run_index.jsonl'].splitlines()]
        variants = {'missing': rows[:-1], 'duplicate': rows + [rows[-1]],
                    'retry': [dict(r, attempt=2) if i == 0 else r for i, r in enumerate(rows)],
                    'not_completed': [dict(r, status='failed') if i == 1 else r for i, r in enumerate(rows)]}
        for name, data in variants.items():
            with self.subTest(name=name):
                self.reject('batch/run_index.jsonl', '\n'.join(json.dumps(r) for r in data).encode(), 'runs.')

    def test_decision_mutations(self):
        for kind in ['send', 'fallback_true', 'fallback_string', 'fallback_missing',
                     'action_fallback', 'missing', 'duplicate', 'score', 'nan', 'idle_duplicate']:
            with self.subTest(kind=kind):
                rows = [json.loads(l) for l in self.members[EVENTS].splitlines()]
                i = next(i for i, e in enumerate(rows) if e['event_type'] == 'decision')
                data = rows[i]['data']
                if kind == 'send': data['action']['mode'] = 'fast'
                elif kind == 'fallback_true': data['fallback'] = True
                elif kind == 'fallback_string': data['fallback'] = 'false'
                elif kind == 'fallback_missing': del data['fallback']
                elif kind == 'action_fallback': data['action']['fallback'] = True
                elif kind == 'missing': del rows[i]
                elif kind == 'duplicate': rows.insert(i, rows[i])
                elif kind == 'score': data['candidate_scores'][0]['score'] = 2.0
                elif kind == 'nan': data['candidate_scores'][0]['score'] = float('nan')
                elif kind == 'idle_duplicate': data['candidate_scores'].append(data['candidate_scores'][-1])
                self.reject(EVENTS, '\n'.join(json.dumps(r) for r in rows).encode(), 'learned.')

    def test_summary_comparison_and_decision_counts(self):
        for kind in ['comparison', 'decisions']:
            with self.subTest(kind=kind):
                data = json.loads(self.members['analysis/summary.json'])
                if kind == 'comparison': data['comparisons']['learned-edf']['overall']['mean_delta'] = 0
                else: data['inference']['decision_latency_count'] = 2159
                self.reject('analysis/summary.json', json.dumps(data).encode(), 'summary.')

    def test_metric_and_paired_table_mutations(self):
        self.reject('export/metrics_by_run.csv', self.members['export/metrics_by_run.csv'].replace(b',1.0,12,', b',0.5,12,', 1), 'metrics.')
        self.reject('analysis/paired_deltas.csv', self.members['analysis/paired_deltas.csv'].replace(b',-1.0', b',0.0', 1), 'paired.')

    def test_zip_sha_and_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'bad.zip'
            p.write_bytes(PACKAGE.read_bytes()+b'changed')
            r = self.cli(p); self.assertNotEqual(r.returncode, 0); self.assertIn(b'zip.sha256', r.stderr)
            p.write_bytes(b'not a zip')
            r = self.cli(p); self.assertNotEqual(r.returncode, 0); self.assertIn(b'zip.', r.stderr)
        self.reject('execute_formal_stage.py', b'corrupt member', 'zip.sha256')

    def test_corrupt_member_crc(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'bad-crc.zip'
            with zipfile.ZipFile(p, 'w', zipfile.ZIP_STORED) as z:
                z.writestr('bad.txt', b'original bytes')
            raw = p.read_bytes().replace(b'original bytes', b'corrupt! bytes')
            p.write_bytes(raw)
            result = self.cli(p)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'zip.corrupt member', result.stderr)


if __name__ == '__main__':
    unittest.main()
