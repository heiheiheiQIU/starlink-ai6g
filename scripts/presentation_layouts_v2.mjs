import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';

export const CANVAS = Object.freeze({ width: 1600, height: 900 });
export const TYPOGRAPHY = Object.freeze({ title: 34, claim: 19, body: 18, metric: 20, source: 10.5 });

export const HERO_GEOMETRY = Object.freeze({
  title: Object.freeze({ left: 84, top: 180, width: 760, height: 150 }),
  claim: Object.freeze({ left: 88, top: 344, width: 780, height: 90 }),
  rule: Object.freeze({ left: 88, top: 458, width: 86, height: 5 }),
  metrics: Object.freeze({ left: 88, top: 500, width: 700, height: 160 }),
  meaning: Object.freeze({ left: 88, top: 698, width: 1030, height: 82 }),
  source: Object.freeze({ left: 88, top: 822, width: 1120, height: 24 }),
});
export const THEME_ASSET = 'frontend/public/visuals/orbital-command-backdrop-v1.png';
export const ROOT = path.resolve(import.meta.dirname, '..');

export const COLORS = Object.freeze({
  navy: '#06111D', navy2: '#0A2035', panel: '#0D2237', white: '#F6F9FC',
  ink: '#152536', muted: '#A8B8C8', steel: '#657E95', cyan: '#6ED6E6',
  blue: '#4F8FEA', teal: '#4FC3A1', amber: '#F4B84A', coral: '#EF6A6A',
  pale: '#F4F7FA', line: '#C9D5E0',
});

export const LAYOUT_FAMILIES = Object.freeze({
  scenario: 'scenario-timeline',
  comparison: 'comparison-matrix',
  mechanism: 'mechanism-chain',
  experiment: 'experiment-protocol',
  boundary: 'engineering-boundary',
  product: 'product-evidence',
});

const common = {
  header: { left: 72, top: 34, width: 1456, height: 142 },
  source: { left: 74, top: 852, width: 1450, height: 20 },
};

export const LAYOUT_GEOMETRY = Object.freeze({
  scenario: {
    ...common,
    evidence: { left: 72, top: 214, width: 930, height: 448 },
    facts: { left: 1030, top: 214, width: 498, height: 448 },
    meaning: { left: 72, top: 692, width: 1456, height: 126 },
  },
  comparison: {
    ...common,
    evidence: { left: 72, top: 214, width: 760, height: 520 },
    facts: { left: 860, top: 214, width: 668, height: 520 },
    meaning: { left: 72, top: 758, width: 1456, height: 64 },
  },
  mechanism: {
    ...common,
    evidence: { left: 72, top: 210, width: 1456, height: 404 },
    facts: { left: 72, top: 642, width: 1456, height: 116 },
    meaning: { left: 72, top: 774, width: 1456, height: 54 },
  },
  experiment: {
    ...common,
    evidence: { left: 72, top: 214, width: 948, height: 510 },
    facts: { left: 1048, top: 214, width: 480, height: 510 },
    meaning: { left: 72, top: 752, width: 1456, height: 72 },
  },
  boundary: {
    ...common,
    evidence: { left: 524, top: 214, width: 1004, height: 500 },
    facts: { left: 72, top: 214, width: 424, height: 500 },
    meaning: { left: 72, top: 744, width: 1456, height: 80 },
  },
  product: {
    ...common,
    evidence: { left: 72, top: 214, width: 1020, height: 516 },
    facts: { left: 1120, top: 214, width: 408, height: 516 },
    meaning: { left: 72, top: 758, width: 1456, height: 66 },
  },
});

export function validatePosition(position) {
  const { left, top, width, height } = position;
  const valid = [left, top, width, height].every(Number.isFinite)
    && left >= 0 && top >= 0 && width > 0 && height > 0
    && left + width <= CANVAS.width && top + height <= CANVAS.height;
  if (!valid) throw new Error(`Position outside 1600x900 canvas: ${JSON.stringify(position)}`);
  return position;
}

