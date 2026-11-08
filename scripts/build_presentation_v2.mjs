import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';
import { MAIN_SLIDES, BACKUP_SLIDES } from './presentation_story_v2.mjs';
import { RENDERERS, ROOT } from './presentation_layouts_v2.mjs';

export const BUILD = path.join(ROOT, '.presentation-build', 'v2');
export const MAIN_TALK_SLIDE_COUNT = 15;
export const FINAL_DECK_PATH = path.join(ROOT, 'docs', 'presentation', 'generated', '星地智调_主讲稿_v2_高信息密度版.pptx');

export function validateStoryResources(slides) {
  const manifest = [];
  for (const slide of slides) {
    const renderer = RENDERERS[slide.layout];
    if (typeof renderer !== 'function') throw new Error(`Unregistered layout for ${slide.id}: ${slide.layout}`);
    for (const evidence of slide.evidence) {
      const absolutePath = path.resolve(ROOT, evidence.asset);
      if (!fs.existsSync(absolutePath)) throw new Error(`Missing evidence asset for ${slide.id}: ${absolutePath}`);
      manifest.push({ slide: slide.id, type: evidence.type, panel: evidence.panel, asset: evidence.asset, absolutePath });
    }
  }
  return manifest;
}

export function outputPaths(mode = 'main') {
  const count = mode === 'main' ? 15 : 20;
  return {
    buildDir: BUILD,
    slidePngs: Array.from({ length: count }, (_, index) => path.join(BUILD, `slide-${String(index + 1).padStart(2, '0')}.png`)),
    montage: path.join(BUILD, mode === 'main' ? 'main-montage.png' : 'full-montage.png'),
    manifest: path.join(BUILD, `${mode}-manifest.json`),
  };
}

async function buildSlides(presentation, slides, offset = 0) {
  for (const [index, spec] of slides.entries()) {
    const renderer = RENDERERS[spec.layout];
    if (!renderer) throw new Error(`Unregistered layout for ${spec.id}: ${spec.layout}`);
    const slide = presentation.slides.add();
    const absolutePage = offset + index + 1;
    const pageLabel = spec.id.startsWith('B') ? `答辩备查 ${spec.id}` : String(absolutePage).padStart(2, '0');
    await renderer({ slide, spec, pageLabel });
  }
}

export async function buildMainDeck(presentation) {
  validateStoryResources(MAIN_SLIDES);
  await buildSlides(presentation, MAIN_SLIDES, 0);
  if (presentation.slides.items.length !== 15) throw new Error(`Expected 15 main slides, got ${presentation.slides.items.length}`);
}

export async function buildFullDeck(presentation) {
  validateStoryResources(MAIN_SLIDES);
  validateStoryResources(BACKUP_SLIDES);
  await buildSlides(presentation, MAIN_SLIDES, 0);
  await buildSlides(presentation, BACKUP_SLIDES, MAIN_SLIDES.length);
  if (presentation.slides.items.length !== 20) throw new Error(`Expected 20 full-deck slides, got ${presentation.slides.items.length}`);
}

async function writeBlob(file, blob) {
  await fsp.writeFile(file, new Uint8Array(await blob.arrayBuffer()));
}

