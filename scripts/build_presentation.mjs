import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const ROOT = path.resolve(import.meta.dirname, '..');
const FIG = path.join(ROOT, 'docs', 'figures', 'generated', 'v2');
const PREVIEW = path.join(FIG, 'previews');
const BUILD = path.join(ROOT, '.presentation-build');
const OUTPUT = path.join(ROOT, 'docs', 'presentation', 'generated');
const FINAL = path.join(OUTPUT, '星地智调_主讲稿_v0_无正式结果数字版.pptx');
const SKILL_DIR = process.env.CODEX_PRESENTATION_SKILL_DIR;
const RUNTIME_PYTHON = process.env.CODEX_RUNTIME_PYTHON;
const FONT = 'Microsoft YaHei';

const C = {
  navy: '#081421',
  graphite: '#111C2A',
  cyan: '#6ED6E6',
  teal: '#4FC3A1',
  amber: '#F4B84A',
  coral: '#EF6A6A',
  white: '#F4F7FA',
  muted: '#A7B5C4',
  steel: '#6C86A0',
};

async function imageBytes(file) {
  const data = await fs.readFile(file);
  return data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
}

function addText(slide, text, position, style = {}) {
  const shape = slide.shapes.add({
    geometry: 'textbox',
    position,
    text: { text },
    fill: 'none',
    line: { fill: 'none', width: 0 },
  });
  shape.text.style = {
    typeface: FONT,
    color: C.white,
    fontSize: 24,
    ...style,
  };
  return shape;
}

function addRect(slide, position, fill, lineFill = fill) {
  return slide.shapes.add({
    geometry: 'rect',
    position,
    fill,
    line: { fill: lineFill, width: 0 },
  });
}

async function addImage(slide, file, position = { left: 0, top: 0, width: 1600, height: 900 }, fit = 'cover', alt = '') {
  slide.images.add({
    blob: await imageBytes(file),
    contentType: 'image/png',
    alt,
    fit,
    position,
  });
}

async function addCover(presentation) {
  const slide = presentation.slides.add();
  slide.background.fill = C.navy;
  await addImage(slide, path.join(FIG, 'C-F00_星地智调主题背景_v1.png'), { left: 600, top: 0, width: 1000, height: 900 }, 'cover', '低轨卫星与星地通信链路主题背景');
  addRect(slide, { left: 0, top: 0, width: 740, height: 900 }, C.navy);
  addText(slide, '人工智能 + 6G 青年创新创业专项赛', { left: 96, top: 122, width: 560, height: 44 }, { fontSize: 18, bold: true, color: C.cyan });
  addText(slide, '星地智调', { left: 92, top: 220, width: 560, height: 106 }, { fontSize: 64, bold: true });
  addText(slide, '面向 6G 星地融合的\n健康感知智能通信调度', { left: 96, top: 360, width: 560, height: 112 }, { fontSize: 30, bold: true });
  addText(slide, 'AI 判断信息价值，约束层保证安全执行', { left: 96, top: 520, width: 570, height: 52 }, { fontSize: 21, color: C.muted });
  addText(slide, '健康感知　　智能调度　　证据闭环', { left: 96, top: 700, width: 580, height: 44 }, { fontSize: 18, bold: true, color: C.teal });
  addText(slide, '场景设计赛道 · 合成环境验证方案', { left: 96, top: 818, width: 520, height: 28 }, { fontSize: 13, color: C.muted });
}

