import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const OUT=path.join(ROOT,'docs','figures','generated','v4','report');
const PRE=path.join(OUT,'previews');
const D=JSON.parse(fs.readFileSync(path.join(ROOT,'docs','figures','source_data','v4_master_pack.json'),'utf8'));
fs.mkdirSync(PRE,{recursive:true});
const C={ink:'#172A3A',muted:'#526575',grid:'#D7E0E6',pale:'#F5F8FA',navy:'#24506F',cyan:'#2B88A3',teal:'#268B79',amber:'#D58A27',red:'#C84F55',violet:'#747FA3',white:'#FFFFFF',sky:'#EAF3F7',mint:'#E9F5F1',sand:'#FCF3E4',rose:'#F9ECEC',lav:'#EEF0F7'};
const FONT="Arial, 'Source Han Sans SC', 'Microsoft YaHei', sans-serif";
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const t=(x,y,s,z=18,w=400,f=C.ink,a='start',extra='')=>`<text x="${x}" y="${y}" font-family="${FONT}" font-size="${z}" font-weight="${w}" fill="${f}" text-anchor="${a}" ${extra}>${esc(s)}</text>`;
const l=(x1,y1,x2,y2,s=C.grid,w=1.2,d='')=>`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${s}" stroke-width="${w}"${d?` stroke-dasharray="${d}"`:''}/>`;
const r=(x,y,w,h,f=C.white,s=C.grid,sw=1.1,rx=2)=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${f}" stroke="${s}" stroke-width="${sw}" rx="${rx}"/>`;
const c=(x,y,rad,f,s=C.white,sw=2)=>`<circle cx="${x}" cy="${y}" r="${rad}" fill="${f}" stroke="${s}" stroke-width="${sw}"/>`;
const p=(pts,s,w=3,f='none',dash='')=>`<path d="M ${pts.map(q=>q.join(' ')).join(' L ')}" fill="${f}" stroke="${s}" stroke-width="${w}" stroke-linejoin="round" stroke-linecap="round"${dash?` stroke-dasharray="${dash}"`:''}/>`;
const arrow=(x1,y1,x2,y2,s=C.navy,w=2,d='')=>`<path d="M${x1} ${y1} L${x2} ${y2}" fill="none" stroke="${s}" stroke-width="${w}"${d?` stroke-dasharray="${d}"`:''} marker-end="url(#a${s.slice(1)})"/>`;
const defs=()=>`<defs>${[C.navy,C.cyan,C.teal,C.amber,C.red,C.violet].map(s=>`<marker id="a${s.slice(1)}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8z" fill="${s}"/></marker>`).join('')}</defs>`;
const pt=(x,y,m,title,sub)=>`${t(x,y,m,23,800)}${t(x+48,y,title,23,800)}${t(x+48,y+28,sub,14,400,C.muted)}`;
const box=(x,y,w,h,m,title,sub)=>`${r(x,y,w,h)}${pt(x+24,y+40,m,title,sub)}`;
const multi=(x,y,lines,z=16,w=500,f=C.ink,dy=25,a='start')=>lines.map((s,i)=>t(x,y+i*dy,s,z,w,f,a)).join('');
const shell=(body,scope)=>`<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" width="170mm" height="108mm" viewBox="0 0 1700 1080" role="img"><rect width="1700" height="1080" fill="#FFFFFF"/>${defs()}${body}${l(55,1050,1645,1050)}${t(55,1070,scope,12,600,C.red)}${t(1645,1070,'数据与口径见 v4_master_pack.json',12,500,C.muted,'end')}</svg>`;

