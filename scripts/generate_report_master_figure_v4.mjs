import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DATA_PATH = path.join(ROOT, 'docs', 'figures', 'source_data', 'v4_master_figure.json');
const OUT = path.join(ROOT, 'docs', 'figures', 'generated', 'v4', 'report');
const PREVIEW = path.join(OUT, 'previews');
const data = JSON.parse(fs.readFileSync(DATA_PATH, 'utf8'));
fs.mkdirSync(PREVIEW, { recursive: true });

const C = {
  ink: '#172A3A', muted: '#526575', grid: '#D7E0E6', pale: '#F5F8FA',
  navy: '#24506F', cyan: '#2B88A3', teal: '#268B79', amber: '#D58A27',
  red: '#C84F55', white: '#FFFFFF', sky: '#EAF3F7', mint: '#E9F5F1', sand: '#FCF3E4', rose: '#F9ECEC',
};
const FONT = "Arial, 'Source Han Sans SC', 'Microsoft YaHei', sans-serif";
const esc = (s) => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const t = (x, y, s, size = 18, weight = 400, fill = C.ink, anchor = 'start', extra = '') => `<text x="${x}" y="${y}" font-family="${FONT}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}" ${extra}>${esc(s)}</text>`;
const l = (x1, y1, x2, y2, stroke = C.grid, width = 1.2, dash = '') => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${width}"${dash ? ` stroke-dasharray="${dash}"` : ''}/>`;
const r = (x, y, w, h, fill = C.white, stroke = C.grid, width = 1, rx = 0) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" stroke="${stroke}" stroke-width="${width}" rx="${rx}"/>`;
const c = (x, y, rad, fill, stroke = C.white, width = 2) => `<circle cx="${x}" cy="${y}" r="${rad}" fill="${fill}" stroke="${stroke}" stroke-width="${width}"/>`;
const poly = (points, fill, stroke = 'none', width = 0) => `<polygon points="${points}" fill="${fill}" stroke="${stroke}" stroke-width="${width}"/>`;
const pathLine = (pts, stroke, width = 3, fill = 'none') => `<path d="M ${pts.map(([x,y]) => `${x} ${y}`).join(' L ')}" fill="${fill}" stroke="${stroke}" stroke-width="${width}" stroke-linejoin="round" stroke-linecap="round"/>`;
const panelTitle = (x, y, mark, title, subtitle) => `${t(x, y, mark, 23, 800)}${t(x + 48, y, title, 23, 800)}${t(x + 48, y + 28, subtitle, 14, 400, C.muted)}`;

function panelA() {
  const x = 55, y = 55, w = 780, h = 515;
  let out = `${r(x,y,w,h,C.white,C.grid,1.2,2)}${panelTitle(x+24,y+40,'(a)','健康感知星地任务场景','状态、任务与可见窗口共同定义决策上下文')}`;
  out += `${poly('150,205 198,178 246,205 222,218 222,250 174,250 174,218',C.navy)}${r(186,250,24,56,C.sky,C.navy,1.5)}${l(170,278,142,300,C.navy,2)}${l(226,278,254,300,C.navy,2)}${t(198,332,'航天器',17,700,C.navy,'middle')}`;
  out += `${pathLine([[250,230],[370,272],[490,292]],C.cyan,3)}${pathLine([[250,246],[370,300],[490,320]],C.cyan,1.5)}${t(368,246,'星地链路',14,700,C.cyan,'middle')}`;
  out += `${poly('485,337 535,312 585,337',C.teal)}${r(505,337,60,48,C.mint,C.teal,1.5)}${l(535,312,535,270,C.teal,2)}${c(535,265,5,C.teal)}${t(535,413,'地面网关',17,700,C.teal,'middle')}`;
  out += `${r(635,150,160,78,C.mint,C.teal,1.4,3)}${t(654,179,'健康下界',14,600,C.muted)}${t(654,211,'9.0 Wh',25,800,C.teal)}${r(635,244,160,78,C.sand,C.amber,1.4,3)}${t(654,273,'待传任务',14,600,C.muted)}${t(654,305,'T1 · 1024 B',22,800,C.amber)}${r(635,338,160,78,C.rose,C.red,1.4,3)}${t(654,367,'业务截止',14,600,C.muted)}${t(654,399,'4.0 s',22,800,C.red)}`;
  const ax0 = 120, ax1 = 780, ay = 500, sx = (v) => ax0 + (ax1-ax0)*v/8;
  out += `${l(ax0,ay,ax1,ay,C.ink,1.5)}${t(450,548,'仿真时间 / s',14,600,C.muted,'middle')}`;
  for (let v=0;v<=8;v+=1) out += `${l(sx(v),ay-5,sx(v),ay+5,C.ink,1)}${t(sx(v),ay+25,v,13,400,C.muted,'middle')}`;
  out += `${r(sx(0),ay-31,sx(2)-sx(0),20,C.sky,C.cyan,1,2)}${t((sx(0)+sx(2))/2,ay-16,'W1',13,700,C.cyan,'middle')}${r(sx(4),ay-31,sx(8)-sx(4),20,C.mint,C.teal,1,2)}${t((sx(4)+sx(8))/2,ay-16,'W2',13,700,C.teal,'middle')}${l(sx(4),ay-62,sx(4),ay+7,C.red,2,'5 4')}${t(sx(4)-5,ay-68,'deadline',12,700,C.red,'end')}`;
  return out;
}