async function addUrgency(presentation) {
  const slide = presentation.slides.add();
  slide.background.fill = C.navy;
  await addImage(slide, path.join(FIG, 'C-F00_星地智调主题背景_v1.png'), { left: 930, top: 0, width: 670, height: 900 }, 'cover', '星地通信链路主题背景');
  addRect(slide, { left: 0, top: 0, width: 1010, height: 900 }, C.navy);
  addText(slide, '6G 覆盖持续扩展，星上资源仍然稀缺', { left: 80, top: 70, width: 900, height: 80 }, { fontSize: 39, bold: true });
  addText(slide, '空天地一体化扩大连接范围，但没有消除任务调度矛盾', { left: 84, top: 160, width: 840, height: 42 }, { fontSize: 19, color: C.muted });
  const items = [
    ['间歇可见', '卫星只有在可见窗口内才能下传，窗口长度和速率随链路变化。', C.cyan],
    ['能源受限', '通信、计算与平台运行共享有限能源，调度动作必须守住储备线。', C.teal],
    ['价值不同', '健康异常、周期状态与历史数据具有不同期限、载荷和业务价值。', C.amber],
  ];
  items.forEach(([title, body, color], i) => {
    const top = 260 + i * 150;
    addRect(slide, { left: 84, top, width: 12, height: 90 }, color);
    addText(slide, title, { left: 125, top: top - 2, width: 220, height: 42 }, { fontSize: 26, bold: true, color });
    addText(slide, body, { left: 350, top: top - 2, width: 540, height: 78 }, { fontSize: 18, color: C.white });
  });
  addText(slide, '核心问题：有限窗口里，应该传什么、何时传、采用何种模式？', { left: 84, top: 748, width: 820, height: 56 }, { fontSize: 24, bold: true, color: C.cyan });
  addText(slide, '来源：[1] IMT-2030(6G)推进组，《6G总体愿景与潜在关键技术》，2021，第22—23页。', { left: 84, top: 842, width: 900, height: 25 }, { fontSize: 11, color: C.muted });
}

async function addFigureSlide(presentation, file, alt) {
  const slide = presentation.slides.add();
  slide.background.fill = '#F7F9FB';
  await addImage(slide, path.join(PREVIEW, file), { left: 0, top: 0, width: 1600, height: 900 }, 'cover', alt);
}

function addConstraints(presentation) {
  const slide = presentation.slides.add();
  slide.background.fill = C.navy;
  addText(slide, 'AI 可以调整排序，安全边界不随模型变化', { left: 80, top: 58, width: 1120, height: 72 }, { fontSize: 40, bold: true });
  addText(slide, '约束解码器逐项检查候选动作，异常时返回可解释原因并执行受控回退', { left: 84, top: 145, width: 1100, height: 42 }, { fontSize: 19, color: C.muted });
  const rows = [
    ['01', '窗口可见', '动作只能落在当前可用窗口内', C.cyan],
    ['02', '数据位置', '只发送星上已存在且仍有剩余字节的数据块', C.teal],
    ['03', '单在途协议', '未完成确认前不启动冲突传输', C.amber],
    ['04', '能源储备', '执行后的能量下界不得低于储备线', C.cyan],
    ['05', '字节配额', '发送量受窗口速率、剩余载荷和协议开销共同限制', C.teal],
  ];
  rows.forEach(([n, title, body, color], i) => {
    const top = 235 + i * 102;
    addText(slide, n, { left: 88, top, width: 56, height: 44 }, { fontSize: 21, bold: true, color });
    addText(slide, title, { left: 165, top: top - 3, width: 230, height: 48 }, { fontSize: 25, bold: true });
    addText(slide, body, { left: 430, top: top, width: 670, height: 48 }, { fontSize: 18, color: C.muted });
    addRect(slide, { left: 84, top: top + 60, width: 1010, height: 2 }, '#26384A');
  });
  addRect(slide, { left: 1170, top: 240, width: 330, height: 390 }, C.graphite);
  addText(slide, '受控回退', { left: 1210, top: 290, width: 250, height: 55 }, { fontSize: 31, bold: true, color: C.amber });
  addText(slide, '模型缺失或损坏\n输入出现非有限值\n推理超时或越界\n候选全部不可执行', { left: 1210, top: 375, width: 250, height: 190 }, { fontSize: 20, color: C.white });
  addText(slide, '回退到冻结规则，并保留原因码与事件证据', { left: 1188, top: 690, width: 300, height: 90 }, { fontSize: 20, bold: true, color: C.teal });
  addText(slide, '项目证据：后端约束解码、错误边界测试与三方验收记录。', { left: 84, top: 842, width: 900, height: 25 }, { fontSize: 11, color: C.muted });
}

