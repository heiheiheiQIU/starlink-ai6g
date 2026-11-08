import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';

test('layout module exposes six evidence-dense renderers and readable typography', async () => {
  const layouts = await import('../scripts/presentation_layouts_v2.mjs');
  for (const name of [
    'renderScenarioTimeline', 'renderComparisonMatrix', 'renderMechanismChain',
    'renderExperimentProtocol', 'renderEngineeringBoundary', 'renderProductEvidence',
  ]) assert.equal(typeof layouts[name], 'function', `${name} must be exported`);
  assert.ok(layouts.TYPOGRAPHY.body >= 18);
  assert.ok(layouts.TYPOGRAPHY.source >= 10.5);
  assert.ok(layouts.TYPOGRAPHY.title >= 32);
  assert.equal(new Set(Object.values(layouts.LAYOUT_FAMILIES)).size, 6);
});

test('layout geometry stays inside the 1600 by 900 canvas', async () => {
  const { CANVAS, LAYOUT_GEOMETRY, validatePosition } = await import('../scripts/presentation_layouts_v2.mjs');
  assert.deepEqual(CANVAS, { width: 1600, height: 900 });
  for (const [family, positions] of Object.entries(LAYOUT_GEOMETRY)) {
    for (const [name, position] of Object.entries(positions)) {
      assert.doesNotThrow(() => validatePosition(position), `${family}.${name}`);
    }
  }
  assert.throws(() => validatePosition({ left: 1500, top: 0, width: 200, height: 50 }), /outside 1600x900/);
});

test('missing evidence resource throws an error with the absolute path', async () => {
  const { addEvidencePanel } = await import('../scripts/presentation_layouts_v2.mjs');
  const missing = 'docs/figures/generated/v4/report/previews/does-not-exist.png';
  assert.throws(
    () => addEvidencePanel(null, { asset: missing, position: { left: 0, top: 0, width: 100, height: 100 } }),
    (error) => error.message.includes(path.resolve(missing)) && error.message.includes('Missing evidence asset'),
  );
});

test('shared primitives are available to the deck builder', async () => {
  const layouts = await import('../scripts/presentation_layouts_v2.mjs');
  for (const name of [
    'addThemeBackground', 'addClaimHeader', 'addEvidencePanel',
    'addMetricStrip', 'addInterpretation', 'addSourceNote',
  ]) assert.equal(typeof layouts[name], 'function', `${name} must be exported`);
});
