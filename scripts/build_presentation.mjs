import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';
import { SLIDE_SPECS, THEME } from './presentation_design.mjs';

const ROOT = path.resolve(import.meta.dirname, '..');
const FIG = path.join(ROOT, 'docs', 'figures', 'generated', 'v2');
const PREVIEW = path.join(FIG, 'previews');
const BUILD = path.join(ROOT, '.presentation-build', 'v1');
const OUTPUT = path.join(ROOT, 'docs', 'presentation', 'generated');
const FINAL = path.join(OUTPUT, '星地智调_主讲稿_v1_统一特色背景版.pptx');
const SKILL_DIR = process.env.CODEX_PRESENTATION_SKILL_DIR;
const RUNTIME_PYTHON = process.env.CODEX_RUNTIME_PYTHON;
const FONT = 'Microsoft YaHei';

const C = Object.freeze({
  navy: '#06111D',
  panel: '#0D2237',
  cyan: '#6ED6E6',
  blue: '#4F8FEA',
  teal: '#4FC3A1',
  amber: '#F4B84A',
  coral: '#EF6A6A',
  white: '#F5F8FB',
  ink: '#152536',
  muted: '#A8B8C8',
  steel: '#72879C',
});

const BODY = Object.freeze({ top: 208, bottom: 818, evidenceWidth: 1080, insightWidth: 336, gap: 24 });

