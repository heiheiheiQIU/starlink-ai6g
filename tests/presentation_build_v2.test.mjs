import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const ROOT = path.resolve(import.meta.dirname, '..');

test('main deck builder registers every layout and resource', async () => {
  const { MAIN_SLIDES } = await import('../scripts/presentation_story_v2.mjs');
  const { RENDERERS } = await import('../scripts/presentation_layouts_v2.mjs');
  const { validateStoryResources } = await import('../scripts/build_presentation_v2.mjs');
  for (const slide of MAIN_SLIDES) assert.equal(typeof RENDERERS[slide.layout], 'function', `${slide.id} layout ${slide.layout}`);
  const manifest = validateStoryResources(MAIN_SLIDES);
  assert.equal(manifest.length, MAIN_SLIDES.reduce((sum, slide) => sum + slide.evidence.length, 0));
  assert.ok(manifest.every((item) => fs.existsSync(item.absolutePath)));
});

test('main deck contract keeps hero endpoints and critical boundaries', async () => {
  const { MAIN_SLIDES } = await import('../scripts/presentation_story_v2.mjs');
  assert.equal(MAIN_SLIDES[0].layout, 'hero');
  assert.equal(MAIN_SLIDES[14].layout, 'hero');
  assert.match(JSON.stringify(MAIN_SLIDES[7]), /观测条件/);
  assert.match(JSON.stringify(MAIN_SLIDES[7]), /仿真真值/);
  assert.equal(MAIN_SLIDES[10].status, '未完成');
});

test('builder exposes 15-page main deck and deterministic preview paths', async () => {
  const { buildMainDeck, outputPaths } = await import('../scripts/build_presentation_v2.mjs');
  assert.equal(typeof buildMainDeck, 'function');
  const paths = outputPaths('main');
  assert.equal(paths.slidePngs.length, 15);
  assert.equal(path.basename(paths.montage), 'main-montage.png');
  assert.match(paths.slidePngs[0], /slide-01\.png$/);
  assert.match(paths.slidePngs[14], /slide-15\.png$/);
});

test('main deck avoids shrinking master plates and uses real product evidence', async () => {
  const { MAIN_SLIDES } = await import('../scripts/presentation_story_v2.mjs');
  const masterPlateCount = MAIN_SLIDES.flatMap((slide) => slide.evidence)
    .filter((item) => item.asset.includes('/v4/report/previews/')).length;
  assert.ok(masterPlateCount <= 2, `too many full master plates: ${masterPlateCount}`);
  assert.ok(!MAIN_SLIDES[11].evidence[0].asset.endsWith('orbital-command-backdrop-v1.png'));
});

test('hero title and claim geometry do not overlap', async () => {
  const { HERO_GEOMETRY } = await import('../scripts/presentation_layouts_v2.mjs');
  assert.ok(HERO_GEOMETRY.title.top + HERO_GEOMETRY.title.height <= HERO_GEOMETRY.claim.top);
  assert.ok(HERO_GEOMETRY.claim.top + HERO_GEOMETRY.claim.height <= HERO_GEOMETRY.rule.top);
});

test('full deck appends five answer-backup pages after the 15-page talk', async () => {
  const { MAIN_SLIDES, BACKUP_SLIDES } = await import('../scripts/presentation_story_v2.mjs');
  const { buildFullDeck, outputPaths } = await import('../scripts/build_presentation_v2.mjs');
  assert.equal(typeof buildFullDeck, 'function');
  assert.deepEqual(BACKUP_SLIDES.map((slide) => slide.id), ['B1', 'B2', 'B3', 'B4', 'B5']);
  assert.ok(BACKUP_SLIDES.every((slide) => slide.section === '答辩备查'));
  assert.equal(MAIN_SLIDES.length + BACKUP_SLIDES.length, 20);
  assert.equal(outputPaths('full').slidePngs.length, 20);
});

test('final export contract keeps main talk order separate from answer backups', async () => {
  const { FINAL_DECK_PATH, MAIN_TALK_SLIDE_COUNT, exportFinalDeck } = await import('../scripts/build_presentation_v2.mjs');
  assert.equal(MAIN_TALK_SLIDE_COUNT, 15);
  assert.equal(typeof exportFinalDeck, 'function');
  assert.match(FINAL_DECK_PATH, /星地智调_主讲稿_v3_正式结果工程化版\.pptx$/);
});