function addShape(slide, geometry, position, fill, line = { fill: 'none', width: 0 }, shadow) {
  validatePosition(position);
  return slide.shapes.add({ geometry, position, fill, line, ...(shadow ? { shadow } : {}) });
}

function addText(slide, text, position, style = {}) {
  validatePosition(position);
  const shape = slide.shapes.add({
    geometry: 'textbox', position, text: { text }, fill: 'none', line: { fill: 'none', width: 0 },
  });
  shape.text.style = { typeface: 'Microsoft YaHei', color: COLORS.white, fontSize: TYPOGRAPHY.body, ...style };
  return shape;
}

async function addImage(slide, absolutePath, position, fit = 'contain', alt = '') {
  validatePosition(position);
  const data = await fsp.readFile(absolutePath);
  slide.images.add({
    blob: data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength),
    contentType: absolutePath.toLowerCase().endsWith('.jpg') || absolutePath.toLowerCase().endsWith('.jpeg') ? 'image/jpeg' : 'image/png',
    alt, fit, position,
  });
}

export async function addThemeBackground(slide, { hero = false } = {}) {
  const absolute = path.resolve(ROOT, THEME_ASSET);
  if (!fs.existsSync(absolute)) throw new Error(`Missing theme asset: ${absolute}`);
  slide.background.fill = COLORS.navy;
  await addImage(slide, absolute, { left: 0, top: 0, width: 1600, height: 900 }, 'cover', '星地智调卫星地球通信主题背景');
  const overlay = hero
    ? 'linear(90deg, #06111D/96 0%, #06111D/75 48%, #06111D/18 100%)'
    : 'linear(180deg, #06111D/78 0%, #071827/63 52%, #06111D/82 100%)';
  addShape(slide, 'rect', { left: 0, top: 0, width: 1600, height: 900 }, overlay);
}

export function addClaimHeader(slide, spec, pageLabel) {
  addText(slide, '星地智调 · 面向6G星地融合的健康感知智能通信调度',
    { left: 72, top: 28, width: 760, height: 24 }, { fontSize: 11.5, color: COLORS.muted });
  addText(slide, spec.section, { left: 72, top: 66, width: 360, height: 30 },
    { fontSize: 15, bold: true, color: COLORS.cyan });
  addText(slide, spec.title, { left: 72, top: 104, width: 1330, height: 48 },
    { fontSize: TYPOGRAPHY.title, bold: true, color: COLORS.white });
  addText(slide, spec.claim, { left: 72, top: 158, width: 1340, height: 32 },
    { fontSize: TYPOGRAPHY.claim, color: '#D4E1EC' });
  addText(slide, pageLabel, { left: 1440, top: 48, width: 88, height: 26 },
    { fontSize: 13, bold: true, color: COLORS.muted, alignment: 'right' });
  addShape(slide, 'rect', { left: 72, top: 198, width: 1456, height: 2 },
    'linear(90deg, #6ED6E6 0%, #4F8FEA/58 58%, #4F8FEA/0 100%)');
}

export function addEvidencePanel(slide, { asset, position, alt = '', fit = 'contain', label = '主证据' }) {
  const absolute = path.resolve(ROOT, asset);
  if (!fs.existsSync(absolute)) throw new Error(`Missing evidence asset: ${absolute}`);
  validatePosition(position);
  addShape(slide, 'roundRect', position, '#F7F9FC/97', { fill: '#FFFFFF/42', width: 1 }, 'shadow-md');
  const badge = { left: position.left + 18, top: position.top + 16, width: 116, height: 28 };
  addShape(slide, 'roundRect', badge, '#0D2237/94', { fill: COLORS.cyan, width: 1 });
  addText(slide, label, { left: badge.left + 8, top: badge.top + 4, width: 100, height: 20 },
    { fontSize: 12, bold: true, color: COLORS.cyan, alignment: 'center' });
  const imagePosition = {
    left: position.left + 16, top: position.top + 54,
    width: position.width - 32, height: position.height - 70,
  };
  return addImage(slide, absolute, imagePosition, fit, alt);
}

