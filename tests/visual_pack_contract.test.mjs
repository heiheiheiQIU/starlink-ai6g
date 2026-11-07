import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '..');
const figures = path.join(root, 'docs', 'figures', 'generated', 'v1');

const readFigure = (name) => fs.readFileSync(path.join(figures, name), 'utf8');
const allowedStatuses = new Set([
  'draft',
  'review_pending',
  'accepted_with_notes',
  'accepted',
  'superseded',
]);

test('A-F01 only claims the frozen scorer output that exists in the contract', () => {
  const svg = readFigure('A-F01_公开特征教师标注学习评分器.svg');

  assert.doesNotMatch(svg, /置信边界/);
  assert.match(svg, /候选分数/);
  assert.match(svg, /B线模块/);
});

test('A-F02 uses bars and points without a percentage ring', () => {
  const svg = readFigure('A-F02_教师标签质量审计.svg');

  assert.doesNotMatch(svg, />65%</);
  assert.doesNotMatch(svg, /stroke-dasharray="327 503"/);
  assert.match(svg, />13\/20</);
  assert.match(svg, />19\/20</);
  assert.match(svg, />1\/20</);
});

test('A line figures do not use decorative drop shadows', () => {
  for (const name of [
    'A-F01_公开特征教师标注学习评分器.svg',
    'A-F02_教师标签质量审计.svg',
    'A-F03_小样本模型对照.svg',
    'A-F05_公开信息与真值隔离.svg',
  ]) {
    assert.doesNotMatch(readFigure(name), /filter="url\(#shadow\)"/, name);
  }
});

test('each A line figure has a truthful review-pending manifest', () => {
  for (const figureId of ['A-F01', 'A-F02', 'A-F03', 'A-F05']) {
    const manifestPath = path.join(figures, `${figureId}_manifest.json`);
    assert.ok(fs.existsSync(manifestPath), `${figureId} manifest is missing`);

    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    assert.equal(manifest.figure_id, figureId);
    assert.equal(manifest.owner, 'A');
    assert.equal(manifest.status, 'review_pending');
    assert.ok(allowedStatuses.has(manifest.status));
    assert.deepEqual(manifest.reviewers, ['B', 'C']);
    assert.ok(manifest.source_files.length > 0);
    assert.ok(manifest.limitations.length > 0);
    assert.ok(manifest.outputs.length > 0);

    for (const output of manifest.outputs) {
      assert.ok(fs.existsSync(path.join(root, output)), `${output} does not exist`);
    }
  }
});