const evidenceSlides = [
  {
    section: '01  场景需求',
    title: '有限窗口内，任务价值与链路资源同时变化',
    figure: 'C-F01_6G星地业务冲突.png',
    alt: '有限窗口内多个任务争抢星地链路',
    insightTitle: '业务矛盾',
    insightBody: '窗口长度、链路速率和能源储备共同限制可发送字节。\n\n调度目标不是“尽量多传”，而是在可执行边界内优先保障高价值信息。',
    accent: C.cyan,
    side: 'right',
    footer: '场景边界：合成星地环境验证，不宣称真实在轨部署',
  },
  {
    section: '01  场景需求',
    title: '固定规则只能覆盖已知工况',
    figure: 'B-F03_开发期18工况规则矩阵.png',
    alt: '开发期18种工况下的规则表现矩阵',
    insightTitle: '为什么需要智能评分',
    insightBody: '固定阈值适合稳定边界，但面对窗口、能量和任务结构联动变化时，优先级容易失真。\n\nAI负责估计相对价值，约束层继续负责安全执行。',
    accent: C.amber,
    side: 'left',
    footer: '开发期工况用于暴露规则局限，不等同于正式实验结论',
  },
  {
    section: '02  方案设计',
    title: '三层架构分离价值判断与安全执行',
    figure: 'C-F02_三层执行架构六步闭环.png',
    alt: '三层执行架构与六步业务闭环',
    insightTitle: '职责边界',
    insightBody: '健康估计提供任务状态。\n\nAI评分器只输出候选价值。\n\n确定性解码器检查窗口、数据位置、能源和协议约束，再生成可执行动作。',
    accent: C.teal,
    side: 'right',
    footer: 'AI改变排序，不改变安全边界',
  },
  {
    section: '02  方案设计',
    title: 'AI 与 6G 状态形成双向闭环',
    figure: 'C-F03_AI与6G双向耦合.png',
    alt: 'AI价值排序与6G状态约束的双向耦合',
    insightTitle: '切合点',
    insightBody: '6G链路状态进入评分过程，影响任务的时效和可达性。\n\nAI输出反向决定发送对象、时机与模式。\n\n两者通过执行反馈持续更新，而不是简单“AI加通信”。',
    accent: C.cyan,
    side: 'left',
    footer: '核心闭环：链路状态输入，价值排序决策，执行结果反馈',
  },
  {
    section: '03  智能评分',
    title: '评分器只学习可公开观测的信息',
    figure: 'A-F01_公开特征教师标注学习评分器.png',
    alt: '公开特征教师标注与学习评分器链路',
    insightTitle: '训练与在线分工',
    insightBody: '离线阶段用冻结教师规则生成监督信号。\n\n在线阶段只读取当前可观测特征，并在毫秒级给出候选排序。\n\n未来结果仅用于事后评估。',
    accent: C.blue,
    side: 'right',
    footer: '证据要求：模型哈希、训练配置、输入边界与错误回退均可追溯',
  },
  {
    section: '04  证据闭环',
    title: '每一项结论都能追溯到运行证据',
    figure: 'C-F04_证据链.png',
    alt: '从运行事实到材料呈现的证据链',
    insightTitle: '材料可信度',
    insightBody: '运行包记录配置、版本和事件。\n\n统计脚本把运行事实转换为比较结果。\n\n报告、PPT和前端只读取已签核结论，避免材料口径漂移。',
    accent: C.teal,
    side: 'left',
    footer: '原则：运行事实先冻结，材料表达后生成',
  },
  {
    section: '05  实验设计',
    title: '正式实验采用冻结策略与配对比较',
    figure: 'B-F04_正式实验公平比较协议.png',
    alt: '正式实验因素矩阵与配对比较协议',
    insightTitle: '公平比较',
    insightBody: '三种策略共享相同环境、种子和候选轨迹。\n\n配对统计减少环境随机性干扰。\n\n正式运行前冻结模型、配置与指标口径。',
    accent: C.blue,
    side: 'right',
    footer: '正式运行必须经过 A/B/C 三方签核',
  },
  {
    section: '05  正式结果',
    title: '正式结果等待三方签核',
    figure: 'B-F05_正式结果未完成模板.png',
    alt: '正式结果未完成安全占位页',
    insightTitle: '当前口径：未完成',
    insightBody: '本页不展示开发期收益，也不预设“胜”或“等效”。\n\n正式运行完成后，按胜、等效、负、未完成四档之一替换本页。',
    accent: C.amber,
    side: 'left',
    footer: '未经三方签核，不得写入收益、提升率或统计结论',
    status: '未完成',
  },
  {
    section: '06  协议可靠性',
    title: '确认丢失不会造成重复入账',
    figure: 'B-F01_发送确认重传去重时序.png',
    alt: '确认丢失后的超时重传与接收端去重',
    insightTitle: '工程可执行性',
    insightBody: '发送端超时后允许重传。\n\n接收端使用任务标识与分片序号去重。\n\n协议状态进入运行证据，便于定位丢包、重传和确认异常。',
    accent: C.teal,
    side: 'right',
    footer: '可靠性来自协议状态机，不依赖模型猜测',
  },
  {
    section: '06  信息边界',
    title: '未来真值不进入在线评分',
    figure: 'A-F05_公开信息与真值隔离.png',
    alt: '评分器公开输入与未来真值隔离边界',
    insightTitle: '防止信息泄漏',
    insightBody: '在线输入只包含决策时刻已经可见的信息。\n\n未来退化、最终收益和后验标签只进入离线评估。\n\n同一边界同时约束训练、仿真和材料表述。',
    accent: C.blue,
    side: 'left',
    footer: '证据边界：公开特征在线可用，未来真值仅用于评估',
  },
  {
    section: '07  落地路线',
    title: '验证路线从合成环境逐步走向受控试点',
    figure: 'C-F05_三阶段落地路线.png',
    alt: '从合成验证到受控试点的三阶段路线',
    insightTitle: '可落地边界',
    insightBody: '当前完成合成环境中的闭环验证。\n\n下一阶段接入半实物链路与真实遥测格式。\n\n最终在受控窗口开展影子运行，再决定是否进入业务试点。',
    accent: C.amber,
    side: 'right',
    footer: '不跨越成熟度：先验证，再联调，最后受控试点',
  },
];

async function imageBytes(file) {
  const data = await fs.readFile(file);
  return data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
}

function addText(slide, text, position, style = {}) {
  try {
    const shape = slide.shapes.add({
      geometry: 'textbox',
      position,
      text: { text },
      fill: 'none',
      line: { fill: 'none', width: 0 },
    });
    shape.text.style = { typeface: FONT, color: C.white, fontSize: 24, ...style };
    return shape;
  } catch (error) {
    console.error('addText failed', { text, position, style });
    throw error;
  }
}

function addShape(slide, geometry, position, fill, line = { fill: 'none', width: 0 }, shadow) {
  try {
    return slide.shapes.add({ geometry, position, fill, line, ...(shadow ? { shadow } : {}) });
  } catch (error) {
    console.error('addShape failed', { geometry, position, fill, line, shadow });
    throw error;
  }
}

async function addImage(slide, file, position, fit = 'cover', alt = '') {
  slide.images.add({
    blob: await imageBytes(file),
    contentType: 'image/png',
    alt,
    fit,
    position,
  });
}

