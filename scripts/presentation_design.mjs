export const THEME = Object.freeze({
  backgroundAsset: 'docs/figures/generated/v2/C-F00_星地智调主题背景_v1.png',
  maxEvidenceCoverage: 0.72,
  minInsightCoverage: 0.22,
  bodyOverlayOpacity: 0.48,
});

const backgroundAsset = THEME.backgroundAsset;
const body = (index, section, layout = 'single') => ({
  index,
  kind: 'body',
  section,
  layout,
  backgroundAsset,
  evidenceCoverage: layout === 'double' ? 0.66 : 0.64,
  insightCoverage: layout === 'double' ? 0.24 : 0.26,
});

export const SLIDE_SPECS = Object.freeze([
  { index: 1, kind: 'cover', section: '封面', backgroundAsset },
  { index: 2, kind: 'narrative', section: '场景需求', backgroundAsset },
  body(3, '场景需求'),
  body(4, '场景需求', 'double'),
  body(5, '方案设计'),
  body(6, 'AI+6G'),
  body(7, '智能评分'),
  { index: 8, kind: 'constraints', section: '安全执行', backgroundAsset },
  body(9, '证据闭环'),
  body(10, '实验设计', 'double'),
  { ...body(11, '正式结果'), status: '未完成', requiresTripartiteSignoff: true },
  body(12, '协议可靠性'),
  body(13, '信息边界'),
  body(14, '落地路线'),
  { index: 15, kind: 'ending', section: '结束', backgroundAsset },
]);