function aiFigure(){
 let b=box(55,45,780,470,'(a)','公开观测—教师—学习评分数据链','模型输出候选价值，不直接下发通信动作');
 const nodes=[['14维全局特征','任务·窗口·健康',C.sky,C.navy],['9维候选特征','task × mode',C.lav,C.violet],['预算教师','gap = 0 准入',C.sand,C.amber],['23-32-16 MLP','效用 + 可行性',C.mint,C.teal],['CandidateScore[]','交给安全解码',C.sky,C.cyan]];
 nodes.forEach((q,i)=>{const x=90+i*145;b+=`${r(x,205,125,105,q[2],q[3],1.5,3)}${t(x+62,242,q[0],15,800,q[3],'middle')}${t(x+62,276,q[1],12,500,C.muted,'middle')}`;if(i<4)b+=arrow(x+125,258,x+142,258,q[3],1.8);});
 b+=`${r(90,350,705,92,C.pale,C.grid)}${t(110,382,'训练域：零数据损失',14,700,C.red)}${t(110,410,'正式评估域：随机数据/ACK丢失（域外）',14,700,C.red)}${t(500,382,'结构边界',14,700,C.navy)}${t(500,410,'评分与执行解耦',14,600,C.ink)}`;
 b+=box(865,45,780,470,'(b)','旧教师标签的信息量审计','n = 20；冻结包只适合管线回归');
 const aud=[['任务动作全零',13,C.red],['idle并列最优',19,C.amber],['唯一非idle最优',1,C.teal],['困难工况覆盖',0,C.red]];
 aud.forEach((q,i)=>{const y=188+i*70;b+=`${t(900,y+7,q[0],15,600)}${l(1055,y,1535,y,C.grid,12)}${l(1055,y,1055+480*q[1]/20,y,q[2],12)}${c(1055+480*q[1]/20,y,8,q[2])}${t(1565,y+7,`${q[1]}/20`,15,800,q[2],'end')}`;});
 b+=`${t(1295,473,'样本数 / 20',13,600,C.muted,'middle')}${r(900,442,665,42,C.rose,C.red,1,2)}${t(1232,469,'不支持AI增益主张',16,800,C.red,'middle')}`;
 b+=box(55,545,780,465,'(c)','小样本基线对照给出负面证据','test utility MSE；越低越好；测试集 n = 4');
 const baseY=930, scale=v=>190+v/0.4*500;
 [0,.1,.2,.3,.4].forEach(v=>{b+=`${l(scale(v),680,scale(v),baseY,C.grid)}${t(scale(v),baseY+25,v.toFixed(1),12,400,C.muted,'middle')}`;});
 [['线性模型',.161,C.navy,760],['MLP',.356,C.cyan,850]].forEach(q=>{b+=`${t(170,q[3]+6,q[0],16,700,C.ink,'end')}${l(190,q[3],scale(q[1]),q[3],q[2],14)}${c(scale(q[1]),q[3],10,q[2])}${t(scale(q[1])+16,q[3]+6,q[1].toFixed(3),16,800,q[2])}`;});
 b+=`${r(120,955,650,35,C.rose,C.red,1,2)}${t(445,979,'线性基线优于当前MLP；不得包装为学习增益',14,800,C.red,'middle')}`;
 b+=box(865,545,780,465,'(d)','计算时延与教师标注成本','本机CPU实测；对数横轴；不是目标星上时延');
 const lx=1050,rx=1585,ly=[700,770,840,910],log=v=>lx+(Math.log10(v)-Math.log10(.4))/(Math.log10(30)-Math.log10(.4))*(rx-lx);
 [.5,1,2,5,10,20].forEach(v=>b+=`${l(log(v),675,log(v),935,C.grid)}${t(log(v),960,v,12,400,C.muted,'middle')}`);
 [['暖中位',.499,C.teal],['暖p95',.681,C.cyan],['冷载',2.2,C.navy]].forEach((q,i)=>{b+=`${t(1030,ly[i]+5,q[0],14,600,C.ink,'end')}${c(log(q[1]),ly[i],8,q[2])}${t(log(q[1])+13,ly[i]+5,`${q[1]} ms`,13,700,q[2])}`;});
 b+=`${t(1030,ly[3]+5,'教师/状态',14,600,C.ink,'end')}${l(log(7),ly[3],log(24),ly[3],C.amber,8)}${c(log(7),ly[3],7,C.amber)}${c(log(24),ly[3],7,C.amber)}${t((log(7)+log(24))/2,ly[3]-14,'7–24 ms',13,800,C.amber,'middle')}${t((lx+rx)/2,990,'耗时 / ms（log）',13,600,C.muted,'middle')}`;
 return shell(b,'已签核小样本/计时证据；不支持AI收益或星上实时性外推');
}

