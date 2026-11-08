import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'docs', 'figures', 'generated', 'v3', 'report');
const PREVIEWS = path.join(OUT, 'previews');
fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(PREVIEWS, { recursive: true });

const C = {
  white: '#FFFFFF', ink: '#263442', muted: '#5E6B75', grid: '#D9E1E7',
  navy: '#24415A', teal: '#2A8C82', amber: '#D9912B', red: '#C95757',
  paleBlue: '#EEF3F6', paleTeal: '#EDF6F4', paleAmber: '#FBF4E8', paleRed: '#F9EEEE',
};
const FONT = 'Arial, Source Han Sans SC, Microsoft YaHei, sans-serif';

const esc = (value) => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const txt = (x, y, value, size = 24, weight = 400, fill = C.ink, anchor = 'start', extra = '') =>
  `<text x="${x}" y="${y}" font-family="${FONT}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}" ${extra}>${esc(value)}</text>`;
const line = (x1, y1, x2, y2, stroke = C.grid, width = 2, dash = '') =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${width}"${dash ? ` stroke-dasharray="${dash}"` : ''}/>`;
const rect = (x, y, w, h, fill = C.white, stroke = 'none', width = 1.5, rx = 0) =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" stroke="${stroke}" stroke-width="${width}" rx="${rx}"/>`;
const circle = (cx, cy, r, fill, stroke = 'none', width = 1.5) =>
  `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${width}"/>`;
const arrow = (x1, y1, x2, y2, stroke = C.navy, width = 3, dash = '') =>
  `<path d="M ${x1} ${y1} L ${x2} ${y2}" fill="none" stroke="${stroke}" stroke-width="${width}"${dash ? ` stroke-dasharray="${dash}"` : ''} marker-end="url(#arrow-${stroke.slice(1)})"/>`;
const panelLabel = (x, y, mark, title) => `${txt(x, y, mark, 25, 700)}${txt(x + 48, y, title, 25, 700)}`;
const marker = (color) => `<marker id="arrow-${color.slice(1)}" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L9,4.5 L0,9 z" fill="${color}"/></marker>`;
const shell = ({ heightMm, viewHeight, label, body }) => `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="170mm" height="${heightMm}mm" viewBox="0 0 1700 ${viewHeight}" role="img" aria-label="${esc(label)}">
<rect x="0" y="0" width="1700" height="${viewHeight}" fill="#FFFFFF"/>
<defs>${marker(C.navy)}${marker(C.teal)}${marker(C.amber)}${marker(C.red)}</defs>
${body}
</svg>
`;