export async function renderPreviews(presentation, mode = 'main') {
  const paths = outputPaths(mode);
  await fsp.mkdir(paths.buildDir, { recursive: true });
  if (presentation.slides.items.length !== paths.slidePngs.length) {
    throw new Error(`Preview count mismatch: expected ${paths.slidePngs.length}, got ${presentation.slides.items.length}`);
  }
  for (const [index, slide] of presentation.slides.items.entries()) {
    await writeBlob(paths.slidePngs[index], await presentation.export({ slide, format: 'png', scale: 1 }));
  }
  await writeBlob(paths.montage, await presentation.export({ format: 'png', montage: true }));
  const storySlides = mode === 'main' ? MAIN_SLIDES : [...MAIN_SLIDES, ...BACKUP_SLIDES];
  const manifest = {
    schema: 'presentation-v2-manifest',
    generatedAt: '2026-11-08',
    mode,
    slideCount: presentation.slides.items.length,
    mainTalkSlideCount: MAIN_TALK_SLIDE_COUNT,
    slides: storySlides.map(({ id, section, title, layout, status, evidence }) => ({ id, section, title, layout, status, evidence })),
    resources: validateStoryResources(storySlides).map(({ absolutePath: _absolutePath, ...item }) => item),
  };
  await fsp.writeFile(paths.manifest, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  return paths;
}

export async function buildFullPreview() {
  const presentation = Presentation.create({ slideSize: { width: 1600, height: 900 } });
  await buildFullDeck(presentation);
  return { presentation, paths: await renderPreviews(presentation, 'full') };
}

export async function exportFinalDeck() {
  const { presentation, paths } = await buildFullPreview();
  await fsp.mkdir(path.dirname(FINAL_DECK_PATH), { recursive: true });
  const draftPath = path.join(BUILD, '星地智调_主讲稿_v2_draft.pptx');
  await (await PresentationFile.exportPptx(presentation)).save(draftPath);
  if (fs.existsSync(FINAL_DECK_PATH)) {
    throw new Error(`Refusing to overwrite existing final deck: ${FINAL_DECK_PATH}`);
  }

  const skillDir = process.env.CODEX_PRESENTATION_SKILL_DIR;
  const runtimePython = process.env.CODEX_RUNTIME_PYTHON;
  let validation = { status: 'skipped', reason: 'Presentation finalizer environment is not configured.' };
  if (skillDir && runtimePython) {
    const { finalizePresentation } = await import(pathToFileURL(path.join(skillDir, 'container_tools', 'artifact_tool_utils.mjs')).href);
    const receiptPath = path.join(BUILD, '星地智调_主讲稿_v2.validation.json');
    validation = await finalizePresentation({
      workspaceDir: ROOT,
      candidatePath: draftPath,
      finalPath: FINAL_DECK_PATH,
      pythonExecutable: runtimePython,
      integrityValidatorPath: path.join(skillDir, 'container_tools', 'inspect_presentation_package_integrity.py'),
      layoutValidatorPath: path.join(skillDir, 'container_tools', 'inspect_presentation_layout_geometry.py'),
      layoutArgs: ['--expected-slide-size-emu', '15240000,8572500', '--validate-heading-fit'],
      explicitTotalSlideCount: 20,
      requiredNativeTableOwnerSlides: [],
      requiredNativeChartOwnerSlides: [],
      fontPolicy: { basis: 'design', families: ['Microsoft YaHei'] },
      verifyArtifactToolImport: true,
      receiptPath,
    });
  } else {
    await fsp.copyFile(draftPath, FINAL_DECK_PATH);
  }
  return { final: FINAL_DECK_PATH, draft: draftPath, paths, validation };
}

export async function buildMainPreview() {
  const presentation = Presentation.create({ slideSize: { width: 1600, height: 900 } });
  await buildMainDeck(presentation);
  return renderPreviews(presentation, 'main');
}

function parseArgs(argv) {
  const modeIndex = argv.indexOf('--mode');
  const mode = modeIndex >= 0 ? argv[modeIndex + 1] : 'main';
  return { mode, previewOnly: argv.includes('--preview-only'), exportDeck: argv.includes('--export') };
}

async function main() {
  const { mode, previewOnly, exportDeck } = parseArgs(process.argv.slice(2));
  if (mode === 'main' && previewOnly) {
    const paths = await buildMainPreview();
    console.log(JSON.stringify({ slides: 15, paths }, null, 2));
    return;
  }
  if (mode === 'full' && previewOnly) {
    const { paths } = await buildFullPreview();
    console.log(JSON.stringify({ slides: 20, paths }, null, 2));
    return;
  }
  if (mode === 'full' && exportDeck) {
    console.log(JSON.stringify(await exportFinalDeck(), null, 2));
    return;
  }
  throw new Error('Use --mode main|full with --preview-only, or --mode full --export');
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