function sixgFigure(){
 let b=box(55,45,1010,470,'(a)','6G星地链路的协议事件闭环','可见窗口、ACK义务与重复块去重共同决定业务状态');
 const sx=v=>150+840*v/8, lanes=[['SAT→GW',190],['GW',285],['GW→SAT',380],['SAT',455]];
 b+=`${r(sx(0),155,sx(2)-sx(0),335,C.sky,'none')}${r(sx(4),155,sx(8)-sx(4),335,C.mint,'none')}`;
 lanes.forEach(q=>b+=`${t(135,q[1]+5,q[0],13,700,C.muted,'end')}${l(150,q[1],990,q[1])}`);
 const es=[[0,190,'发送',C.navy],[1.03125,285,'接收',C.teal],[2.03125,380,'ACK丢失',C.red],[3.03125,455,'超时',C.amber],[4,190,'重传',C.navy],[5.03125,285,'去重接收',C.cyan],[6.03125,380,'ACK',C.teal]];
 es.forEach((q,i)=>b+=`${c(sx(q[0]),q[1],8,q[3])}${t(sx(q[0]),q[1]+(i%2?-17:28),q[2],12,800,q[3],'middle')}`);
 b+=`${p([[sx(0),190],[sx(1.03125),285],[sx(2.03125),380]],C.red,2)}${p([[sx(4),190],[sx(5.03125),285],[sx(6.03125),380]],C.teal,2)}${l(sx(4),155,sx(4),490,C.red,2,'6 5')}`;
 b+=box(1095,45,550,470,'(b)','发送段能量守恒校核','同一口径实现值与手算值完全一致');
 const vals=[['背景 2 s',.02,C.navy],['发送 1.03125 s',.0103125,C.teal]];
 vals.forEach((q,i)=>{const x=1190+i*190,h=q[1]/.032*230;b+=`${r(x,430-h,110,h,q[2],q[2],0)}${t(x+55,455,q[0],13,600,C.muted,'middle')}${t(x+55,415-h,q[1].toFixed(7),13,800,q[2],'middle')}`;});
 b+=`${l(1160,430,1585,430,C.ink,1.5)}${r(1160,475,425,25,C.sand,C.amber)}${t(1372,493,'ΔE = 0.0303125 Wh',14,800,C.amber,'middle')}`;
 b+=box(55,545,780,465,'(c)','开发期规则矩阵只用于工程验证','weighted-on-time-rate；非正式实验');
 const w=D.claims.development_wotr, yy=800;
 [['EDF',w.edf,C.navy,720],['Value',w.value,C.amber,835]].forEach(q=>{b+=`${t(170,q[3]+6,q[0],16,700,C.ink,'end')}${l(195,q[3],700,q[3],C.grid,18)}${l(195,q[3],195+505*q[1],q[3],q[2],18)}${t(210+505*q[1],q[3]+6,q[1].toFixed(6),16,800,q[2])}`;});
 b+=`${t(447,930,'weighted-on-time-rate',13,600,C.muted,'middle')}${r(120,955,650,35,C.sand,C.amber)}${t(445,979,'开发期规则验证 ≠ AI正式增益结论',14,800,C.amber,'middle')}`;
 b+=box(865,545,780,465,'(d)','通信执行合同的确定性安全边界','高分候选也必须通过全部通信与资源约束');
 const rows=[['窗口可见','NO_VISIBLE_WINDOW'],['单块在途','INFLIGHT_BLOCK'],['期限可达','DEADLINE_UNREACHABLE'],['能量储备','ENERGY_RESERVE'],['字节配额','CONTROL_BUDGET'],['ACK义务','ACK_TIMEOUT']];
 rows.forEach((q,i)=>{const y=690+i*47;b+=`${t(925,y,q[0],14,700)}${t(1190,y,q[1],12,600,C.muted)}${c(1535,y-5,7,i===3?C.amber:C.teal)}${t(1560,y,i===3?'拒绝/idle':'逐项检查',12,700,i===3?C.amber:C.teal)}`;});
 b+=`${l(900,660,1595,660,C.grid)}${t(925,645,'约束',13,600,C.muted)}${t(1190,645,'原因码',13,600,C.muted)}${t(1535,645,'执行语义',13,600,C.muted)}`;
 return shell(b,'R3/R5工程签核与开发期证据；不作为正式AI策略比较');
}

