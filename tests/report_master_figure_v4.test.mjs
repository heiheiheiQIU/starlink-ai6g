import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import test from 'node:test';

const root = new URL('../', import.meta.url);
const dataUrl = new URL('../docs/figures/source_data/v4_master_figure.json', import.meta.url);
const svgUrl = new URL('../docs/figures/generated/v4/report/C-F00_AI6G闭环证据主图.svg', import.meta.url);

test('source contract freezes signed teacher, event, energy and result evidence', async () => {
  const data = JSON.parse(await fs.readFile(dataUrl, 'utf8'));
  assert.equal(data.provenance.teacher.blob, '13647fb7a71d104022d7c029e883ffa3c538716a');
  assert.deepEqual(data.teacher.candidates.map((x) => [x.key, x.score, x.feasible]), [
    ['T1/robust', 0, false], ['T1/fast', 1, true], ['T2/robust', 0.5, true],
    ['T2/fast', 0.5, true], ['idle', 0.5, true],
  ]);
  assert.deepEqual(data.ack_loss.events.map((x) => x.time_s), [0, 1.03125, 2.03125, 3.03125, 4, 5.03125, 6.03125]);
  assert.equal(data.ack_loss.energy.at(-1).energy_after_Wh, 9.898888888888894);
  assert.equal(data.ack_loss.results.joule_per_success_bit, 0.04443359375);
  assert.equal(data.ack_loss.results.weighted_on_time_rate, 1);
});

test('master figure is a four-panel white-background scientific plate with honest scope', async () => {
  const svg = await fs.readFile(svgUrl, 'utf8');
  assert.match(svg, /width="170mm"/);
  assert.match(svg, /fill="#FFFFFF"/);
  for (const mark of ['\(a\)', '\(b\)', '\(c\)', '\(d\)']) assert.match(svg, new RegExp(mark));
  for (const value of ['1.03125', '2.03125', '3.03125', '5.03125', '6.03125', '0.0444336']) assert.match(svg, new RegExp(value));
  assert.match(svg, /工程签核样例/);
  assert.match(svg, /非正式策略对比结果/);
  assert.doesNotMatch(svg, /优于基线|显著提升|正式实验结果/);
  assert.doesNotMatch(svg, /<filter|drop-shadow|linearGradient/);
});

test('master figure keeps the report caption outside the SVG', async () => {
  const svg = await fs.readFile(svgUrl, 'utf8');
  assert.doesNotMatch(svg, /图\s*[0-9一二三四五六七八九十]+[：:.]/);
  assert.doesNotMatch(svg, /AI 健康感知与 6G 星地传输的闭环证据图/);
});

test('all text stays inside the canvas and the score panel carries scientific metadata', async () => {
  const svg = await fs.readFile(svgUrl, 'utf8');
  const textX = [...svg.matchAll(/<text x="([0-9.]+)"/g)].map((m) => Number(m[1]));
  assert.ok(textX.length > 0);
  assert.ok(Math.max(...textX) <= 1645, `text exceeds safe right margin: ${Math.max(...textX)}`);
  assert.match(svg, /离线教师效用分数/);
  assert.match(svg, /OPTIMAL/);
  assert.match(svg, /gap = 0\.0/);
});