function couplingFigure() {
  const body = `
${txt(70, 70, '输入状态', 20, 700, C.muted)}
${rect(70, 110, 250, 112, C.white, C.grid, 2, 6)}
${line(70, 110, 70, 222, C.navy, 8)}
${txt(100, 151, '公开观测', 25, 700)}
${txt(100, 188, '健康风险 · 能量余量', 18, 400, C.muted)}
${rect(70, 258, 250, 112, C.white, C.grid, 2, 6)}
${line(70, 258, 70, 370, C.navy, 8)}
${txt(100, 299, '任务与窗口', 25, 700)}
${txt(100, 336, '紧迫度 · 可见期 · 收益', 18, 400, C.muted)}

${arrow(320, 166, 425, 225, C.navy)}
${arrow(320, 314, 425, 255, C.navy)}
${txt(372, 198, '特征', 17, 600, C.muted, 'middle')}

${rect(425, 125, 295, 230, C.paleTeal, C.teal, 2, 6)}
${txt(572, 181, 'AI价值排序', 29, 700, C.teal, 'middle')}
${line(465, 205, 680, 205, C.grid, 2)}
${txt(465, 248, '候选任务效用评分', 20, 600)}
${txt(465, 286, '健康风险与时效权衡', 20, 600)}
${txt(465, 324, '输出：候选价值次序', 20, 600)}

${arrow(720, 240, 825, 240, C.teal)}
${txt(772, 212, '价值分数', 17, 600, C.teal, 'middle')}

${rect(825, 125, 295, 230, C.paleAmber, C.amber, 2, 6)}
${txt(972, 181, '6G可行域', 29, 700, C.amber, 'middle')}
${line(865, 205, 1080, 205, C.grid, 2)}
${txt(865, 248, '可见窗口 · 速率 · 丢失', 20, 600)}
${txt(865, 286, 'ACK义务 · 能量储备', 20, 600)}
${txt(865, 324, '输出：可执行候选集合', 20, 600)}

${arrow(1120, 240, 1225, 240, C.amber)}
${txt(1172, 212, '约束掩码', 17, 600, C.amber, 'middle')}

${rect(1225, 125, 405, 230, C.white, C.navy, 2.4, 6)}
${txt(1427, 181, '安全解码与执行', 29, 700, C.navy, 'middle')}
${line(1265, 205, 1590, 205, C.grid, 2)}
${txt(1265, 248, '在可行集合内选择最高价值候选', 20, 600)}
${txt(1265, 286, '异常、域外输入或空集合触发回退', 20, 600)}
${txt(1265, 324, '动作：robust / fast / idle', 20, 600)}

${line(425, 448, 1620, 448, C.grid, 1.5)}
${line(425, 466, 425, 512, C.teal, 7)}
${txt(457, 499, '评分—解码解耦：AI负责价值排序；规则负责通信与安全边界。', 23, 700, C.ink)}

${rect(1225, 585, 405, 104, C.white, C.grid, 1.5, 6)}
${txt(1260, 628, '链路结果', 23, 700)}
${txt(1260, 663, '送达 · 重传 · 超时 · 能耗', 18, 400, C.muted)}
<path data-role="feedback-path" d="M 1225 637 L 360 637 L 360 390 L 572 390 L 572 355" fill="none" stroke="${C.teal}" stroke-width="2.8" stroke-dasharray="10 8" marker-end="url(#arrow-${C.teal.slice(1)})"/>
${txt(790, 620, '链路结果进入下一决策周期', 18, 700, C.teal, 'middle')}
`;
  return shell({ heightMm: 74, viewHeight: 740, label: 'AI价值排序与6G可行域约束的协同决策机制', body });
}