function formalFigure(){
 let b=box(55,45,780,470,'(a)','18 个工况的三因子全组合','负载 3 × 能量 3 × 链路扰动 2');
 const loads=['低负载','近容量','过载'], energies=['低能量','中能量','充足'];
 loads.forEach((u,i)=>energies.forEach((e,j)=>{const x=185+j*170,y=190+i*92;b+=`${r(x,y,145,65,i===2?C.rose:j===0?C.sand:C.sky,C.grid)}${t(x+72,y+25,`${u} × ${e}`,12,700,C.ink,'middle')}${t(x+72,y+49,'mild / strong',11,600,C.muted,'middle')}`;}));
 b+=`${t(455,490,'每格2种链路扰动 → 18 个工况',14,800,C.navy,'middle')}`;
 b+=box(865,45,780,470,'(b)','同轨迹三策略配对比较','180 条轨迹 × EDF / Value / Learned = 540 次策略运行');
 b+=`${r(905,185,165,190,C.pale,C.grid)}${t(987,230,'180 条轨迹',21,800,C.navy,'middle')}${t(987,265,'每工况10条',14,600,C.muted,'middle')}${t(987,300,'seed 600000–600179',12,600,C.muted,'middle')}`;
 const policies=[['EDF',C.navy,165],['Value',C.amber,275],['Learned',C.cyan,385]];
 b+=`<g data-role="paired-fanout">${l(1070,280,1160,280,C.navy,2)}${l(1160,205,1160,425,C.navy,2)}`;
 policies.forEach(q=>{const cy=q[2]+38;b+=`${r(1260,q[2],190,76,C.white,q[1],2)}${t(1355,q[2]+31,q[0],16,800,q[1],'middle')}${t(1355,q[2]+56,'同一轨迹输入',11,600,C.muted,'middle')}<path d="M1160 ${cy} L1250 ${cy}" fill="none" stroke="${q[1]}" stroke-width="2" marker-end="url(#a${q[1].slice(1)})"/>`;});
 b+='</g>';
 b+=`${r(960,460,590,38,C.sky,C.cyan)}${t(1255,485,'同轨迹共享输入和随机流，禁止跨轨迹拼接',13,800,C.cyan,'middle')}`;
 b+=box(55,545,780,465,'(c)','预登记统计协议约束分析自由度','分层配对 bootstrap；缺失不插补、不删格');
 const steps=[['配对差值','Learned−EDF / Value'],['18格等权','轨迹内配对'],['10,000次','固定seed 20261104'],['95%区间','percentile'],['输出四档','胜/等效/负/未完成']];
 steps.forEach((q,i)=>{const x=85+i*145;b+=`${r(x,705,125,145,i===4?C.lav:C.pale,i===4?C.violet:C.grid)}${t(x+62,745,q[0],15,800,i===4?C.violet:C.navy,'middle')}${t(x+62,784,q[1],11,600,C.muted,'middle')}`;if(i<4)b+=arrow(x+125,778,x+142,778,C.navy,1.6);});
 b+=`${t(445,920,'采样单位：trajectory within cell　·　pointwise intervals',13,600,C.muted,'middle')}`;
 b+=box(865,545,780,465,'(d)','结果发布门禁保持“未完成”','claim-X1/X2/X3 pending；ABC回执前禁止结论化');
 const outs=[['胜',C.teal],['等效档',C.cyan],['负',C.red],['未完成',C.muted]];
 outs.forEach((q,i)=>{const x=910+i*170;b+=`${r(x,710,145,100,i===3?C.pale:C.white,q[1],1.8)}${t(x+72,752,q[0],19,800,q[1],'middle')}${t(x+72,783,i===3?'当前状态':'待统计',12,600,C.muted,'middle')}`;});
 b+=`${r(930,860,640,82,C.rose,C.red)}${t(1250,894,'当前正式输入 0 条 · 正式运行 0 次',16,800,C.red,'middle')}${t(1250,923,'不得填写效果百分比、胜负色块或显著性',14,600,C.red,'middle')}`;
 return shell(b,'正式实验设计已预登记；结果状态：未完成');
}