async function addThemeBackground(slide, { overlay = 48, focus = 'body' } = {}) {
  slide.background.fill = C.navy;
  await addImage(slide, path.join(ROOT, THEME.backgroundAsset), { left: 0, top: 0, width: 1600, height: 900 }, 'cover', '卫星、地球弧面与通信光链项目主题背景');
  const fill = focus === 'hero'
    ? 'linear(90deg, #06111D/94 0%, #06111D/68 43%, #06111D/10 100%)'
    : `linear(180deg, #06111D/${Math.min(overlay + 18, 86)} 0%, #0B213D/${overlay} 100%)`;
  addShape(slide, 'rect', { left: 0, top: 0, width: 1600, height: 900 }, fill);
}

function addPageHeader(slide, section, title, page) {
  addText(slide, '星地智调  |  面向 6G 星地融合的健康感知智能通信调度', { left: 72, top: 28, width: 760, height: 28 }, { fontSize: 12, color: C.muted });
  addText(slide, section, { left: 72, top: 76, width: 300, height: 34 }, { fontSize: 17, bold: true, color: C.cyan });
  addText(slide, title, { left: 72, top: 112, width: 1380, height: 66 }, { fontSize: 36, bold: true });
  addShape(slide, 'rect', { left: 72, top: 184, width: 1456, height: 2 }, 'linear(90deg, #6ED6E6 0%, #4F8FEA/70 55%, #4F8FEA/0 100%)');
  addText(slide, String(page).padStart(2, '0'), { left: 1470, top: 44, width: 58, height: 28 }, { fontSize: 13, bold: true, color: C.muted, alignment: 'right' });
}

function addEvidenceCard(slide, side) {
  const left = side === 'left' ? 448 : 72;
  addShape(slide, 'roundRect', { left, top: BODY.top, width: BODY.evidenceWidth, height: 610 }, '#F7F9FC/98', { fill: '#FFFFFF/30', width: 1 }, 'shadow-md');
  return { left: left + 18, top: BODY.top + 18, width: BODY.evidenceWidth - 36, height: 574 };
}

function addInsightPanel(slide, { side, insightTitle, insightBody, accent, footer, status }) {
  const left = side === 'left' ? 72 : 1176;
  addShape(slide, 'roundRect', { left, top: 240, width: BODY.insightWidth, height: 472 }, '#0B1E31/90', { fill: `${accent}/80`, width: 1.5 }, 'shadow-md');
  addShape(slide, 'rect', { left: left + 24, top: 268, width: 7, height: 96 }, accent);
  if (status) {
    addShape(slide, 'roundRect', { left: left + 48, top: 268, width: 150, height: 34 }, '#F4B84A/18', { fill: C.amber, width: 1 });
    addText(slide, status, { left: left + 65, top: 274, width: 116, height: 22 }, { fontSize: 14, bold: true, color: C.amber, alignment: 'center' });
  }
  addText(slide, insightTitle, { left: left + 48, top: status ? 320 : 274, width: 252, height: 72 }, { fontSize: 24, bold: true, color: accent });
  addText(slide, insightBody, { left: left + 48, top: status ? 405 : 370, width: 248, height: 246 }, { fontSize: 18, color: C.white });
  addText(slide, footer, { left: 76, top: 846, width: 1320, height: 24 }, { fontSize: 11, color: C.muted });
}

async function addEvidenceSlide(presentation, config, page) {
  const slide = presentation.slides.add();
  await addThemeBackground(slide, { overlay: 46 });
  addPageHeader(slide, config.section, config.title, page);
  const frame = addEvidenceCard(slide, config.side);
  await addImage(slide, path.join(PREVIEW, config.figure), frame, 'contain', config.alt);
  addInsightPanel(slide, config);
}

async function addCover(presentation) {
  const slide = presentation.slides.add();
  await addThemeBackground(slide, { overlay: 22, focus: 'hero' });
  addText(slide, '人工智能 + 6G 青年创新创业专项赛', { left: 92, top: 126, width: 640, height: 38 }, { fontSize: 18, bold: true, color: C.cyan });
  addText(slide, '星地智调', { left: 88, top: 214, width: 600, height: 96 }, { fontSize: 62, bold: true });
  addText(slide, '面向 6G 星地融合的\n健康感知智能通信调度', { left: 92, top: 346, width: 600, height: 132 }, { fontSize: 34, bold: true });
  addShape(slide, 'rect', { left: 92, top: 525, width: 86, height: 5 }, C.cyan);
  addText(slide, 'AI 判断信息价值，确定性约束层保证安全执行', { left: 92, top: 558, width: 650, height: 54 }, { fontSize: 21, color: C.white });
  addText(slide, '场景设计赛道  |  合成环境闭环验证', { left: 92, top: 808, width: 500, height: 26 }, { fontSize: 13, color: C.muted });
}