export function addMetricStrip(slide, facts, position, { compact = false } = {}) {
  validatePosition(position);
  const gap = 14;
  const count = Math.max(1, facts.length);
  const width = (position.width - gap * (count - 1)) / count;
  facts.forEach((fact, index) => {
    const left = position.left + index * (width + gap);
    const accent = [COLORS.cyan, COLORS.blue, COLORS.teal, COLORS.amber][index % 4];
    addShape(slide, 'roundRect', { left, top: position.top, width, height: position.height },
      compact ? '#0B1E31/90' : '#10283F/91', { fill: `${accent}/70`, width: 1 });
    addShape(slide, 'rect', { left: left + 18, top: position.top + 16, width: 6, height: Math.min(44, position.height - 30) }, accent);
    addText(slide, String(index + 1).padStart(2, '0'),
      { left: left + 38, top: position.top + 13, width: 42, height: 24 },
      { fontSize: 12, bold: true, color: accent });
    addText(slide, fact,
      { left: left + 38, top: position.top + 38, width: width - 58, height: position.height - 48 },
      { fontSize: compact ? 15.5 : TYPOGRAPHY.body, color: COLORS.white });
  });
}

export function addInterpretation(slide, text, position, { label = '业务含义', accent = COLORS.teal } = {}) {
  validatePosition(position);
  addShape(slide, 'roundRect', position, '#071B2C/94', { fill: `${accent}/82`, width: 1.25 });
  addText(slide, label, { left: position.left + 22, top: position.top + 18, width: 112, height: 24 },
    { fontSize: 13, bold: true, color: accent });
  addText(slide, text,
    { left: position.left + 142, top: position.top + 14, width: position.width - 166, height: position.height - 24 },
    { fontSize: TYPOGRAPHY.body, bold: true, color: COLORS.white });
}

export function addSourceNote(slide, text) {
  addText(slide, text, LAYOUT_GEOMETRY.scenario.source,
    { fontSize: TYPOGRAPHY.source, color: COLORS.muted });
}

function factStack(slide, facts, position, { accent = COLORS.cyan, heading = '关键信息' } = {}) {
  addShape(slide, 'roundRect', position, '#0B1E31/93', { fill: `${accent}/64`, width: 1.2 }, 'shadow-md');
  addText(slide, heading, { left: position.left + 28, top: position.top + 24, width: position.width - 56, height: 30 },
    { fontSize: 17, bold: true, color: accent });
  const rowHeight = (position.height - 76) / facts.length;
  facts.forEach((fact, index) => {
    const top = position.top + 72 + index * rowHeight;
    addText(slide, String(index + 1).padStart(2, '0'), { left: position.left + 28, top, width: 42, height: 26 },
      { fontSize: 13, bold: true, color: accent });
    addText(slide, fact, { left: position.left + 78, top: top - 2, width: position.width - 106, height: rowHeight - 8 },
      { fontSize: TYPOGRAPHY.body, color: COLORS.white });
    if (index < facts.length - 1) addShape(slide, 'rect',
      { left: position.left + 28, top: top + rowHeight - 12, width: position.width - 56, height: 1 }, `${accent}/28`);
  });
}

async function prepare(slide, spec, pageLabel) {
  await addThemeBackground(slide);
  addClaimHeader(slide, spec, pageLabel);
}

export async function renderScenarioTimeline({ slide, spec, pageLabel }) {
  const g = LAYOUT_GEOMETRY.scenario;
  await prepare(slide, spec, pageLabel);
  await addEvidencePanel(slide, { ...spec.evidence[0], position: g.evidence, label: '场景证据' });
  factStack(slide, spec.supportingFacts, g.facts, { heading: '约束与任务' });
  addInterpretation(slide, spec.businessMeaning, g.meaning);
  addSourceNote(slide, spec.sourceNote);
}

export async function renderComparisonMatrix({ slide, spec, pageLabel }) {
  const g = LAYOUT_GEOMETRY.comparison;
  await prepare(slide, spec, pageLabel);
  await addEvidencePanel(slide, { ...spec.evidence[0], position: g.evidence, label: '对照证据' });
  factStack(slide, spec.supportingFacts, g.facts, { accent: COLORS.amber, heading: '比较与边界' });
  addInterpretation(slide, spec.businessMeaning, g.meaning, { accent: COLORS.amber });
  addSourceNote(slide, spec.sourceNote);
}