function reliabilityFigure(){
 let b=box(55,45,780,470,'(a)','高分候选被能量储备安全拒绝','开发期注入探针：score=10；energy lower=0.49 Wh');
 b+=`${r(105,195,180,90,C.sky,C.cyan)}${t(195,230,'robust / fast',15,700,C.cyan,'middle')}${t(195,265,'score = 10.0',21,800,C.cyan,'middle')}${arrow(285,240,410,240,C.cyan,3)}${r(410,175,205,130,C.sand,C.amber,2)}${t(512,215,'ENERGY_RESERVE',14,800,C.amber,'middle')}${t(512,250,'0.49 < 0.50 Wh',18,800,C.red,'middle')}${t(512,280,'约束失败',13,700,C.red,'middle')}${arrow(615,240,720,240,C.amber,3)}${r(720,195,80,90,C.mint,C.teal,2)}${t(760,230,'idle',18,800,C.teal,'middle')}${t(760,262,'安全动作',12,600,C.muted,'middle')}`;
 b+=`${r(105,365,695,82,C.pale,C.grid)}${t(125,397,'结论',14,800,C.navy)}${t(185,397,'AI高分不覆盖确定性安全边界；拒绝原因进入事件证据。',14,600)}${t(185,425,'该案例证明约束层有效，不证明学习模型性能。',13,600,C.red)}`;
 b+=box(865,45,780,470,'(b)','模型包错误被转换为受控边界','BadZipFile / EOFError → MODEL_FORMAT；禁止异常泄漏');
 const stages=[['模型文件','加载'],['格式校验','捕获异常'],['错误归一','MODEL_FORMAT'],['策略层','受控处理']];
 stages.forEach((q,i)=>{const x=900+i*175;b+=`${r(x,205,140,105,i===2?C.rose:C.pale,i===2?C.red:C.grid)}${t(x+70,244,q[0],15,800,i===2?C.red:C.navy,'middle')}${t(x+70,278,q[1],12,600,C.muted,'middle')}`;if(i<3)b+=arrow(x+140,258,x+168,258,i===1?C.red:C.navy,2);});
 b+=`${r(925,365,620,82,C.mint,C.teal)}${t(1235,398,'边界结果可记录、可测试、可复现',16,800,C.teal,'middle')}${t(1235,425,'不把损坏模型伪装为正常AI输出',13,600,C.muted,'middle')}`;
 b+=box(55,545,1010,465,'(c)','链路异常通过协议状态机恢复','ACK丢失不重复计收益；超时后同块重传，接收端去重');
 const sx=v=>145+860*v/6.2, ev=[[0,'发送',C.navy],[1.03125,'首次接收',C.teal],[2.03125,'ACK丢失',C.red],[3.03125,'超时',C.amber],[4,'重传',C.navy],[5.03125,'去重接收',C.cyan],[6.03125,'ACK',C.teal]];
 b+=l(145,805,1005,805,C.ink,2);
 ev.forEach((q,i)=>{const x=sx(q[0]);b+=`${l(x,795,x,815,C.ink)}${c(x,805,9,q[2])}${t(x,760-(i%2)*55,q[1],13,800,q[2],'middle')}${t(x,780-(i%2)*55,q[0].toFixed(q[0]%1?5:1)+' s',11,500,C.muted,'middle')}`;});
 b+=`${p(ev.map(q=>[sx(q[0]),805]),C.grid,2)}${r(160,900,830,55,C.mint,C.teal)}${t(575,933,'有效载荷 1024 B · 能量违规 0 · 不重复计收益',14,800,C.teal,'middle')}`;
 b+=box(1095,545,550,465,'(d)','证据边界矩阵','每种失效均有原因码、事件和限定结论');
 const rr=[['能量不足','ENERGY_RESERVE','idle'],['窗口关闭','NO_VISIBLE_WINDOW','拒绝'],['ACK丢失','ACK_TIMEOUT','重传'],['模型损坏','MODEL_FORMAT','受控错误']];
 rr.forEach((q,i)=>{const y=690+i*70;b+=`${t(1135,y,q[0],14,700)}${t(1270,y,q[1],12,600,C.muted)}${r(1485,y-25,110,36,i===3?C.rose:C.pale,i===3?C.red:C.grid)}${t(1540,y,q[2],13,800,i===3?C.red:C.navy,'middle')}`;});
 return shell(b,'开发期失效注入与R3签核样例；不作为正式策略收益证据');
}

