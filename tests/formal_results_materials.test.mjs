import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '..');
const generator = path.join(root, 'scripts', 'generate_formal_results_materials.mjs');

function summary(signoff = 'accepted') {
  const cells = Array.from({ length: 18 }, (_, index) => ({
    cell_id: `L${Math.floor(index / 6) + 1}-E${Math.floor((index % 6) / 2) + 1}-D${index % 2 + 1}`,
    n: 10,
    missing: 0,
    mean_delta: (index - 8.5) / 100,
    ci95: [(index - 10.5) / 100, (index - 6.5) / 100],
  }));
  const comparison = (verdict) => ({
    cells,
    paired_count: 180,
    overall: { mean_delta: verdict === '胜' ? 0.04 : -0.01, ci95: verdict === '胜' ? [0.01, 0.07] : [-0.04, 0.02], aggregation: 'equal_cell_weight' },
    statistical_verdict: verdict,
    formal_verdict: signoff === 'accepted' ? verdict : '未完成',
  });
  return {
    schema_version: 'formal-analysis-summary-v1', expected_policy_runs: 540,
    completed_policy_runs: 540, missing_policy_runs: 0, failed_policy_runs: 0, failed_attempts: 2,
    result_signoff: signoff, data_scope: 'formal_v2', domain: 'lossy_random_link',
    multiplicity: 'two_primary_comparisons', policy_ids: ['edf', 'value', 'learned'],
    comparisons: { 'learned-edf': comparison('胜'), 'learned-value': comparison('未检出稳定差异') },
    provenance: { frozen_manifest_sha256: 'a'.repeat(64), run_index_sha256: 'b'.repeat(64), binding: { code_sha256: 'c'.repeat(64) } },
    inference: { requests: 20, fallback_count: 1, fallback_rate: 0.05, cold_load_ms: [2.1], decision_latency_count: 20,
      decision_latency_median_ms: 1.2, decision_latency_p95_ms: 2.4, scope: 'local_CPU_end_to_end_decision_not_pure_model_forward' },
  };
}

async function tempCase(signoff = 'accepted') {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), 'formal-materials-'));
  const input = path.join(folder, 'summary.json');
  const output = path.join(folder, 'out');
  const payload = `${JSON.stringify(summary(signoff), null, 2)}\n`;
  await fs.writeFile(input, payload, 'utf8');
  return { folder, input, output, payload };
}

test('signed formal summary generates two report-grade SVG masters and a traceable manifest', async () => {
  const item = await tempCase();
  try {
    const result = spawnSync(process.execPath, [generator, '--input', item.input, '--output', item.output], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    const files = await fs.readdir(item.output);
    assert.ok(files.includes('B-F07_正式策略比较总览.svg'));
    assert.ok(files.includes('B-F08_十八工况配对差值矩阵.svg'));
    assert.ok(files.includes('CAPTIONS.md'));
    const overview = await fs.readFile(path.join(item.output, 'B-F07_正式策略比较总览.svg'), 'utf8');
    assert.match(overview, /width="170mm"/);
    assert.match(overview, /fill="#FFFFFF"/);
    assert.match(overview, /Learned − EDF/);
    assert.match(overview, /未检出稳定差异/);
    assert.doesNotMatch(overview, />等效</);
    const matrix = await fs.readFile(path.join(item.output, 'B-F08_十八工况配对差值矩阵.svg'), 'utf8');
    for (let index = 1; index <= 18; index += 1) assert.match(matrix, new RegExp(`L${Math.floor((index - 1) / 6) + 1}-E`));
    const manifest = JSON.parse(await fs.readFile(path.join(item.output, 'manifest.json'), 'utf8'));
    assert.equal(manifest.source_sha256, crypto.createHash('sha256').update(item.payload).digest('hex'));
    assert.equal(manifest.result_signoff, 'accepted');
    assert.equal(manifest.figures.length, 2);
  } finally { await fs.rm(item.folder, { recursive: true, force: true }); }
});

test('pending or unsigned formal summary is rejected without creating material figures', async () => {
  const item = await tempCase('pending');
  try {
    const result = spawnSync(process.execPath, [generator, '--input', item.input, '--output', item.output], { encoding: 'utf8' });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /三方结果签核/);
    await assert.rejects(fs.access(item.output));
  } finally { await fs.rm(item.folder, { recursive: true, force: true }); }
});

test('generator refuses to overwrite an existing output directory', async () => {
  const item = await tempCase();
  try {
    await fs.mkdir(item.output);
    const result = spawnSync(process.execPath, [generator, '--input', item.input, '--output', item.output], { encoding: 'utf8' });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /输出目录必须不存在/);
  } finally { await fs.rm(item.folder, { recursive: true, force: true }); }
});