function auditFigure() {
  const x0 = 70, panelW = 500;
  const axis = (x, y, w) => `${line(x, y, x + w, y, C.ink, 1.6)}${[0, 5, 10, 15, 20].map(v => `${line(x + w * v / 20, y - 7, x + w * v / 20, y + 7, C.ink, 1.2)}${txt(x + w * v / 20, y + 32, v, 15, 400, C.muted, 'middle')}`).join('')}`;
  let grid = '';
  const gx = 1320, gy = 228, cell = 10, gap = 4;
  for (let r = 0; r < 4; r += 1) {
    for (let c = 0; c < 20; c += 1) {
      grid += rect(gx + c * (cell + gap), gy + r * 82, cell, cell, C.white, C.grid, 1, 1);
    }
  }
  const body = `
${line(590, 80, 590, 825, C.grid, 1.5)}${line(1120, 80, 1120, 825, C.grid, 1.5)}
${panelLabel(x0, 92, '(a)', '任务标签信息量')}
${txt(x0, 142, '样本数（n = 20）', 17, 500, C.muted)}
${axis(145, 690, 360)}
${txt(145, 255, '任务动作全零', 20, 600)}
${rect(145, 285, 234, 54, C.red)}${txt(391, 321, '13/20', 22, 700, C.red)}
${txt(145, 410, '至少一个非零动作', 20, 600)}
${rect(145, 440, 126, 54, C.teal)}${txt(283, 476, '7/20', 22, 700, C.teal)}
${line(145, 548, 505, 548, C.grid, 1.5)}
${txt(145, 594, '13/20样本缺少可学习的任务动作差异', 18, 600, C.muted)}

${panelLabel(630, 92, '(b)', '最优集合辨识度')}
${txt(630, 142, '同一冻结样本集（n = 20）', 17, 500, C.muted)}
${axis(705, 690, 340)}
${txt(630, 255, 'idle位于最优集合', 20, 600)}
${line(705, 305, 1028, 305, C.grid, 5)}${circle(1028, 305, 11, C.amber)}${txt(1028, 350, '19/20', 22, 700, C.amber, 'middle')}
${txt(630, 430, '唯一非idle最优', 20, 600)}
${line(705, 480, 722, 480, C.grid, 5)}${circle(722, 480, 11, C.teal)}${txt(722, 525, '1/20', 22, 700, C.teal, 'middle')}
${line(630, 580, 1060, 580, C.grid, 1.5)}
${txt(630, 623, '高命中不等于学习策略具备有效区分能力', 18, 600, C.muted)}

${panelLabel(1160, 92, '(c)', '困难工况覆盖')}
${txt(1160, 142, '每格代表1个样本；空心表示未覆盖', 17, 500, C.muted)}
${txt(1160, 244, '低能量', 18, 600)}
${txt(1160, 326, '无窗口', 18, 600)}
${txt(1160, 408, '窗口前到期', 18, 600)}
${txt(1160, 490, '多任务冲突', 18, 600)}
${grid}
${txt(1660, 244, '0/20', 18, 700, C.red, 'end')}
${txt(1660, 326, '0/20', 18, 700, C.red, 'end')}
${txt(1660, 408, '0/20', 18, 700, C.red, 'end')}
${txt(1660, 490, '0/20', 18, 700, C.red, 'end')}
${line(1160, 580, 1605, 580, C.grid, 1.5)}
${txt(1160, 625, '旧20样本冻结包', 19, 700, C.red)}
${txt(1160, 660, '仅支持管线回归，不支持AI增益主张', 18, 500, C.muted)}
`;
  return shell({ heightMm: 84, viewHeight: 840, label: '教师标签质量与困难工况覆盖审计', body });
}