function engineeringFigure(){
 let b=box(55,45,780,470,'(a)','四层工程架构承载同一决策闭环','从仿真状态到材料证据，接口边界清晰');
 const layers=[['展示与证据层','控制台 · 对比 · 追溯',C.lav,C.violet],['服务接口层','创建 · 状态 · 事件 · 导出',C.sky,C.cyan],['决策核心层','评分 · 解码 · 回退',C.mint,C.teal],['仿真环境层','窗口 · 信道 · 能量 · ACK',C.sand,C.amber]];
 layers.forEach((q,i)=>{const y=155+i*82;b+=`${r(110,y,660,60,q[2],q[3],1.4)}${t(140,y+25,q[0],15,800,q[3])}${t(350,y+25,q[1],14,600,C.ink)}${i<3?arrow(440,y+60,440,y+78,C.navy,1.5):''}`;});
 b+=box(865,45,780,470,'(b)','六步业务链贯穿算法与通信执行','每一步均产生可观察状态或可追溯事件');
 const six=[['1','任务到达'],['2','窗口预测'],['3','AI评分'],['4','约束解码'],['5','发送/确认'],['6','评估归档']];
 six.forEach((q,i)=>{const x=900+(i%3)*225,y=175+Math.floor(i/3)*155;b+=`${c(x+42,y+35,23,[C.navy,C.cyan,C.violet,C.amber,C.teal,C.red][i])}${t(x+42,y+42,q[0],15,800,C.white,'middle')}${t(x+80,y+41,q[1],15,700)}${i%3<2?arrow(x+165,y+35,x+215,y+35,C.navy,1.8):''}`;});
 b+=`${arrow(1440,210,1440,330,C.navy,1.8)}<path data-role="feedback-loop" d="M1392 392 L1392 470 L942 470 L942 398" fill="none" stroke="${C.teal}" stroke-width="1.8" stroke-dasharray="6 4" marker-end="url(#a${C.teal.slice(1)})"/>${t(1167,495,'结果反馈进入下一决策周期',13,700,C.teal,'middle')}`;
 b+=box(55,545,1010,465,'(c)','证据链把每项主张追溯到运行事实','材料只消费已冻结、已统计、已签核的证据');
 const chain=[['冻结输入','config/model SHA'],['运行身份','run/policy/seed'],['原始事件','events/ledger'],['统计结果','results/CI'],['主张登记','claim + scope'],['材料发布','报告/PPT/视频']];
 chain.forEach((q,i)=>{const x=85+i*158;b+=`${r(x,705,135,125,i===5?C.lav:C.pale,i===5?C.violet:C.grid)}${t(x+67,745,q[0],14,800,i===5?C.violet:C.navy,'middle')}${t(x+67,782,q[1],11,600,C.muted,'middle')}`;if(i<5)b+=arrow(x+135,768,x+153,768,C.navy,1.6);});
 b+=`${r(105,895,900,55,C.sky,C.cyan)}${t(555,928,'事实源 → 指标 → 主张为单向链；材料不得反向改写运行事实',14,800,C.cyan,'middle')}`;
 b+=box(1095,545,550,465,'(d)','发布门禁与演示边界','工程平台可操作；演示数据与实验结论隔离');
 const gates=[['SHA完整性','冻结对象'],['数据分区','fixture/formal'],['四档口径','胜/等效/负/未完成'],['三方签核','A/B/C receipts'],['匿名检查','身份/路径'],['可复现性','换机验收']];
 gates.forEach((q,i)=>{const x=1130+(i%2)*245,y=670+Math.floor(i/2)*92;b+=`${r(x,y,220,65,C.white,i===5?C.amber:C.grid,1.2)}${t(x+15,y+25,q[0],14,800,i===5?C.amber:C.navy)}${t(x+15,y+49,q[1],12,600,C.muted)}`;});
 b+=`${r(1130,960,465,30,C.rose,C.red)}${t(1362,981,'未签核结果不得进入前端、报告或PPT',13,800,C.red,'middle')}`;
 return shell(b,'工程架构与材料追溯机制；不代表真实在轨部署');
}