async function addUrgency(presentation) {
  const slide = presentation.slides.add();
  await addThemeBackground(slide, { overlay: 42 });
  addPageHeader(slide, '01  场景需求', '空天地一体化扩大覆盖，但没有消除星上资源矛盾', 2);
  addShape(slide, 'roundRect', { left: 72, top: 232, width: 920, height: 500 }, '#0B1E31/84', { fill: '#6ED6E6/35', width: 1 }, 'shadow-md');
  const facts = [
    ['间歇可见', '任务只能在可见窗口内下传，窗口长度与有效速率持续变化。', C.cyan],
    ['能源共享', '通信、计算和平台运行共享有限能源，动作必须守住储备线。', C.teal],
    ['价值分层', '健康异常、周期状态和历史数据具有不同期限与业务价值。', C.amber],
  ];
  facts.forEach(([title, body, color], index) => {
    const top = 278 + index * 132;
    addText(slide, String(index + 1).padStart(2, '0'), { left: 112, top, width: 52, height: 34 }, { fontSize: 17, bold: true, color });
    addText(slide, title, { left: 184, top: top - 4, width: 220, height: 42 }, { fontSize: 25, bold: true });
    addText(slide, body, { left: 420, top: top - 2, width: 510, height: 62 }, { fontSize: 18, color: C.muted });
    if (index < facts.length - 1) addShape(slide, 'rect', { left: 112, top: top + 84, width: 820, height: 1 }, '#6ED6E6/22');
  });
  addShape(slide, 'roundRect', { left: 1040, top: 314, width: 464, height: 300 }, '#F7F9FC/94', { fill: '#FFFFFF/28', width: 1 }, 'shadow-md');
  addText(slide, '调度问题', { left: 1092, top: 360, width: 360, height: 46 }, { fontSize: 22, bold: true, color: C.blue });
  addText(slide, '有限窗口内，应该发送什么信息，选择何时发送，并采用何种传输模式？', { left: 1092, top: 438, width: 350, height: 126 }, { fontSize: 26, bold: true, color: C.ink });
  addText(slide, '来源：[1] IMT-2030(6G)推进组，《6G总体愿景与潜在关键技术》，2021，第22—23页。', { left: 76, top: 846, width: 1160, height: 24 }, { fontSize: 11, color: C.muted });
}

async function addConstraints(presentation) {
  const slide = presentation.slides.add();
  await addThemeBackground(slide, { overlay: 48 });
  addPageHeader(slide, '03  安全执行', 'AI 可以调整排序，安全边界不随模型变化', 8);
  addShape(slide, 'roundRect', { left: 72, top: 222, width: 1080, height: 596 }, '#F7F9FC/97', { fill: '#FFFFFF/30', width: 1 }, 'shadow-md');
  const rows = [
    ['01', '窗口可见', '动作只能落在当前可用窗口内'],
    ['02', '数据位置', '只发送星上已存在且仍有剩余字节的数据块'],
    ['03', '单在途协议', '未完成确认前不启动冲突传输'],
    ['04', '能源储备', '执行后的能量下界不得低于储备线'],
    ['05', '字节配额', '发送量受速率、剩余载荷和协议开销共同限制'],
  ];
  rows.forEach(([number, title, body], index) => {
    const top = 267 + index * 100;
    addText(slide, number, { left: 116, top, width: 52, height: 34 }, { fontSize: 16, bold: true, color: C.blue });
    addText(slide, title, { left: 192, top: top - 5, width: 220, height: 42 }, { fontSize: 23, bold: true, color: C.ink });
    addText(slide, body, { left: 430, top, width: 660, height: 44 }, { fontSize: 17, color: '#50657A' });
    if (index < rows.length - 1) addShape(slide, 'rect', { left: 116, top: top + 63, width: 980, height: 1 }, '#B7C7D6/60');
  });
  addShape(slide, 'roundRect', { left: 1184, top: 270, width: 336, height: 438 }, '#0B1E31/90', { fill: '#F4B84A/75', width: 1.5 }, 'shadow-md');
  addText(slide, '受控回退', { left: 1228, top: 314, width: 244, height: 50 }, { fontSize: 27, bold: true, color: C.amber });
  addText(slide, '模型缺失或损坏\n输入出现非有限值\n推理超时或越界\n候选全部不可执行', { left: 1228, top: 390, width: 244, height: 188 }, { fontSize: 19, color: C.white });
  addText(slide, '回退到冻结规则，并保留原因码和事件证据。', { left: 1228, top: 610, width: 244, height: 68 }, { fontSize: 18, bold: true, color: C.teal });
  addText(slide, '项目证据：约束解码、错误边界测试与三方验收记录。', { left: 76, top: 846, width: 980, height: 24 }, { fontSize: 11, color: C.muted });
}

