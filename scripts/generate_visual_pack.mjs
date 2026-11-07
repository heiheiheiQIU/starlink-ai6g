import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';

const ROOT = path.resolve(import.meta.dirname, '..');
const OUT = path.join(ROOT, 'docs', 'figures', 'generated', 'v1');
fs.mkdirSync(OUT, { recursive: true });

const C = {bg:'#F7F9FB', ink:'#17232E', muted:'#617181', grid:'#DDE3E8', navy:'#17324D', cyan:'#2B9BB0', teal:'#29977D', amber:'#D49A3A', coral:'#D95C5C', steel:'#6C86A0', pale:'#E8EFF4', white:'#FFFFFF'};
const font = "'Noto Sans SC','Source Han Sans SC','Microsoft YaHei',Arial,sans-serif";
const esc = s => String(s).replace(/[&<>\"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[m]));
const T = (x,y,s,size=24,weight=400,fill=C.ink,anchor='start') => `<text x="${x}" y="${y}" font-family="${font}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}">${esc(s)}</text>`;
const L = (x1,y1,x2,y2,stroke=C.grid,w=2,dash='') => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${w}" ${dash?`stroke-dasharray="${dash}"`:''}/>`;
const R = (x,y,w,h,fill=C.white,stroke=C.grid,r=18,sw=1.5,extra='') => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" ${extra}/>`;
const CIRC = (x,y,r,fill,stroke='none',sw=0) => `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
const P = pts => pts.map(([x,y])=>`${x},${y}`).join(' ');
const arrow = (x1,y1,x2,y2,color=C.cyan,w=3,dash='') => `${L(x1,y1,x2,y2,color,w,dash)}<polygon points="${x2},${y2} ${x2-12},${y2-7} ${x2-12},${y2+7}" fill="${color}" transform="rotate(${Math.atan2(y2-y1,x2-x1)*180/Math.PI} ${x2} ${y2})"/>`;
const multiline = (x,y,lines,size=21,weight=400,fill=C.ink,gap=1.35,anchor='start') => lines.map((s,i)=>T(x,y+i*size*gap,s,size,weight,fill,anchor)).join('');
const box = (x,y,w,h,title,lines=[],accent=C.cyan) => `${R(x,y,w,h)}<rect x="${x}" y="${y}" width="8" height="${h}" rx="4" fill="${accent}"/>${T(x+28,y+42,title,25,700)}${multiline(x+28,y+76,lines,18,400,C.muted,1.4)}`;
const svg = (title,subtitle,body,footer='项目证据：已签核事实源；图形为机制/开发期结果，不代表在轨性能') => `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
<defs><filter id="shadow"><feDropShadow dx="0" dy="7" stdDeviation="12" flood-color="#17324D" flood-opacity="0.09"/></filter><linearGradient id="sea" x1="0" x2="1"><stop stop-color="#17324D"/><stop offset="1" stop-color="#2B9BB0"/></linearGradient><pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="#9AA9B7" stroke-width="2"/></pattern></defs>
<rect width="1600" height="900" fill="${C.bg}"/><rect x="0" y="0" width="1600" height="8" fill="url(#sea)"/>
${T(80,72,title,38,800)}${T(80,108,subtitle,18,400,C.muted)}${body}
${L(80,848,1520,848,C.grid,1)}${T(80,878,footer,14,400,C.muted)}
</svg>`;

const figs = {};
figs['C-F01_6G星地业务冲突.svg'] = svg('有限窗口里，多个遥测任务争抢同一条星地链路','业务场景示意＋窗口冲突时间轴',`
<path d="M80 630 Q800 350 1520 630" fill="#EAF1F6" stroke="#B8C8D6" stroke-width="3"/>
<path d="M80 630 Q800 390 1520 630" fill="none" stroke="${C.cyan}" stroke-width="2" stroke-dasharray="10 12"/>
${CIRC(1230,240,54,C.navy)}<rect x="1170" y="228" width="120" height="24" rx="8" fill="${C.white}"/><rect x="1120" y="213" width="52" height="54" fill="${C.steel}"/><rect x="1288" y="213" width="52" height="54" fill="${C.steel}"/>${T(1230,320,'低轨卫星',22,700,C.navy,'middle')}
<path d="M350 630 L390 520 L430 630 Z" fill="${C.steel}"/><ellipse cx="390" cy="515" rx="64" ry="22" fill="${C.white}" stroke="${C.navy}" stroke-width="4"/>${T(390,695,'地面网关',22,700,C.navy,'middle')}
${L(430,505,1170,270,C.cyan,8)}${T(790,360,'可见窗口内才能传输',23,700,C.cyan,'middle')}
${box(90,170,330,140,'健康异常摘要',['高价值 · 短期限 · 小载荷'],C.coral)}${box(90,330,330,140,'周期状态记录',['中价值 · 周期到达'],C.teal)}${box(90,490,330,120,'批量历史数据',['大载荷 · 可延迟'],C.amber)}
${R(520,670,930,105,C.white,C.grid,16)}${T(545,706,'时间',17,700,C.muted)}${L(610,726,1410,726,C.navy,3)}
<rect x="690" y="696" width="120" height="60" rx="10" fill="#DDF4F7"/><rect x="1010" y="696" width="170" height="60" rx="10" fill="#DDF4F7"/><rect x="1320" y="696" width="70" height="60" rx="10" fill="#DDF4F7"/>
${T(750,735,'窗口1',18,700,C.cyan,'middle')}${T(1095,735,'窗口2',18,700,C.cyan,'middle')}${T(1355,735,'窗口3',18,700,C.cyan,'middle')}
${T(635,680,'任务到达',16,600,C.coral)}${T(890,680,'期限冲突',16,600,C.amber)}${T(1210,680,'能量门槛',16,600,C.teal)}
`,'机制图；不含真实在轨数据。来源：项目业务需求与冻结仿真合同。');

figs['C-F02_四层架构六步闭环.svg'] = svg('六步闭环把健康观测变成可追溯的通信决策','四层架构不是功能堆叠，而是输入—决策—执行—证据闭环',`
${R(70,150,1460,610,'#F0F4F7',C.grid,28)}
${T(105,200,'感知层',21,800,C.teal)}${T(105,350,'智能层',21,800,C.cyan)}${T(105,500,'执行层',21,800,C.amber)}${T(105,650,'证据层',21,800,C.steel)}
${L(220,225,1480,225,C.grid,1)}${L(220,375,1480,375,C.grid,1)}${L(220,525,1480,525,C.grid,1)}
${box(250,250,300,100,'① 状态融合',['健康下界 · 任务 · 窗口'],C.teal)}${box(650,250,300,100,'② 候选构造',['任务 × robust/fast + idle'],C.cyan)}${box(1050,250,300,100,'③ AI价值评分',['输出候选分数，不直接执行'],C.cyan)}
${arrow(550,300,650,300)}${arrow(950,300,1050,300)}
${box(350,400,360,100,'④ 约束解码',['窗口 · 能量 · 协议义务'],C.amber)}${box(890,400,360,100,'⑤ 链路执行',['发送 · ACK · 重传 · 去重'],C.amber)}${arrow(710,450,890,450,C.amber)}
${box(410,550,340,100,'⑥ 证据记录',['run_id · 哈希 · 事件 · 指标'],C.steel)}${box(850,550,340,100,'结果回灌',['适用域 · 失败边界 · 版本冻结'],C.teal)}${arrow(750,600,850,600,C.steel)}
<path d="M1190 600 C1430 600 1440 300 1350 300" fill="none" stroke="${C.teal}" stroke-width="3" stroke-dasharray="9 8"/><polygon points="1350,300 1363,292 1363,308" fill="${C.teal}"/>
`);

figs['C-F03_AI与6G双向耦合.svg'] = svg('AI决定“传什么、何时传、用何种模式”，6G状态反过来约束AI','评分—解码解耦：学习处理排序，规则保证可执行',`
${CIRC(800,455,128,'#E6F3F6',C.cyan,4)}${T(800,430,'条件化',29,800,C.navy,'middle')}${T(800,470,'通信决策',29,800,C.navy,'middle')}${T(800,505,'AI × 6G',21,700,C.cyan,'middle')}
${box(150,190,380,150,'AI侧：价值估计',['任务紧迫度 · 健康风险','能量余量 · 候选收益'],C.cyan)}${box(1070,190,380,150,'6G侧：状态与约束',['可见窗口 · 速率 · 丢失','ACK义务 · 单在途协议'],C.amber)}
${box(150,590,380,140,'输出：候选排序',['发送哪条遥测','robust / fast / idle'],C.teal)}${box(1070,590,380,140,'执行：安全解码',['不可行动作被屏蔽','域外/异常受控回退'],C.steel)}
<path d="M530 270 C690 190 910 190 1070 270" fill="none" stroke="${C.cyan}" stroke-width="6"/><polygon points="1068,270 1045,258 1048,284" fill="${C.cyan}"/>
${T(800,210,'AI给出价值排序',20,700,C.cyan,'middle')}
<path d="M1070 660 C910 760 690 760 530 660" fill="none" stroke="${C.amber}" stroke-width="6"/><polygon points="532,660 555,648 552,674" fill="${C.amber}"/>
${T(800,752,'链路结果与边界形成新证据',20,700,C.amber,'middle')}
${arrow(530,650,700,515,C.teal)}${arrow(900,515,1070,650,C.steel)}
`);

figs['A-F01_公开特征教师标注学习评分器.svg'] = svg('训练链与推理链在约束解码器处汇合，而不是让模型直接控制链路','公开特征—教师标注—学习评分器数据链',`
${T(100,165,'离线训练链',22,800,C.cyan)}${T(100,520,'在线推理链',22,800,C.teal)}
${box(90,210,250,125,'版本锁定观测',['14维全局 + 9维候选'],C.steel)}${box(400,210,250,125,'候选集合',['task × mode + idle'],C.cyan)}${box(710,210,250,125,'教师预算树',['仅 OPTIMAL / gap=0 准入'],C.amber)}${box(1020,210,250,125,'监督标签',['候选效用 + 可行性'],C.teal)}${box(1330,210,190,125,'评分器',['23-32-16'],C.cyan)}
${arrow(340,272,400,272)}${arrow(650,272,710,272)}${arrow(960,272,1020,272)}${arrow(1270,272,1330,272)}
${box(90,565,300,125,'实时公开观测',['健康下界 · 任务 · 预测窗口'],C.teal)}${box(470,565,300,125,'冻结学习评分器',['候选分数'],C.cyan)}${box(850,565,300,125,'约束解码器（B线模块）',['能量 · 窗口 · 协议'],C.amber)}${box(1230,565,290,125,'可执行动作',['发送 / 等待 / 回退'],C.steel)}
${arrow(390,628,470,628,C.teal)}${arrow(770,628,850,628,C.teal)}${arrow(1150,628,1230,628,C.teal)}
${R(470,390,680,80,'#FFF5E3',C.amber,14)}${T(810,425,'训练域：零损失　→　正式域：含随机丢失（域外压力测试）',20,800,C.amber,'middle')}${T(810,457,'模型输出是评分，不是执行命令',17,600,C.muted,'middle')}
`,'项目事实：claim-D1/D3/E2；正式域外关系见正式输入协议。');

figs['A-F02_教师标签质量审计.svg'] = svg('旧20样本缺少可学习的决策差异，只能用于管线回归','条形分布＋标签类别点图＋困难工况覆盖矩阵',`
${R(70,150,460,620,C.white,C.grid,20)}${T(105,200,'(a) 任务标签信息量',22,800)}
${T(115,270,'任务动作全零',19,600)}<rect x="300" y="242" width="180" height="36" rx="8" fill="#E8EFF4"/><rect x="300" y="242" width="117" height="36" rx="8" fill="${C.coral}"/>${T(430,268,'13/20',18,800,C.coral)}
${T(115,340,'至少一个非零',19,600)}<rect x="300" y="312" width="180" height="36" rx="8" fill="#E8EFF4"/><rect x="300" y="312" width="63" height="36" rx="8" fill="${C.teal}"/>${T(375,338,'7/20',18,800,C.teal)}
${R(125,420,350,155,'#FCEAEA',C.coral,16)}${T(300,472,'13/20',36,900,C.coral,'middle')}${T(300,512,'任务动作全零',18,700,C.ink,'middle')}${T(300,548,'仅支持管线回归',17,700,C.muted,'middle')}
${R(570,150,440,620,C.white,C.grid,20)}${T(605,200,'(b) 最优集合辨识度',22,800)}
${T(625,275,'idle 位于最优集合',19,600)}${L(625,315,930,315,C.grid,5)}${CIRC(915,315,12,C.amber)}${T(915,355,'19/20',18,800,C.amber,'middle')}
${T(625,435,'唯一非 idle 最优',19,600)}${L(625,475,930,475,C.grid,5)}${CIRC(640,475,12,C.teal)}${T(640,515,'1/20',18,800,C.teal,'middle')}
${R(620,590,340,105,'#FFF5E3',C.amber,14)}${multiline(790,625,['高命中不等于学到有效策略','并列最优会掩盖模型能力'],18,700,C.amber,1.45,'middle')}
${R(1050,150,480,620,C.white,C.grid,20)}${T(1085,200,'(c) 困难工况覆盖',22,800)}
${['低能量','无窗口','窗口前到期','多任务冲突'].map((s,i)=>`${T(1090,285+i*92,s,18,600)}${R(1280,250+i*92,180,55,'url(#hatch)',C.grid,10)}${T(1370,286+i*92,'0 / 20',18,800,C.muted,'middle')}`).join('')}
${R(1090,650,370,70,'#FCEAEA',C.coral,12)}${T(1275,692,'仅旧20样本冻结包',20,800,C.coral,'middle')}
`,'数据源：claim-D1；不得据此声称AI优于规则。');

figs['A-F03_小样本模型对照.svg'] = svg('小样本域内对照不支持学习评分器优于简单基线','棒棒糖图＋样本量警示；test utility MSE，越低越好',`
${R(100,170,930,560,C.white,C.grid,22)}${T(150,225,'测试集 utility MSE',24,800)}
${[0,0.1,0.2,0.3,0.4].map((v,i)=>`${L(220+i*165,275,220+i*165,650,C.grid,1)}${T(220+i*165,685,v.toFixed(1),16,500,C.muted,'middle')}`).join('')}
${T(160,370,'线性模型',20,700)}${L(220,360,486,360,C.steel,6)}${CIRC(486,360,14,C.teal)}${T(505,367,'0.161',20,800,C.teal)}
${T(160,520,'MLP',20,700)}${L(220,510,807,510,C.steel,6)}${CIRC(807,510,14,C.coral)}${T(830,517,'0.356',20,800,C.coral)}
${R(1080,170,420,250,'#FFF5E3',C.amber,22)}${T(1290,235,'n = 4',48,900,C.amber,'middle')}${T(1290,285,'测试观测数量',20,700,C.ink,'middle')}${multiline(1290,335,['置信度不足','禁止计算“提升率”'],18,600,C.muted,1.4,'middle')}
${R(1080,460,420,270,'#EDF7F4',C.teal,22)}${T(1290,525,'Idle 基线',24,800,C.teal,'middle')}${T(1290,590,'4 / 4',52,900,C.teal,'middle')}${T(1290,635,'最优集合命中',18,600,C.muted,'middle')}${T(1290,685,'进一步说明标签辨识度不足',16,600,C.muted,'middle')}
`,'数据源：claim-D3；仅4条测试观测，不构成调度收益或泛化证据。');

figs['A-F05_公开信息与真值隔离.svg'] = svg('评分器只看可公开观测，未来真实结果被隔离在评估侧','信息边界图：输入、禁止项与评估真值',`
${R(90,170,650,560,'#EDF7F4',C.teal,26)}${T(415,225,'评分器可见：公开观测',27,800,C.teal,'middle')}
${box(135,270,260,120,'健康信息',['能量/SOC/容量下界'],C.teal)}${box(435,270,260,120,'任务信息',['期限 · 权重 · 剩余字节'],C.cyan)}${box(135,440,260,120,'链路预测',['窗口 · 速率 · 预测丢失'],C.cyan)}${box(435,440,260,120,'协议公开态',['在途标志 · 可见任务数'],C.steel)}
${R(860,170,650,560,'#FCEAEA',C.coral,26)}${T(1185,225,'评分器不可见：未来与对照真值',27,800,C.coral,'middle')}
${box(905,270,260,120,'未来真实链路',['真实丢包 · 未来ACK'],C.coral)}${box(1205,270,260,120,'最终结果',['按时交付 · 最低SOC'],C.coral)}${box(905,440,260,120,'其他策略结果',['EDF/Value未来收益'],C.coral)}${box(1205,440,260,120,'评估器专用',['完整事件链 · 统计裁决'],C.amber)}
${L(800,185,800,715,C.coral,4,'12 10')}${T(800,765,'禁止未来信息泄漏',22,800,C.coral,'middle')}
`);

figs['B-F01_发送确认重传去重时序.svg'] = svg('确认丢失不会重复计收益：系统重传同一数据块并在接收端去重','协议泳道时序图',`
${['任务队列','调度器','星上发送端','随机信道','地面接收端','证据记录器'].map((s,i)=>`${T(170+i*250,180,s,19,800,C.navy,'middle')}${L(170+i*250,205,170+i*250,755,C.grid,2,'7 7')}`).join('')}
${T(90,250,'正常路径',17,800,C.teal)}${arrow(170,265,420,265,C.teal)}${T(295,250,'任务到达',15,600,C.muted,'middle')}${arrow(420,315,670,315,C.cyan)}${T(545,300,'选择块 k',15,600,C.muted,'middle')}${arrow(670,365,920,365,C.cyan)}${T(795,350,'DATA(k)',15,700,C.cyan,'middle')}${arrow(920,415,1170,415,C.cyan)}${arrow(1170,465,920,465,C.teal)}${T(1045,450,'ACK(k)',15,700,C.teal,'middle')}${arrow(920,505,1420,505,C.steel)}${T(1170,490,'完成事件 + 哈希',15,600,C.muted,'middle')}
${T(90,575,'异常路径',17,800,C.coral)}${arrow(670,590,920,590,C.cyan)}${L(920,590,1170,590,C.coral,4,'10 8')}${T(1045,575,'ACK 丢失',16,800,C.coral,'middle')}${arrow(670,650,920,650,C.amber)}${T(795,635,'同块重传 k',15,700,C.amber,'middle')}${arrow(920,700,1170,700,C.amber)}${T(1045,685,'接收端去重',15,700,C.amber,'middle')}${arrow(1170,735,1420,735,C.steel)}
`,'机制图；事件名称以冻结协议实现与验收记录为准。');

figs['B-F02_能量账本校核.svg'] = svg('发送能耗可由事件账本独立复算，而不是界面装饰','能量构成瀑布＋事件阶梯线＋手算校核',`
${R(70,160,650,610,C.white,C.grid,20)}${T(105,210,'(a) 单次发送能量构成',22,800)}
<rect x="150" y="330" width="180" height="260" fill="${C.steel}"/><rect x="390" y="460" width="180" height="130" fill="${C.cyan}"/>${L(120,590,640,590,C.ink,2)}
${T(240,625,'背景段',18,700,C.steel,'middle')}${T(480,625,'发送段',18,700,C.cyan,'middle')}${T(240,315,'36 W × 2 s',17,700,C.steel,'middle')}${T(480,445,'36 W × 1.03125 s',17,700,C.cyan,'middle')}${T(360,700,'合计 = 0.0303125 Wh',25,900,C.navy,'middle')}
${R(770,160,760,360,C.white,C.grid,20)}${T(805,210,'(b) 事件驱动的能量阶梯线',22,800)}
${[0,1,2,3,4].map((v,i)=>`${L(860,265+i*50,1450,265+i*50,C.grid,1)}${T(840,271+i*50,(0.62-i*0.03).toFixed(2),15,500,C.muted,'end')}`).join('')}
<polyline points="860,265 980,265 980,315 1120,315 1120,365 1280,365 1280,415 1450,415" fill="none" stroke="${C.teal}" stroke-width="7"/>
${T(980,465,'任务到达',15,600,C.muted,'middle')}${T(1120,465,'发送',15,700,C.cyan,'middle')}${T(1280,465,'ACK/超时',15,700,C.amber,'middle')}
${R(770,560,760,210,'#EDF7F4',C.teal,20)}${T(810,610,'(c) 实现—手算一致性',22,800)}${T(850,675,'实现值',18,600)}${T(1050,675,'0.0303125 Wh',24,900,C.teal)}${T(850,730,'手算值',18,600)}${T(1050,730,'0.0303125 Wh',24,900,C.teal)}${T(1420,705,'Δ = 0',30,900,C.navy,'middle')}
`,'数据源：claim-E1；仅指定发送段口径，不外推为整星能耗。');

function csvRows(text){ const [h,...rs]=text.trim().split(/\r?\n/); const keys=h.split(','); return rs.map(r=>Object.fromEntries(r.split(',').map((v,i)=>[keys[i],v]))); }
let perRun='', matrix='';
try { perRun=execFileSync('git',['show','64db43c:docs/evidence/B/R5_2026-10-29/per_run.csv'],{cwd:ROOT,encoding:'utf8'}); matrix=execFileSync('git',['show','64db43c:experiments/test_matrix.json'],{cwd:ROOT,encoding:'utf8'}); } catch { perRun=''; matrix=''; }
const cellMeta = matrix ? Object.fromEntries(JSON.parse(matrix).cells.map(c=>[c.cell_id,c])) : {};
const rows=perRun?csvRows(perRun):[]; const agg={};
for(const r of rows){ const k=r.cell_id; agg[k]??={edf:[],value:[]}; agg[k][r.policy_id].push(+r.weighted_on_time_rate); }
const mean=a=>a.reduce((x,y)=>x+y,0)/a.length; const vals=Object.keys(agg).sort().map(k=>({k,edf:mean(agg[k].edf),value:mean(agg[k].value),...cellMeta[k]}));
const colorSeq=v=>{const t=Math.max(0,Math.min(1,v)); const a=[232,239,244],b=[43,155,176]; return `rgb(${a.map((x,i)=>Math.round(x+(b[i]-x)*t)).join(',')})`;};
const colorDiv=v=>{const m=.25,t=Math.min(1,Math.abs(v)/m); const b=v>=0?[41,151,125]:[217,92,92],a=[247,249,251]; return `rgb(${a.map((x,i)=>Math.round(x+(b[i]-x)*t)).join(',')})`;};
const heat=(x,title,key,div=false)=>{let s=T(x,210,title,21,800); vals.forEach((d,i)=>{const col=i%6,row=Math.floor(i/6),v=key==='diff'?d.value-d.edf:d[key]; const xx=x+col*73,yy=250+row*125;s+=R(xx,yy,65,76,div?colorDiv(v):colorSeq(v),C.white,8,1);s+=T(xx+32,yy+34,v.toFixed(2),15,800,div?(v>=0?C.teal:C.coral):C.ink,'middle');s+=T(xx+32,yy+60,d.k.replace('cell_',''),12,600,C.muted,'middle');});return s;};
figs['B-F03_开发期18工况规则矩阵.svg'] = svg('固定规则的优劣随工况变化，说明策略选择存在优化空间','三联热力图；每格为10条轨迹均值',`
${heat(70,'(a) EDF','edf')}${heat(590,'(b) Value','value')}${heat(1110,'(c) Value − EDF','diff',true)}
${T(290,690,'低负载',16,700,C.muted,'middle')}${T(290,715,'近容量',16,700,C.muted,'middle')}${T(290,740,'过载',16,700,C.muted,'middle')}
${R(500,660,600,95,'#FFF5E3',C.amber,14)}${T(800,700,'开发期规则验证矩阵',22,900,C.amber,'middle')}${T(800,730,'非正式实验 · 不支持AI收益结论',17,700,C.muted,'middle')}
`,'数据源：R5 per_run.csv，360次规则运行；claim-D2。');

figs['B-F04_正式实验公平比较协议.svg'] = svg('18工况×10轨迹的配对设计，先冻结输入再裁决AI收益','因素矩阵＋共享输入配对流程',`
${R(70,160,580,610,C.white,C.grid,20)}${T(110,215,'(a) 3 × 3 × 2 因素矩阵',23,800)}
${['低能量','中能量','高能量'].map((s,i)=>T(285+i*115,270,s,16,700,C.muted,'middle')).join('')}
${['低负载','近容量','过载'].map((s,i)=>T(185,350+i*110,s,17,700,C.muted,'end')).join('')}
${[0,1,2].map(r=>[0,1,2].map(c=>`${R(230+c*115,305+r*110,94,82,'#E8F3F6',C.cyan,12)}${T(277+c*115,337+r*110,'mild',14,700,C.cyan,'middle')}${T(277+c*115,370+r*110,'strong',14,700,C.amber,'middle')}`).join('')).join('')}
${T(360,690,'18工况 × 每工况10条独立轨迹',20,900,C.navy,'middle')}
${R(700,160,830,610,C.white,C.grid,20)}${T(740,215,'(b) 同一冻结输入上的配对比较',23,800)}
${box(755,270,250,110,'冻结输入',['任务 · 信道 · 能源 · seed'],C.steel)}${box(1130,240,280,90,'EDF',['固定期限规则'],C.navy)}${box(1130,355,280,90,'Value',['固定价值规则'],C.teal)}${box(1130,470,280,90,'学习策略',['冻结模型 + 受控回退'],C.cyan)}
${arrow(1005,325,1130,285,C.steel)}${arrow(1005,325,1130,400,C.steel)}${arrow(1005,325,1130,515,C.steel)}
${box(930,625,350,105,'配对差 + 95%区间',['总体等权 + 分工况 + 四档裁决'],C.amber)}${arrow(1270,560,1110,625,C.amber)}
${R(740,575,160,120,'#FCEAEA',C.coral,15)}${multiline(820,610,['正式环境含','随机数据丢失','属于域外评估'],16,800,C.coral,1.35,'middle')}
`,'正式结果未签核；本图只描述预登记实验协议。');

figs['C-F04_证据链.svg'] = svg('每个结论都能沿 claim 回到运行、事件和版本指纹','证据追溯网络：材料不是代码截图的堆叠',`
${[['业务主张',180,340,C.navy],['claim_id',460,240,C.cyan],['指标与区间',460,470,C.teal],['run_id',790,240,C.steel],['事件与能量账本',790,470,C.amber],['输入/模型哈希',1120,240,C.coral],['报告·PPT·前端',1350,410,C.navy]].map(([s,x,y,c])=>`${CIRC(x,y,78,'#FFFFFF',c,5)}${multiline(x,y-8,s.split('·'),18,800,c,1.35,'middle')}`).join('')}
${arrow(258,330,382,265,C.navy)}${arrow(258,355,382,445,C.navy)}${arrow(538,240,712,240,C.cyan)}${arrow(538,470,712,470,C.teal)}${arrow(868,240,1042,240,C.steel)}${arrow(868,470,1042,275,C.amber)}${arrow(1198,265,1280,370,C.coral)}${arrow(1198,470,1280,430,C.coral)}
${R(410,650,780,90,'#EDF7F4',C.teal,16)}${T(800,690,'事实源更新 → 门禁校验 → 三方签核 → 材料同步',23,900,C.teal,'middle')}${T(800,722,'禁止从PPT反向手抄数字回事实源',16,700,C.muted,'middle')}
`);

figs['C-F05_三阶段落地路线.svg'] = svg('先证明闭环可信，再做影子运行，最后才讨论在轨试点','每一阶段都有输入、验收标准和退出条件',`
${L(170,430,1430,430,C.grid,12)}
${[['阶段1',260,'合成验证',['冻结仿真与模型','预登记实验','三方复算'],'退出：结果与边界可复现',C.cyan],['阶段2',800,'影子运行',['接入离线遥测','不下发控制','比较人工/规则/AI'],'退出：连续稳定且可解释',C.teal],['阶段3',1340,'受控试点',['沙箱链路','人工确认','小范围灰度'],'退出：安全审查与回滚齐备',C.amber]].map(([k,x,t,ls,e,c])=>`${CIRC(x,430,48,c)}${T(x,440,k,18,900,C.white,'middle')}${R(x-190,170,380,190,C.white,c,20,3)}${T(x,220,t,26,900,c,'middle')}${multiline(x,265,ls,18,600,C.muted,1.55,'middle')}${R(x-190,520,380,105,'#F7F9FB',c,14,2)}${multiline(x,560,e.split('；'),17,800,c,1.4,'middle')}`).join('')}
${T(800,730,'不跨阶段夸大成熟度：当前定位为“合成环境下的场景设计验证”',22,900,C.navy,'middle')}
`);

figs['C-F08_产业规模与应用价值.svg'] = svg('卫星产业规模持续增长，但本项目只主张调度方案的可迁移价值','比例环＋规模条；数据均为SIA FY2025口径',`
${R(80,160,520,610,C.white,C.grid,22)}${T(120,215,'商业卫星产业占全球航天经济',23,800)}${CIRC(340,420,140,'none',C.pale,38)}<circle cx="340" cy="420" r="140" fill="none" stroke="${C.cyan}" stroke-width="38" stroke-dasharray="625 880" transform="rotate(-90 340 420)"/>${T(340,415,'71%',56,900,C.cyan,'middle')}${T(340,455,'商业卫星产业',18,700,C.muted,'middle')}${T(340,650,'3030 / 4290 亿美元',24,900,C.navy,'middle')}
${R(650,160,870,610,C.white,C.grid,22)}${T(700,215,'FY2025 行业规模快照',23,800)}
${[['年末在轨卫星',14266,14500,C.navy],['年度入轨卫星',4434,14500,C.cyan],['年度发射次数',296,14500,C.amber]].map(([s,v,m,c],i)=>`${T(710,315+i*130,s,20,700)}<rect x="930" y="280" width="500" height="38" rx="9" fill="${C.pale}" transform="translate(0 ${i*130})"/><rect x="930" y="280" width="${500*v/m}" height="38" rx="9" fill="${c}" transform="translate(0 ${i*130})"/>${T(1450,310+i*130,v,22,900,c,'end')}`).join('')}
${R(700,650,720,70,'#FFF5E3',C.amber,12)}${T(1060,692,'行业数据说明需求规模，不等同项目性能或市场份额',19,800,C.amber,'middle')}
`,'来源：claim-P2；SIA 2026报告，统计年度FY2025。');

figs['B-F05_正式结果未完成模板.svg'] = svg('正式实验结果：等待三方签核','安全占位模板；签核前不得生成结果点、胜负颜色或提升率',`
${R(140,190,1320,500,C.white,C.grid,28,1.5,'filter="url(#shadow)"')}${T(800,330,'正式运行未完成',54,900,C.muted,'middle')}${T(800,390,'claim-X1 / claim-X2 / claim-X3 均为 pending',22,700,C.muted,'middle')}
${L(310,520,1290,520,C.grid,3)}${L(800,475,800,565,C.steel,3,'8 8')}${T(800,610,'三方签核后由固定脚本生成森林图、工况热力图和失败事件链',20,800,C.navy,'middle')}
${R(520,735,560,55,'#FCEAEA',C.coral,12)}${T(800,770,'禁止以演示数据、0值或理想结果替代',18,900,C.coral,'middle')}
`,'结果状态：未完成；此模板本身不包含任何实验结论。');

const heroPath=path.join(OUT,'C-F00_星地智调主题背景_v1.png');
const manifest={schema_version:'visual-pack-v1',generated_at:'2026-11-07',generator:'scripts/generate_visual_pack.mjs',canvas:'1600x900 SVG',palette:C,fonts:['Noto Sans SC','Source Han Sans SC','Microsoft YaHei','Arial'],source_revision:'64db43c for R5 evidence lookup',external_assets:fs.existsSync(heroPath)?[{file:path.basename(heroPath),sha256:crypto.createHash('sha256').update(fs.readFileSync(heroPath)).digest('hex'),method:'OpenAI built-in image generation',scope:'non-data thematic background only'}]:[],figures:[]};
for(const [name,content] of Object.entries(figs)){const p=path.join(OUT,name);fs.writeFileSync(p,content,'utf8');manifest.figures.push({file:name,sha256:crypto.createHash('sha256').update(content).digest('hex'),status:name.includes('未完成模板')?'template_only':'ready_for_review'});}
fs.writeFileSync(path.join(OUT,'manifest.json'),JSON.stringify(manifest,null,2)+'\n','utf8');

const sourceGitSha=execFileSync('git',['rev-parse','HEAD'],{cwd:ROOT,encoding:'utf8'}).trim();
const aFigureManifests = [
  {
    figure_id:'A-F01',
    title_cn:'公开特征、教师标注与学习评分器数据链',
    file:'A-F01_公开特征教师标注学习评分器.svg',
    source_files:['docs/report/report_v2.md','docs/contracts/README.md','docs/report/claim_values.json'],
    claim_ids:['claim-D1','claim-D3','claim-E2'],
    data_scope:'mechanism_from_signed_contracts',
    limitations:['模型只输出候选评分，不直接执行动作','正式域含随机丢失，属于零损失训练域外评估'],
  },
  {
    figure_id:'A-F02',
    title_cn:'教师标签质量与困难工况覆盖审计',
    file:'A-F02_教师标签质量审计.svg',
    source_files:['docs/report/claim_values.json'],
    claim_ids:['claim-D1'],
    data_scope:'frozen_old_20_samples_pipeline_regression_only',
    limitations:['仅旧20样本冻结包','不得据此声称AI优于规则或A-N4b扩样成功'],
  },
  {
    figure_id:'A-F03',
    title_cn:'小样本模型对照',
    file:'A-F03_小样本模型对照.svg',
    source_files:['docs/report/claim_values.json'],
    claim_ids:['claim-D3'],
    data_scope:'small_test_set_n4_not_scheduling_gain',
    limitations:['测试观测仅4条','MSE不构成调度收益、提升率或泛化证据'],
  },
  {
    figure_id:'A-F05',
    title_cn:'公开信息与真值隔离',
    file:'A-F05_公开信息与真值隔离.svg',
    source_files:['docs/report/report_v2.md','docs/contracts/README.md'],
    claim_ids:[],
    data_scope:'mechanism_public_observation_boundary',
    limitations:['机制图不包含实验结果','完整事件链和未来真值仅供事后评估，评分器不得回读'],
  },
];
for(const spec of aFigureManifests){
  const preview=`docs/figures/generated/v1/previews/${spec.file.replace(/\.svg$/,'.png')}`;
  const outputs=[`docs/figures/generated/v1/${spec.file}`];
  if(fs.existsSync(path.join(ROOT,preview))) outputs.push(preview);
  const figureManifest={
    schema_version:'figure-manifest-v1',
    figure_id:spec.figure_id,
    title_cn:spec.title_cn,
    owner:'A',
    reviewers:['B','C'],
    source_files:spec.source_files,
    claim_ids:spec.claim_ids,
    data_scope:spec.data_scope,
    script:'scripts/generate_visual_pack.mjs',
    outputs,
    source_git_sha:sourceGitSha,
    git_sha:sourceGitSha,
    generated_at:'2026-11-07',
    status:'review_pending',
    limitations:[...spec.limitations,'嵌字PDF与600 DPI PNG尚待C统一导出'],
  };
  fs.writeFileSync(path.join(OUT,`${spec.figure_id}_manifest.json`),JSON.stringify(figureManifest,null,2)+'\n','utf8');
}
console.log(`generated ${manifest.figures.length} SVG figures in ${OUT}`);