const figs=[
 ['A-F00_AI数据模型与局限证据总图.svg',aiFigure()],
 ['B-F00_6G协议调度与能量证据总图.svg',sixgFigure()],
 ['B-F04_正式实验设计与裁决协议总图.svg',formalFigure()],
 ['B-F06_可靠性失效边界与安全回退总图.svg',reliabilityFigure()],
 ['C-F04_工程架构与证据追溯闭环总图.svg',engineeringFigure()],
];
for(const [name,svg] of figs){fs.writeFileSync(path.join(OUT,name),svg,'utf8');await sharp(Buffer.from(svg),{density:300}).flatten({background:C.white}).png({compressionLevel:9}).toFile(path.join(PRE,name.replace('.svg','.png')));}
const all=fs.readdirSync(OUT).filter(f=>f.endsWith('.svg')).sort();
const manifest={schema_version:'report-figure-pack-v4',generated_at:'2026-11-08',status:'review_pending',master_format:'SVG',figures:all.map(file=>({file,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(OUT,file))).digest('hex')}))};
fs.writeFileSync(path.join(OUT,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
fs.writeFileSync(path.join(OUT,'README.md'),'# 报告科研图形 v4\n\n本目录包含六张证据密集型科研主图：AI+6G闭环证据、AI数据模型与局限、6G协议调度与能量、正式实验设计与裁决协议、可靠性失效边界与安全回退、工程架构与证据追溯闭环。\n\nSVG为170 mm矢量母版，PNG为300 dpi审阅预览。图题与完整图注由报告DOCX统一排版，见 `CAPTIONS.md`。正式实验图仅呈现实验设计与未完成状态，不含虚构结果。\n');
console.log(`generated ${figs.length} additional master figures; pack=${all.length}`);