async function addEnding(presentation) {
  const slide = presentation.slides.add();
  await addThemeBackground(slide, { overlay: 18, focus: 'hero' });
  addText(slide, '星地智调', { left: 92, top: 224, width: 560, height: 88 }, { fontSize: 58, bold: true });
  addText(slide, '让有限的星地连接\n优先承载更重要的信息', { left: 92, top: 354, width: 610, height: 136 }, { fontSize: 35, bold: true });
  addShape(slide, 'rect', { left: 92, top: 548, width: 86, height: 5 }, C.cyan);
  addText(slide, 'AI 面向链路状态进行价值排序，确定性约束层负责执行安全。', { left: 92, top: 584, width: 670, height: 62 }, { fontSize: 20, color: C.white });
  addText(slide, '感谢聆听', { left: 92, top: 794, width: 260, height: 38 }, { fontSize: 18, bold: true, color: C.teal });
}

async function main() {
  await fs.mkdir(BUILD, { recursive: true });
  await fs.mkdir(OUTPUT, { recursive: true });
  const presentation = Presentation.create({ slideSize: { width: 1600, height: 900 } });

  await addCover(presentation);
  await addUrgency(presentation);
  for (let index = 0; index < 5; index += 1) await addEvidenceSlide(presentation, evidenceSlides[index], index + 3);
  await addConstraints(presentation);
  for (let index = 5; index < evidenceSlides.length; index += 1) await addEvidenceSlide(presentation, evidenceSlides[index], index + 4);
  await addEnding(presentation);

  if (presentation.slides.items.length !== SLIDE_SPECS.length) throw new Error(`Expected ${SLIDE_SPECS.length} slides, got ${presentation.slides.items.length}`);

  for (const [index, slide] of presentation.slides.items.entries()) {
    const file = path.join(BUILD, `slide-${String(index + 1).padStart(2, '0')}.png`);
    const blob = await presentation.export({ slide, format: 'png', scale: 1 });
    await fs.writeFile(file, new Uint8Array(await blob.arrayBuffer()));
  }
  const montage = await presentation.export({ format: 'webp', montage: true });
  await fs.writeFile(path.join(BUILD, 'montage.webp'), new Uint8Array(await montage.arrayBuffer()));

  const draft = path.join(BUILD, '星地智调_主讲稿_v1_draft.pptx');
  await (await PresentationFile.exportPptx(presentation)).save(draft);
  await fs.rm(FINAL, { force: true });
  let validation = {
    status: 'skipped',
    reason: 'Set CODEX_PRESENTATION_SKILL_DIR and CODEX_RUNTIME_PYTHON to enable package, layout, font, and first-party import validation.',
  };
  if (SKILL_DIR && RUNTIME_PYTHON) {
    const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, 'container_tools', 'artifact_tool_utils.mjs')).href);
    const receiptPath = path.join(BUILD, '星地智调_主讲稿_v1.validation.json');
    await fs.rm(receiptPath, { force: true });
    validation = await finalizePresentation({
      workspaceDir: ROOT,
      candidatePath: draft,
      finalPath: FINAL,
      pythonExecutable: RUNTIME_PYTHON,
      integrityValidatorPath: path.join(SKILL_DIR, 'container_tools', 'inspect_presentation_package_integrity.py'),
      layoutValidatorPath: path.join(SKILL_DIR, 'container_tools', 'inspect_presentation_layout_geometry.py'),
      layoutArgs: ['--expected-slide-size-emu', '15240000,8572500', '--validate-heading-fit'],
      explicitTotalSlideCount: 15,
      requiredNativeTableOwnerSlides: [],
      requiredNativeChartOwnerSlides: [],
      fontPolicy: { basis: 'design', families: [FONT] },
      verifyArtifactToolImport: true,
      receiptPath,
    });
  } else {
    await fs.copyFile(draft, FINAL);
  }
  console.log(JSON.stringify({ slides: presentation.slides.items.length, final: FINAL, previews: BUILD, validation }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
