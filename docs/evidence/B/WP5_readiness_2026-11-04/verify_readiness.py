"""Read-only readiness evidence; does not freeze inputs or validate a new model."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
C_REF = 'b1d5e8b'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--attachment', type=Path, required=True)
    args = parser.parse_args()
    import sys
    sys.path.insert(0, str(ROOT))
    from training.audit_policy_dataset import audit_rows

    def git(*argv):
        return subprocess.check_output(['git', *argv], cwd=ROOT)

    suite = ET.parse(args.runs/'backend.xml').getroot().find('testsuite')
    assert suite is not None
    assert suite.attrib['failures'] == suite.attrib['errors'] == '0'
    frontend = (args.runs/'frontend.log').read_text(encoding='utf-8-sig')
    assert '70 passed' in frontend and '19 passed' in frontend and 'built in' in frontend
    http = json.loads((args.runs/'http/verification.json').read_text())
    assert http['paired_inputs'] and http['all_artifact_hashes_verified']
    assert http['owned_servers_stopped']
    runtime = http['runs'][0]['code_revision']
    assert {r['code_revision'] for r in http['runs']} == {runtime}
    assert not git('diff', '--name-only', runtime, 'HEAD', '--', 'backend', 'tests', 'configs', 'frontend', 'training')

    prior = json.loads((ROOT/'docs/evidence/B/WP2_learned_2026-11-04/verification.json').read_text())
    frozen = {}
    for path, expected in prior['frozen_sha256'].items():
        digest = sha((ROOT/path).read_bytes())
        assert digest == expected, path
        frozen[path] = digest
    old_data = git('ls-tree', '-r', '--name-only', '6051d34', 'data/teacher/a_n3_20_v2').decode().splitlines()
    for path in old_data:
        assert git('show', f'6051d34:{path}') == git('show', f'HEAD:{path}'), path
    c_sources = git('ls-tree', '-r', '--name-only', C_REF, '--',
                    'frontend/src', 'scripts', 'docs/materials', 'docs/report').decode().splitlines()
    for path in c_sources:
        assert git('show', f'{C_REF}:{path}') == git('show', f'HEAD:{path}'), path

    rows = [json.loads(line) for line in (ROOT/'data/teacher/a_n3_20_v2/samples.jsonl').read_text().splitlines()]
    audit = audit_rows(rows, reserve_wh=.5)
    fixture = json.loads((ROOT/'frontend/src/fixtures/teacher_audit.json').read_text())
    actual = {r['sample_id']: r for r in rows}
    mismatches = []
    for item in fixture['samples']:
        row = actual[item['sample_id']]
        obs = row['observation']
        task = [c for c in row['candidate_scores'] if c['mode'] != 'idle']
        feasible = [c for c in row['candidate_scores'] if c['feasible']]
        optimal = [c for c in feasible if c['score'] == max(x['score'] for x in feasible)]
        kind = ('unique-nonidle' if len(optimal) == 1 and optimal[0]['mode'] != 'idle'
                else 'all-zero' if task and all(c['score'] == 0 for c in task)
                else 'idle-tied' if any(c['mode'] == 'idle' for c in optimal) else 'other')
        expected = dict(kind=kind, energy_lower_Wh=obs['health']['energy_lower_Wh'], windows=len(obs['forecast_windows']))
        if any(item[k] != v for k, v in expected.items()):
            mismatches.append(dict(sample_id=item['sample_id'], expected=expected, displayed=item))

    attachment = args.attachment.read_bytes()
    tracked = (ROOT/'docs/handoffs/A_N4b_data_battle_plan_2026-11-04.md').read_bytes()
    normalize = lambda raw: raw.decode('utf-8-sig').replace('\r\n', '\n')
    assert normalize(attachment) == normalize(tracked)
    record = dict(kind='WP5_preparation_not_frozen_experiment', runtime_commit=runtime,
                  refs={ref:git('rev-parse', ref).decode().strip() for ref in [
                      'origin/main','origin/feature/frontend','origin/codex/a-n4-data-audit','origin/codex/b-wp2-learned-20261104']},
                  tests=suite.attrib, frontend_tests=70, frontend_build=True, browser_verified=False,
                  http=http, frozen_sha256=frozen, old_data_file_count=len(old_data),
                  c_source_files_unchanged=len(c_sources), old_data_audit=audit,
                  teacher_card_row_mismatches=mismatches,
                  attachment=dict(filename=args.attachment.name,sha256=sha(attachment),normalized_matches_repository=True),
                  formal_runs_executed=0, new_model_received=False,
                  raw_evidence_sha256={name:sha((args.runs/name).read_bytes()) for name in [
                      'backend.xml','backend.log','frontend.log','http/verification.json','http.log']})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps(dict(tests=suite.attrib['tests'],skipped=suite.attrib['skipped'],frontend_tests=70,
                         frozen_paths=len(frozen),c_sources=len(c_sources),card_mismatches=len(mismatches)),ensure_ascii=False))


if __name__ == '__main__':
    main()
