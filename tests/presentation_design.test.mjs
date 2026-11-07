import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import test from 'node:test';

test('all 15 slides use the project theme background', async () => {
  const { SLIDE_SPECS, THEME } = await import('../scripts/presentation_design.mjs');
  assert.equal(SLIDE_SPECS.length, 15);
  assert.equal(THEME.backgroundAsset, 'docs/figures/generated/v2/C-F00_星地智调主题背景_v1.png');
  assert.ok(SLIDE_SPECS.every((slide) => slide.backgroundAsset === THEME.backgroundAsset));
});

test('body slides reserve space for evidence and interpretation', async () => {
  const { SLIDE_SPECS, THEME } = await import('../scripts/presentation_design.mjs');
  const bodySlides = SLIDE_SPECS.filter((slide) => slide.kind === 'body');
  assert.equal(bodySlides.length, 11);
  for (const slide of bodySlides) {
    assert.ok(slide.evidenceCoverage > 0 && slide.evidenceCoverage <= THEME.maxEvidenceCoverage, `slide ${slide.index} evidence coverage`);
    assert.ok(slide.insightCoverage >= THEME.minInsightCoverage, `slide ${slide.index} insight coverage`);
  }
});

test('formal result slide remains unsigned and incomplete', async () => {
  const { SLIDE_SPECS } = await import('../scripts/presentation_design.mjs');
  const resultSlide = SLIDE_SPECS.find((slide) => slide.index === 11);
  assert.equal(resultSlide.status, '未完成');
  assert.equal(resultSlide.requiresTripartiteSignoff, true);
});

test('generator targets v1 and consumes the unified design contract', async () => {
  const source = await fs.readFile(new URL('../scripts/build_presentation.mjs', import.meta.url), 'utf8');
  assert.match(source, /presentation_design\.mjs/);
  assert.match(source, /星地智调_主讲稿_v1_统一特色背景版\.pptx/);
  assert.doesNotMatch(source, /function addFigureSlide|async function addFigureSlide/);
});

test('insight panel consumes the dedicated insight copy fields', async () => {
  const source = await fs.readFile(new URL('../scripts/build_presentation.mjs', import.meta.url), 'utf8');
  assert.match(source, /function addInsightPanel\(slide, \{ side, insightTitle, insightBody, accent, footer, status \}\)/);
  assert.match(source, /addText\(slide, insightTitle,/);
  assert.match(source, /addText\(slide, insightBody,/);
});