function panelB() {
  const x = 865, y = 55, w = 780, h = 515;
  let out = `${r(x,y,w,h,C.white,C.grid,1.2,2)}${panelTitle(x+24,y+40,'(b)','候选价值排序与安全可行域','冻结教师样本 r4_00；分数仅表示该样本的离线教师效用')}`;
  const left=1030, right=1510, top=175, row=61, scoreX=(v)=>left+(right-left)*v;
  out += `${t(1595,122,'OPTIMAL · gap = 0.0',12,700,C.navy,'end')}`;
  for(let v=0;v<=1.0001;v+=0.25) out += `${l(scoreX(v),top-15,scoreX(v),top+row*5-18,C.grid,1)}${t(scoreX(v),top-25,v.toFixed(2),12,400,C.muted,'middle')}`;
  data.teacher.candidates.forEach((d,i)=>{
    const yy=top+i*row;
    out += `${t(left-18,yy+6,d.key,15,600,d.feasible?C.ink:C.red,'end')}${l(left,yy,right,yy,C.grid,5)}${l(left,yy,scoreX(d.score),yy,d.feasible?C.teal:C.red,8)}${c(scoreX(d.score),yy,8,d.feasible?C.teal:C.red)}${t(right+18,yy+6,d.score.toFixed(2),15,700,d.feasible?C.teal:C.red)}`;
    if(!d.feasible) out += `${l(right+54,yy-8,right+70,yy+8,C.red,2)}${l(right+70,yy-8,right+54,yy+8,C.red,2)}${t(right+80,yy+6,'不可行',13,700,C.red)}`;
  });
  out += `${t((left+right)/2,458,'离线教师效用分数',13,600,C.muted,'middle')}`;
  out += `${r(916,474,680,62,C.pale,C.grid,1,2)}${t(936,498,'裁决：',14,800,C.navy)}${t(992,498,'先由 AI/教师给出价值排序，再由通信与安全约束形成可执行集合；',14,500,C.ink)}${t(936,522,'本例 T1/fast = 1.00 且可行；T1/robust = 0.00 且被可行域剔除。',14,500,C.ink)}`;
  return out;
}

function panelC() {
  const x=55,y=600,w=1010,h=610;
  let out=`${r(x,y,w,h,C.white,C.grid,1.2,2)}${panelTitle(x+24,y+40,'(c)','ACK 丢失—超时—重传—去重事件链','签核样例的离散事件时序；阴影为可见窗口，红虚线为业务截止')}`;
  const ax0=160,ax1=1015,top=735,bottom=1125,sx=(v)=>ax0+(ax1-ax0)*v/8;
  out += `${r(sx(0),top,sx(2)-sx(0),bottom-top,C.sky,'none')}${r(sx(4),top,sx(8)-sx(4),bottom-top,C.mint,'none')}${t((sx(0)+sx(2))/2,top+24,'W1 可见',13,700,C.cyan,'middle')}${t((sx(4)+sx(8))/2,top+24,'W2 可见',13,700,C.teal,'middle')}`;
  const lanes=[['SAT→GW',790],['GW',875],['GW→SAT',960],['SAT',1045]];
  lanes.forEach(([name,yy])=>{out+=`${t(ax0-18,yy+5,name,14,700,C.muted,'end')}${l(ax0,yy,ax1,yy,C.grid,1.2)}`;});
  for(let v=0;v<=8;v++) out+=`${l(sx(v),bottom,sx(v),bottom+6,C.ink,1)}${t(sx(v),bottom+25,v,12,400,C.muted,'middle')}`;
  out+=`${l(ax0,bottom,ax1,bottom,C.ink,1.4)}${t((ax0+ax1)/2,bottom+49,'仿真时间 / s',14,600,C.muted,'middle')}${l(sx(4),top,sx(4),bottom,C.red,2,'6 5')}${t(sx(4)-6,top+45,'deadline = 4 s',12,700,C.red,'end')}`;
  const laneY=Object.fromEntries(lanes);
  const colors={sent:C.navy,received:C.teal,lost:C.red,timeout:C.amber,duplicate:C.cyan,acked:C.teal};
  data.ack_loss.events.forEach((e,i)=>{
    const xx=sx(e.time_s), yy=laneY[e.lane], above=i%2===0;
    out+=`${c(xx,yy,9,colors[e.kind])}${l(xx,yy+(above?-10:10),xx,yy+(above?-38:42),colors[e.kind],1.3)}${t(xx,yy+(above?-48:61),e.label,13,700,colors[e.kind],'middle')}${t(xx,yy+(above?-66:79),e.time_s.toFixed(e.time_s%1?5:1)+' s',11,500,C.muted,'middle')}`;
  });
  out+=`${pathLine([[sx(0),790],[sx(1.03125),875]],C.navy,2)}${pathLine([[sx(1.03125),875],[sx(2.03125),960]],C.red,2)}${pathLine([[sx(4),790],[sx(5.03125),875]],C.navy,2)}${pathLine([[sx(5.03125),875],[sx(6.03125),960]],C.teal,2)}`;
  return out;
}

