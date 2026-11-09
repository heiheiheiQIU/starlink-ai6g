import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const C = {
  white: '#FFFFFF', ink: '#172A3A', muted: '#526575', grid: '#D7E0E6', pale: '#F5F8FA',
  navy: '#24506F', cyan: '#2B88A3', teal: '#268B79', amber: '#D58A27', red: '#C84F55',
  sky: '#EAF3F7', mint: '#E9F5F1', sand: '#FCF3E4', rose: '#F9ECEC', violet: '#747FA3',
};
const FONT = "Arial, 'Source Han Sans SC', 'Microsoft YaHei', sans-serif";
const VERDICTS = new Set(['胜', '负', '未检出稳定差异', '未完成']);

function fail(message) { throw new Error(message); }
function record(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
function finite(value) { return typeof value === 'number' && Number.isFinite(value); }
function integer(value) { return Number.isInteger(value) && value >= 0; }
function interval(value) { return Array.isArray(value) && value.length === 2 && finite(value[0]) && finite(value[1]) && value[0] <= value[1]; }
function esc(value) { return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;'); }
function text(x, y, value, size = 18, weight = 400, fill = C.ink, anchor = 'start') {
  return `<text x="${x}" y="${y}" font-family="${FONT}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}">${esc(value)}</text>`;
}
function rect(x, y, width, height, fill = C.white, stroke = C.grid, strokeWidth = 1.2, radius = 3) {
  return `<rect x="${x}" y="${y}" width="${width}" height="${height}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}" rx="${radius}"/>`;
}
function line(x1, y1, x2, y2, stroke = C.grid, strokeWidth = 1.2, dash = '') {
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${strokeWidth}"${dash ? ` stroke-dasharray="${dash}"` : ''}/>`;
}
function circle(x, y, radius, fill, stroke = C.white, strokeWidth = 2) {
  return `<circle cx="${x}" cy="${y}" r="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
}
function panelHeading(x, y, mark, title, subtitle) {
  return `${text(x, y, mark, 23, 800)}${text(x + 48, y, title, 23, 800)}${text(x + 48, y + 29, subtitle, 14, 400, C.muted)}`;
}
function shell(body, scope, heightMm = 105, viewHeight = 1050) {
  return `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="170mm" height="${heightMm}mm" viewBox="0 0 1700 ${viewHeight}" role="img"><rect x="0" y="0" width="1700" height="${viewHeight}" fill="#FFFFFF"/>${body}${line(55, viewHeight - 34, 1645, viewHeight - 34)}${text(55, viewHeight - 12, scope, 12, 600, C.red)}${text(1645, viewHeight - 12, '来源：签核后的 formal-analysis-summary-v1', 12, 500, C.muted, 'end')}</svg>\n`;
}

function classify(mean, ci95) {
  if (mean === null || ci95 === null) return '未完成';
  if (mean > 0 && ci95[0] > 0) return '胜';
  if (mean < 0 && ci95[1] < 0) return '负';
  return '未检出稳定差异';
}

function validateComparison(value, id) {
  if (!record(value) || !Array.isArray(value.cells) || value.cells.length !== 18) fail(`${id}必须包含18个工况格`);
  const ids = new Set();
  let pairs = 0;
  for (const cell of value.cells) {
    if (!record(cell) || typeof cell.cell_id !== 'string' || ids.has(cell.cell_id) || !integer(cell.n) || !integer(cell.missing)
      || cell.n + cell.missing !== 10 || (cell.mean_delta !== null && !finite(cell.mean_delta))
      || (cell.ci95 !== null && !interval(cell.ci95))) fail(`${id}工况格结构无效`);
    ids.add(cell.cell_id); pairs += cell.n;
  }
  if (!integer(value.paired_count) || value.paired_count !== pairs || !record(value.overall)
    || (value.overall.mean_delta !== null && !finite(value.overall.mean_delta))
    || (value.overall.ci95 !== null && !interval(value.overall.ci95))
    || !VERDICTS.has(value.statistical_verdict) || !VERDICTS.has(value.formal_verdict)) fail(`${id}总体统计结构无效`);
  if (value.statistical_verdict !== classify(value.overall.mean_delta, value.overall.ci95)) fail(`${id}统计结论与区间不一致`);
  if (value.formal_verdict !== value.statistical_verdict) fail(`${id}正式结论与冻结统计结论不一致`);
  return value;
}

function validate(summary) {
  if (!record(summary) || summary.schema_version !== 'formal-analysis-summary-v1') fail('不支持的正式分析版本');
  if (summary.result_signoff !== 'accepted') fail('必须完成A/B/C三方结果签核后才能生成材料图件');
  if (summary.expected_policy_runs !== 540 || !integer(summary.completed_policy_runs) || !integer(summary.failed_policy_runs)
    || !integer(summary.missing_policy_runs) || summary.completed_policy_runs + summary.failed_policy_runs + summary.missing_policy_runs !== 540) fail('540次策略运行计数不一致');
  if (!record(summary.comparisons) || !record(summary.provenance)
    || !/^[a-f0-9]{64}$/i.test(summary.provenance.frozen_manifest_sha256 ?? '')
    || !/^[a-f0-9]{64}$/i.test(summary.provenance.run_index_sha256 ?? '')) fail('正式证据来源无效');
  validateComparison(summary.comparisons['learned-edf'], 'learned-edf');
  validateComparison(summary.comparisons['learned-value'], 'learned-value');
  if (!record(summary.inference) || !integer(summary.inference.requests) || !integer(summary.inference.fallback_count)
    || summary.inference.fallback_count > summary.inference.requests || typeof summary.inference.scope !== 'string'
    || (summary.inference.decision_latency_median_ms !== null && !finite(summary.inference.decision_latency_median_ms))
    || (summary.inference.decision_latency_p95_ms !== null && !finite(summary.inference.decision_latency_p95_ms))) fail('推理证据结构无效');
  return summary;
}

function number(value, digits = 4) { return value === null ? '—' : Number(value).toFixed(digits); }
function verdictColor(verdict) { return verdict === '胜' ? C.teal : verdict === '负' ? C.red : verdict === '未完成' ? C.muted : C.cyan; }

function overviewFigure(summary) {
  const edf = summary.comparisons['learned-edf'];
  const value = summary.comparisons['learned-value'];
  let body = panelHeading(55, 72, '(a)', '正式运行完整度', '冻结范围内的完成、失败与缺失均原样计数');
  const counts = [
    ['完成', summary.completed_policy_runs, C.teal], ['失败', summary.failed_policy_runs, C.red],
    ['缺失', summary.missing_policy_runs, C.amber], ['总计', 540, C.navy],
  ];
  counts.forEach((item, index) => {
    const x = 80 + index * 185;
    body += `${rect(x, 145, 160, 120, C.pale, item[2], 1.5)}${text(x + 80, 188, item[0], 15, 700, C.muted, 'middle')}${text(x + 80, 238, item[1], 29, 800, item[2], 'middle')}`;
  });
  body += `${rect(80, 300, 715, 100, C.sky, C.cyan)}${text(105, 335, '数据范围', 14, 700, C.muted)}${text(250, 335, `${summary.data_scope} · ${summary.domain}`, 15, 700)}${text(105, 370, '签核状态', 14, 700, C.muted)}${text(250, 370, 'A/B/C accepted', 15, 800, C.teal)}`;

  body += panelHeading(865, 72, '(b)', '两项预登记主比较', '总体均值差与95% CI；正值表示Learned较高');
  const axisLeft = 1015; const axisRight = 1575; const zero = (axisLeft + axisRight) / 2;
  const bounds = [edf.overall.mean_delta, ...(edf.overall.ci95 ?? []), value.overall.mean_delta, ...(value.overall.ci95 ?? [])].filter(finite);
  const axisLimit = Math.max(0.1, Math.ceil(Math.max(...bounds.map(Math.abs), 0) * 10) / 10);
  const scale = (axisRight - axisLeft) / (2 * axisLimit);
  [-axisLimit, -axisLimit / 2, 0, axisLimit / 2, axisLimit].forEach((tick) => {
    const x = zero + tick * scale;
    body += `${line(x, 155, x, 400, tick === 0 ? C.ink : C.grid, tick === 0 ? 1.8 : 1)}${text(x, 430, tick.toFixed(1), 12, 500, C.muted, 'middle')}`;
  });
  [['Learned − EDF', edf, 225], ['Learned − Value', value, 335]].forEach(([label, comparison, y]) => {
    const mean = comparison.overall.mean_delta; const ci = comparison.overall.ci95; const color = verdictColor(comparison.formal_verdict);
    body += text(995, y + 6, label, 15, 700, C.ink, 'end');
    if (mean !== null && ci !== null) body += `${line(zero + ci[0] * scale, y, zero + ci[1] * scale, y, color, 6)}${circle(zero + mean * scale, y, 10, color)}`;
    body += `${text(1595, y - 8, comparison.formal_verdict, 14, 800, color, 'end')}${text(1595, y + 18, `Δ=${number(mean)} · n=${comparison.paired_count}`, 12, 600, C.muted, 'end')}`;
  });

  body += panelHeading(55, 535, '(c)', '推理与安全运行证据', '本机CPU端到端决策口径，不外推为在轨时延');
  const inference = summary.inference ?? {};
  const metrics = [
    ['推理请求', inference.requests ?? null, '次'], ['安全回退', inference.fallback_count ?? null, '次'],
    ['决策中位时延', inference.decision_latency_median_ms ?? null, 'ms'], ['决策p95时延', inference.decision_latency_p95_ms ?? null, 'ms'],
  ];
  metrics.forEach((item, index) => {
    const x = 80 + (index % 2) * 350; const y = 625 + Math.floor(index / 2) * 125;
    body += `${rect(x, y, 320, 92, C.white, C.grid)}${text(x + 22, y + 32, item[0], 14, 700, C.muted)}${text(x + 22, y + 69, item[1] === null ? '—' : `${number(item[1], 2)} ${item[2]}`, 21, 800, C.navy)}`;
  });
  body += `${rect(80, 880, 670, 62, C.sand, C.amber)}${text(415, 918, inference.scope ?? '未提供推理口径', 13, 700, C.amber, 'middle')}`;

  body += panelHeading(865, 535, '(d)', '证据溯源与口径边界', '图件只消费签核JSON，不由材料反向修改实验事实');
  const provenance = [
    ['冻结清单 SHA-256', summary.provenance.frozen_manifest_sha256],
    ['运行索引 SHA-256', summary.provenance.run_index_sha256],
    ['正式口径', '胜 / 负 / 未检出稳定差异 / 未完成'],
  ];
  provenance.forEach((item, index) => {
    const y = 635 + index * 92;
    body += `${text(900, y, item[0], 14, 700, C.muted)}${rect(900, y + 15, 665, 48, C.pale, C.grid)}${text(920, y + 47, item[1], index < 2 ? 12 : 14, 700, index < 2 ? C.navy : C.cyan)}`;
  });
  body += `${rect(900, 910, 665, 42, C.rose, C.red)}${text(1232, 938, '“未检出稳定差异”不等同于统计等效', 14, 800, C.red, 'middle')}`;
  return shell(body, '正式结果已签核；结论仅适用于预登记域与当前冻结模型');
}

function deltaColor(value) {
  if (value === null) return C.pale;
  const strength = Math.min(Math.abs(value) / 0.2, 1);
  const target = value >= 0 ? [38, 139, 121] : [200, 79, 85];
  const base = [255, 255, 255];
  const rgb = base.map((channel, index) => Math.round(channel + (target[index] - channel) * (0.18 + strength * 0.72)));
  return `rgb(${rgb.join(',')})`;
}

function matrixPanel(comparison, x0, y0, mark, title) {
  let body = panelHeading(x0, y0, mark, title, '每格10条同轨迹配对；色彩表示加权按时交付率均值差');
  const cellW = 112; const cellH = 112; const gap = 10; const gridX = x0 + 38; const gridY = y0 + 95;
  comparison.cells.forEach((cell, index) => {
    const column = index % 6; const row = Math.floor(index / 6); const x = gridX + column * (cellW + gap); const y = gridY + row * (cellH + gap);
    const fill = deltaColor(cell.mean_delta); const ink = Math.abs(cell.mean_delta ?? 0) > 0.12 ? C.white : C.ink;
    body += `${rect(x, y, cellW, cellH, fill, C.white, 2, 2)}${text(x + 8, y + 23, cell.cell_id, 11, 700, ink)}${text(x + cellW / 2, y + 63, number(cell.mean_delta, 3), 18, 800, ink, 'middle')}${text(x + cellW / 2, y + 88, `n=${cell.n} · miss=${cell.missing}`, 10, 600, ink, 'middle')}`;
  });
  const verdictColorValue = verdictColor(comparison.formal_verdict);
  body += `${rect(gridX, gridY + 3 * (cellH + gap) + 12, 722, 64, C.pale, verdictColorValue, 1.5)}${text(gridX + 20, gridY + 3 * (cellH + gap) + 40, `正式结论：${comparison.formal_verdict}`, 16, 800, verdictColorValue)}${text(gridX + 700, gridY + 3 * (cellH + gap) + 40, `总体 Δ=${number(comparison.overall.mean_delta)}　95% CI ${comparison.overall.ci95 ? `[${number(comparison.overall.ci95[0])}, ${number(comparison.overall.ci95[1])}]` : '—'}`, 12, 700, C.muted, 'end')}`;
  return body;
}

function matrixFigure(summary) {
  let body = matrixPanel(summary.comparisons['learned-edf'], 55, 70, '(a)', 'Learned − EDF：18工况配对差值');
  body += matrixPanel(summary.comparisons['learned-value'], 865, 70, '(b)', 'Learned − Value：18工况配对差值');
  body += `${text(850, 940, '−0.20', 12, 600, C.muted, 'end')}`;
  for (let index = 0; index < 10; index += 1) body += rect(860 + index * 35, 922, 35, 22, deltaColor(-0.2 + index * (0.4 / 9)), 'none', 0, 0);
  body += `${text(1220, 940, '+0.20', 12, 600, C.muted)}${text(1040, 974, '均值差 Δ（Learned − baseline）', 13, 700, C.muted, 'middle')}`;
  return shell(body, '工况格按冻结summary顺序展示；缺失不补零，负值与零增益原样保留', 102, 1020);
}

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 2) {
    if (!argv[index]?.startsWith('--') || argv[index + 1] === undefined) fail('用法：--input summary.json --output output_dir');
    args[argv[index].slice(2)] = argv[index + 1];
  }
  if (!args.input || !args.output) fail('用法：--input summary.json --output output_dir');
  return args;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const inputPath = path.resolve(args.input); const outputPath = path.resolve(args.output);
  if (fs.existsSync(outputPath)) fail('输出目录必须不存在，禁止覆盖既有材料证据');
  const sourceBytes = fs.readFileSync(inputPath); const summary = validate(JSON.parse(sourceBytes.toString('utf8')));
  const figures = [
    ['B-F07_正式策略比较总览.svg', overviewFigure(summary)],
    ['B-F08_十八工况配对差值矩阵.svg', matrixFigure(summary)],
  ];
  fs.mkdirSync(outputPath, { recursive: false });
  for (const [name, svg] of figures) fs.writeFileSync(path.join(outputPath, name), svg, 'utf8');
  const sourceHash = crypto.createHash('sha256').update(sourceBytes).digest('hex');
  const manifest = {
    schema_version: 'formal-materials-pack-v1', generated_at: new Date().toISOString(), result_signoff: summary.result_signoff,
    source_file: path.basename(inputPath), source_sha256: sourceHash, data_scope: summary.data_scope,
    figures: figures.map(([file, svg]) => ({ file, sha256: crypto.createHash('sha256').update(svg).digest('hex'), master_format: 'SVG', width: '170mm' })),
  };
  fs.writeFileSync(path.join(outputPath, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  fs.writeFileSync(path.join(outputPath, 'CAPTIONS.md'), `# 正式结果图件图注\n\n## B-F07 正式策略比较总览\n\n图展示formal_v2冻结范围内的运行完整度、两项预登记主比较、推理证据和来源哈希。误差线为95%置信区间；结论适用范围以签核JSON为准。\n\n## B-F08 十八工况配对差值矩阵\n\n图按冻结顺序展示18个工况格的Learned相对EDF和Value的加权按时交付率配对均值差。正值表示Learned较高，负值表示Learned较低；缺失不补零。“未检出稳定差异”不等同于统计等效。\n\n来源SHA-256：\`${sourceHash}\`\n`, 'utf8');
  process.stdout.write(`generated ${figures.length} signed formal-result SVG masters in ${outputPath}\n`);
}

try { main(); } catch (error) { process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`); process.exitCode = 1; }