async function addEnding(presentation) {
  const slide = presentation.slides.add();
  slide.background.fill = C.navy;
  await addImage(slide, path.join(FIG, 'C-F00_星地智调主题背景_v1.png'), { left: 520, top: 0, width: 1080, height: 900 }, 'cover', '单一星地通信链路主题背景');
  addRect(slide, { left: 0, top: 0, width: 720, height: 900 }, C.navy);
  addText(slide, '星地智调', { left: 96, top: 205, width: 520, height: 92 }, { fontSize: 58, bold: true });
  addText(slide, '让每一次星地连接\n更值得、更安全、更可追溯', { left: 96, top: 340, width: 570, height: 135 }, { fontSize: 34, bold: true });
  addText(slide, '价值判断　　安全执行　　证据闭环', { left: 96, top: 610, width: 560, height: 44 }, { fontSize: 19, bold: true, color: C.teal });
  addText(slide, 'AI 面向 6G 链路状态进行价值排序，确定性约束层负责执行安全。', { left: 96, top: 710, width: 570, height: 66 }, { fontSize: 18, color: C.muted });
}

async function main() {
  await fs.mkdir(BUILD, { recursive: true });
  await fs.mkdir(OUTPUT, { recursive: true });
  const presentation = Presentation.create({ slideSize: { width: 1600, height: 900 } });

  await addCover(presentation);
  await addUrgency(presentation);
  await addFigureSlide(presentation, 'C-F01_6G星地业务冲突.png', '有限窗口内多个任务争抢星地链路');
  await addFigureSlide(presentation, 'B-F03_开发期18工况规则矩阵.png', '开发期规则在18种工况下的表现矩阵');
  await addFigureSlide(presentation, 'C-F02_三层执行架构六步闭环.png', '三层执行架构和六步闭环');
  await addFigureSlide(presentation, 'C-F03_AI与6G双向耦合.png', 'AI价值排序与6G状态约束的双向耦合');
  await addFigureSlide(presentation, 'A-F01_公开特征教师标注学习评分器.png', '离线教师标注和在线学习评分器链路');
  addConstraints(presentation);
  await addFigureSlide(presentation, 'C-F04_证据链.png', '从运行事实到材料呈现的证据链');
  await addFigureSlide(presentation, 'B-F04_正式实验公平比较协议.png', '正式实验的因素矩阵与配对比较协议');
  await addFigureSlide(presentation, 'B-F05_正式结果未完成模板.png', '正式结果等待三方签核的安全占位页');
  await addFigureSlide(presentation, 'B-F01_发送确认重传去重时序.png', '确认丢失后的超时重传与接收端去重');
  await addFigureSlide(presentation, 'A-F05_公开信息与真值隔离.png', '评分器公开输入与未来真值隔离边界');
  await addFigureSlide(presentation, 'C-F05_三阶段落地路线.png', '从合成验证到受控试点的成熟度路线');
  await addEnding(presentation);

  for (const [index, slide] of presentation.slides.items.entries()) {
    const file = path.join(BUILD, `slide-${String(index + 1).padStart(2, '0')}.png`);
    const blob = await presentation.export({ slide, format: 'png', scale: 1 });
    await fs.writeFile(file, new Uint8Array(await blob.arrayBuffer()));
  }
  const montage = await presentation.export({ format: 'webp', montage: true });
  await fs.writeFile(path.join(BUILD, 'montage.webp'), new Uint8Array(await montage.arrayBuffer()));
  const draft = path.join(BUILD, '星地智调_主讲稿_v0_draft.pptx');
  await (await PresentationFile.exportPptx(presentation)).save(draft);
  await fs.rm(FINAL, { force: true });
  let validation = {
    status: 'skipped',
    reason: 'Set CODEX_PRESENTATION_SKILL_DIR and CODEX_RUNTIME_PYTHON to enable package, layout, font, and first-party import validation.',
  };
  if (SKILL_DIR && RUNTIME_PYTHON) {
    const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, 'container_tools', 'artifact_tool_utils.mjs')).href);
    const receiptPath = path.join(BUILD, '星地智调_主讲稿_v0.validation.json');
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
  console.log(JSON.stringify({ slides: presentation.slides.items.length, draft, final: FINAL, previews: BUILD, validation }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