export async function renderMechanismChain({ slide, spec, pageLabel }) {
  const g = LAYOUT_GEOMETRY.mechanism;
  await prepare(slide, spec, pageLabel);
  await addEvidencePanel(slide, { ...spec.evidence[0], position: g.evidence, label: '机制主链' });
  addMetricStrip(slide, spec.supportingFacts, g.facts, { compact: true });
  addInterpretation(slide, spec.businessMeaning, g.meaning);
  addSourceNote(slide, spec.sourceNote);
}

export async function renderExperimentProtocol({ slide, spec, pageLabel }) {
  const g = LAYOUT_GEOMETRY.experiment;
  await prepare(slide, spec, pageLabel);
  await addEvidencePanel(slide, { ...spec.evidence[0], position: g.evidence, label: spec.status === '未完成' ? '裁决协议' : '实验协议' });
  factStack(slide, spec.supportingFacts, g.facts, { accent: spec.status === '未完成' ? COLORS.amber : COLORS.blue, heading: spec.status });
  addInterpretation(slide, spec.businessMeaning, g.meaning, { accent: spec.status === '未完成' ? COLORS.amber : COLORS.blue });
  addSourceNote(slide, spec.sourceNote);
}

export async function renderEngineeringBoundary({ slide, spec, pageLabel }) {
  const g = LAYOUT_GEOMETRY.boundary;
  await prepare(slide, spec, pageLabel);
  factStack(slide, spec.supportingFacts, g.facts, { accent: COLORS.amber, heading: '触发与审计边界' });
  await addEvidencePanel(slide, { ...spec.evidence[0], position: g.evidence, label: '工程边界' });
  addInterpretation(slide, spec.businessMeaning, g.meaning, { accent: COLORS.amber });
  addSourceNote(slide, spec.sourceNote);
}

export async function renderProductEvidence({ slide, spec, pageLabel }) {
  const g = LAYOUT_GEOMETRY.product;
  await prepare(slide, spec, pageLabel);
  await addEvidencePanel(slide, { ...spec.evidence[0], position: g.evidence, fit: 'cover', label: '工程平台' });
  factStack(slide, spec.supportingFacts, g.facts, { accent: COLORS.teal, heading: '操作链与接口' });
  addInterpretation(slide, spec.businessMeaning, g.meaning, { accent: COLORS.teal });
  addSourceNote(slide, spec.sourceNote);
}

export async function renderHero({ slide, spec, pageLabel }) {
  const g = HERO_GEOMETRY;
  await addThemeBackground(slide, { hero: true });
  addText(slide, spec.section, { left: 88, top: 108, width: 460, height: 34 },
    { fontSize: 17, bold: true, color: COLORS.cyan });
  addText(slide, spec.title, g.title,
    { fontSize: spec.title.length > 18 ? 48 : 56, bold: true, color: COLORS.white });
  addText(slide, spec.claim, g.claim,
    { fontSize: spec.claim.length > 42 ? 27 : 30, bold: true, color: COLORS.white });
  addShape(slide, 'rect', g.rule, COLORS.cyan);
  addMetricStrip(slide, spec.supportingFacts, g.metrics, { compact: true });
  addInterpretation(slide, spec.businessMeaning, g.meaning);
  addText(slide, spec.sourceNote, g.source,
    { fontSize: TYPOGRAPHY.source, color: COLORS.muted });
  addText(slide, pageLabel, { left: 1436, top: 48, width: 92, height: 26 },
    { fontSize: 13, bold: true, color: COLORS.muted, alignment: 'right' });
}

export const RENDERERS = Object.freeze({
  hero: renderHero,
  'scenario-timeline': renderScenarioTimeline,
  'comparison-matrix': renderComparisonMatrix,
  'mechanism-chain': renderMechanismChain,
  'experiment-protocol': renderExperimentProtocol,
  'engineering-boundary': renderEngineeringBoundary,
  'product-evidence': renderProductEvidence,
});