function energyFigure() {
  const body = `
${line(605, 80, 605, 830, C.grid, 1.5)}
${panelLabel(70, 92, '(a)', '发送段能耗分解')}
${txt(70, 142, '能量 / Wh', 17, 500, C.muted)}
${line(145, 680, 520, 680, C.ink, 1.6)}
${line(145, 220, 145, 680, C.ink, 1.6)}
${[0, 0.005, 0.010, 0.015, 0.020].map((v, i) => `${line(137, 680 - i * 100, 520, 680 - i * 100, i === 0 ? C.ink : C.grid, i === 0 ? 1.6 : 1)}${txt(126, 686 - i * 100, v.toFixed(3), 15, 400, C.muted, 'end')}`).join('')}
${rect(200, 280, 105, 400, C.navy)}${rect(375, 474, 105, 206, C.teal)}
${txt(252, 260, '0.0200000', 18, 700, C.navy, 'middle')}
${txt(427, 454, '0.0103125', 18, 700, C.teal, 'middle')}
${txt(252, 720, '背景段', 18, 600, C.navy, 'middle')}
${txt(427, 720, '发送段', 18, 600, C.teal, 'middle')}
${txt(252, 758, '36 W × 2 s / 3600', 15, 500, C.muted, 'middle')}
${txt(427, 758, '36 W × 1.03125 s / 3600', 15, 500, C.muted, 'middle')}
${line(200, 805, 480, 805, C.teal, 2)}${line(200, 795, 200, 815, C.teal, 2)}${line(480, 795, 480, 815, C.teal, 2)}
${txt(340, 845, '合计 ΔE = 0.0303125 Wh', 19, 700, C.teal, 'middle')}

${panelLabel(650, 92, '(b)', '事件账本累计关系')}
${txt(650, 142, '相对剩余能量', 17, 500, C.muted)}
${line(720, 220, 720, 650, C.ink, 1.6)}${line(720, 650, 1135, 650, C.ink, 1.6)}
${[260, 360, 460, 560].map(y => line(720, y, 1135, y, C.grid, 1)).join('')}
<path d="M 750 270 L 850 270 L 850 370 L 960 370 L 960 480 L 1070 480 L 1070 565 L 1120 565" fill="none" stroke="${C.teal}" stroke-width="5"/>
${line(720, 605, 1135, 605, C.red, 2, '10 8')}
${txt(1130, 595, 'Ereserve', 17, 700, C.red, 'end')}
${txt(800, 690, '背景耗能', 16, 500, C.muted, 'middle')}
${txt(905, 690, '发送', 16, 500, C.teal, 'middle')}
${txt(1040, 690, 'ACK / 超时', 16, 500, C.amber, 'middle')}
${txt(720, 225, 'E₀', 16, 600, C.muted, 'end')}
${txt(720, 375, 'E₀−ΔEbg', 16, 600, C.muted, 'end')}
${txt(720, 485, 'E₀−ΔEbg−ΔEtx', 16, 600, C.muted, 'end')}
${txt(720, 570, 'E₀−ΣΔE', 16, 600, C.muted, 'end')}

${panelLabel(1195, 92, '(c)', '实现—手算一致性')}
${txt(1195, 142, '同一发送段口径', 17, 500, C.muted)}
${txt(1195, 265, '实现值', 19, 600)}${circle(1430, 258, 10, C.navy)}${txt(1460, 266, '0.0303125 Wh', 22, 700, C.navy)}
${txt(1195, 365, '手算值', 19, 600)}${circle(1430, 358, 10, C.teal)}${txt(1460, 366, '0.0303125 Wh', 22, 700, C.teal)}
${line(1430, 258, 1430, 358, C.grid, 2, '6 6')}
${line(1195, 440, 1615, 440, C.grid, 1.5)}
${txt(1195, 500, '绝对差', 18, 500, C.muted)}${txt(1615, 500, '0 Wh', 25, 700, C.teal, 'end')}
${txt(1195, 565, '相对误差', 18, 500, C.muted)}${txt(1615, 565, '0%', 25, 700, C.teal, 'end')}
${line(1195, 640, 1615, 640, C.grid, 1.5)}
${line(1195, 665, 1195, 735, C.amber, 7)}
${txt(1220, 690, '口径边界', 18, 700, C.amber)}
${txt(1220, 728, '指定发送段，不外推为整星能耗', 18, 500, C.muted)}

`;
  return shell({ heightMm: 88, viewHeight: 880, label: '发送段能量账本分解与手算一致性校核', body });
}

const figures = [
  ['C-F03_AI与6G双向耦合_报告版.svg', couplingFigure(), 'mechanism'],
  ['A-F02_教师标签质量审计_报告版.svg', auditFigure(), 'quantitative-audit'],
  ['B-F02_能量账本校核_报告版.svg', energyFigure(), 'engineering-validation'],
];

for (const [name, svg] of figures) {
  fs.writeFileSync(path.join(OUT, name), svg, 'utf8');
  await sharp(Buffer.from(svg), { density: 300 })
    .flatten({ background: C.white })
    .png({ compressionLevel: 9 })
    .toFile(path.join(PREVIEWS, name.replace(/\.svg$/u, '.png')));
}

const manifest = {
  schema_version: 'report-figure-pack-v3', generated_at: '2026-11-08',
  scope: 'report-only', master_format: 'SVG', background: C.white,
  width: '170mm', font_stack: FONT,
  figures: figures.map(([file, svg, kind]) => ({
    file, kind, sha256: crypto.createHash('sha256').update(svg).digest('hex'),
  })),
};
fs.writeFileSync(path.join(OUT, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
fs.writeFileSync(path.join(OUT, 'README.md'), `# 报告科研图形 v3\n\n本目录是报告专用白底科研图形，不覆盖 \`generated/v2\` 的PPT展示资产。\n\n- SVG为正式母版，物理宽度170 mm；\n- 图内不放总标题、图号徽章和来源脚注；\n- 图题、图注和数据来源由报告DOCX统一排版；\n- 当前三张为风格校准样板，确认后再迁移其余报告图。\n`, 'utf8');

console.log(`generated ${figures.length} report SVG samples in ${OUT}`);
