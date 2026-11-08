import assert from 'node:assert/strict';
import test from 'node:test';

const REQUIRED_FIELDS = [
  'id', 'section', 'title', 'claim', 'layout', 'evidence',
  'supportingFacts', 'businessMeaning', 'sourceNote', 'status',
];

test('story contract defines 15 main slides and 5 backup slides', async () => {
  const { MAIN_SLIDES, BACKUP_SLIDES } = await import('../scripts/presentation_story_v2.mjs');
  assert.equal(MAIN_SLIDES.length, 15);
  assert.equal(BACKUP_SLIDES.length, 5);
  assert.deepEqual(MAIN_SLIDES.map((slide) => slide.id), Array.from({ length: 15 }, (_, i) => `S${i + 1}`));
  assert.deepEqual(BACKUP_SLIDES.map((slide) => slide.id), ['B1', 'B2', 'B3', 'B4', 'B5']);
});

test('body slides carry evidence explanation and business meaning', async () => {
  const { MAIN_SLIDES, BACKUP_SLIDES } = await import('../scripts/presentation_story_v2.mjs');
  for (const slide of [...MAIN_SLIDES.slice(1, 14), ...BACKUP_SLIDES]) {
    for (const field of REQUIRED_FIELDS) assert.ok(Object.hasOwn(slide, field), `${slide.id} missing ${field}`);
    assert.ok(slide.evidence.length >= 1, `${slide.id} needs a primary evidence item`);
    assert.ok(slide.supportingFacts.length >= 2, `${slide.id} needs at least two supporting facts`);
    assert.ok(slide.businessMeaning.trim().length >= 12, `${slide.id} needs a concrete business meaning`);
    assert.ok(slide.sourceNote.trim().length >= 8, `${slide.id} needs a source or scope note`);
  }
});

test('visible copy preserves evidence and safety boundaries', async () => {
  const { MAIN_SLIDES, BACKUP_SLIDES, SLIDE_GUARDRAILS } = await import('../scripts/presentation_story_v2.mjs');
  const visible = JSON.stringify([...MAIN_SLIDES, ...BACKUP_SLIDES]);
  for (const forbidden of ['绝对安全', '不能被突破', '全面优于', '真实在轨部署']) {
    assert.ok(!visible.includes(forbidden), `forbidden claim: ${forbidden}`);
  }
  assert.deepEqual(SLIDE_GUARDRAILS.formalResultVocabulary, ['胜', '等效', '负', '未完成']);
  const result = MAIN_SLIDES[10];
  assert.equal(result.status, '未完成');
  assert.match(`${result.title}${result.claim}${result.businessMeaning}`, /未完成/);
  assert.match(visible, /胜.*等效.*负.*未完成/);
  assert.doesNotMatch(JSON.stringify(result), /\d+(?:\.\d+)?%/);
});

test('guard slide distinguishes observed feasibility from simulated truth', async () => {
  const { MAIN_SLIDES } = await import('../scripts/presentation_story_v2.mjs');
  const guard = MAIN_SLIDES[7];
  const text = JSON.stringify(guard);
  assert.match(text, /观测条件/);
  assert.match(text, /仿真真值/);
  assert.match(text, /回退/);
});