function panelD(){
  const x=1095,y=600,w=550,h=610;
  let out=`${r(x,y,w,h,C.white,C.grid,1.2,2)}${panelTitle(x+24,y+40,'(d)','能量账本与业务结果','同一 ACK 丢失样例；逐段账本累计，不外推整星能耗')}`;
  const ax0=1170,ax1=1595,top=748,bottom=985,sx=(v)=>ax0+(ax1-ax0)*v/8,sy=(v)=>bottom-(v-9.89)/(10.005-9.89)*(bottom-top);
  for(const v of [9.90,9.93,9.96,9.99]) out+=`${l(ax0,sy(v),ax1,sy(v),C.grid,1)}${t(ax0-10,sy(v)+5,v.toFixed(2),12,400,C.muted,'end')}`;
  for(let v=0;v<=8;v+=2) out+=`${l(sx(v),bottom,sx(v),bottom+5,C.ink,1)}${t(sx(v),bottom+22,v,12,400,C.muted,'middle')}`;
  out+=`${l(ax0,top,ax0,bottom,C.ink,1.4)}${l(ax0,bottom,ax1,bottom,C.ink,1.4)}${t(ax0-10,top-12,'剩余能量 / Wh',13,600,C.muted)}${t((ax0+ax1)/2,bottom+44,'仿真时间 / s',13,600,C.muted,'middle')}`;
  const pts=data.ack_loss.energy.map(p=>[sx(p.time_s),sy(p.energy_after_Wh)]);
  out+=`${pathLine(pts,C.teal,3)}${pts.map(([xx,yy])=>c(xx,yy,4,C.teal,C.white,1)).join('')}${t(sx(8)-5,sy(data.ack_loss.energy.at(-1).energy_after_Wh)-12,'9.8989 Wh',12,700,C.teal,'end')}`;
  out+=`${l(sx(1.03125),top,sx(1.03125),bottom,C.navy,1,'4 4')}${l(sx(5.03125),top,sx(5.03125),bottom,C.navy,1,'4 4')}${t(sx(1.03125),top+18,'TX₁',11,700,C.navy,'middle')}${t(sx(5.03125),top+18,'TX₂',11,700,C.navy,'middle')}`;
  const m=data.ack_loss.results;
  const cards=[['有效载荷',`${m.success_payload_bytes} B`,C.navy],['单位成功比特能耗',`${m.joule_per_success_bit.toFixed(7)} J/bit`,C.amber],['加权按时率',`${(m.weighted_on_time_rate*100).toFixed(0)}%`,C.teal],['能量违规段',`${m.energy_violation_count}`,C.teal]];
  cards.forEach((d,i)=>{const xx=1125+(i%2)*250,yy=1055+Math.floor(i/2)*70;out+=`${r(xx,yy,230,55,C.pale,C.grid,1,2)}${t(xx+14,yy+21,d[0],12,500,C.muted)}${t(xx+216,yy+39,d[1],17,800,d[2],'end')}`;});
  return out;
}

const scope=data.scope_note;
const svg=`<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="170mm" height="126mm" viewBox="0 0 1700 1260" role="img" aria-label="AI与6G星地通信闭环证据四联图">
<rect x="0" y="0" width="1700" height="1260" fill="#FFFFFF"/>
${panelA()}${panelB()}${panelC()}${panelD()}
${l(55,1232,1645,1232,C.grid,1)}${t(55,1252,scope,12,600,C.red)}${t(1645,1252,'来源：冻结教师样本 + R3 ACK-loss 签核运行包',12,500,C.muted,'end')}
</svg>`;

const name='C-F00_AI6G闭环证据主图.svg';
fs.writeFileSync(path.join(OUT,name),svg,'utf8');
await sharp(Buffer.from(svg),{density:300}).flatten({background:C.white}).png({compressionLevel:9}).toFile(path.join(PREVIEW,name.replace('.svg','.png')));
const manifest={schema_version:'report-figure-pack-v4',generated_at:'2026-11-08',status:'calibration-sample',source_contract:path.relative(ROOT,DATA_PATH).replaceAll('\\','/'),figures:[{file:name,sha256:crypto.createHash('sha256').update(svg).digest('hex'),width:'170mm',height:'126mm'}]};
fs.writeFileSync(path.join(OUT,'manifest.json'),`${JSON.stringify(manifest,null,2)}\n`,'utf8');
fs.writeFileSync(path.join(OUT,'README.md'),'# 报告科研图形 v4\n\n本目录为四联证据主图校准样板。SVG 是正式母版，PNG 仅供预览。图题与完整图注由报告 DOCX 统一排版；用户确认前不接入报告。\n','utf8');
console.log(path.join(OUT,name));
