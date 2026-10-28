# 星地智调 B角色工作路线与实施计划

> 后续执行者：按任务逐项使用 superpowers:executing-plans；本路线不授权立即实现所有产品模块。每项先做有意义的失败用例，再最小实现、验证和交接；执行状态以勾选及交接证据为准，未获授权不自动跨阶段。

**Goal：** 建立可信、可复现的单星回传系统，让A的评分真正影响通信动作，让C可以展示同一运行的过程、结果和证据。

**Architecture：** 环境持有隐藏真值；策略只读Observation。A输出健康估计及任务/模式评分，B负责约束解码、链路执行、独立评价、API和集成；C消费事件与结果，不另算科学指标。

**Tech Stack：** Python 3.12；已有A模块依赖NumPy/PyTorch。API建议FastAPI；优化器须在R4按安装可用性、状态/gap能力和20场景耗时选择，当前未冻结或安装。首版CPU可运行，GPU不作为演示前提。

**Spec：** 同级研发包中的WORKSPACE_HANDOFF、06完整方案、07排期、09详细手册、成员任务书00和B。技术合同冲突以09补充为准，赛事事实另查Require原件。仓库CONTRIBUTING定义分支及所有权。

## 1 先认识自己的工作

你的链路：明确输入格式 → 模拟通信及能量 → 建立公平基线/教师 → 接收AI评分 → 提供API → 产出可复算实验 → 交付技术材料及运行包。

你不训练A的网络，不替A批量整理教师样本，不替C画页面。队长身份未确定，报名行政工作不默认归B。遇到跨模块问题，给拥有者最小复现和日志；代改须登记并复核。

本路线是执行顺序，不是已经完成的声明。工作区准备完成不等于H00验收通过。

## 2 当前起点（2026-10-28本机检查）

- 起始提交：`f048da9`。仓库已有A1旧资产审计与离线推理，未实现B仿真/API和完整通信闭环。
- A1返回LegacyPrediction，不是正式HealthEstimate；正式健康估计和学习评分器尚缺。
- 已有公共合同草案，但contracts.py、schema、H00交接和验收回执尚缺。
- 研发包此前148文件大小/SHA核验通过；不是旧模型科学验证或新实验验收。
- 本机资料包与仓库并列；默认资产配置多了一层“交付包”。工作区准备提供忽略提交的本机配置，团队默认配置保留。
- 旧README引用的外部A验收报告和旧venv在本机不存在；不得照抄其测试数字作为本机结果。
- 新仓库排期晚于09部分日期，尚不能据此视为团队已共同批准改期。

## 3 全局约束

- 单星、单网关、多窗口；从星上队列到网关确认。无真实射频、星间路由、完整6G空口或在轨验证。
- schema_version="1.0"；秒、W、Wh、bit/s、byte；1Wh=3600J，1byte=8bit。数值有限，缺失用null及原因。
- AI只给任务×idle/robust/fast候选评分；实际字节量由guard按约束确定。所有在线方法同观测、同协议、同外部轨迹。
- 首版设计：1秒步长、最多3窗口预测；最大有效块1024byte，头32byte，ACK16byte，单在途，ACK延迟1步、超时2步。均为待参数台账冻结的仿真假设。
- 先处理接收/ACK及到达，再判断过期，再观测/决策/推进；接收时间<=deadline算按时；窗口[start,end)，发送须在end前完成。
- 网关成功与星上确认分开；ACK丢失可重传，但网关去重。环境能量裁剪前记录真实违例。
- 失败任务进入应评价分母，期限超评价终点的任务单列；无成功有效字节时J/bit=null并给NO_DELIVERY。
- synthetic、fixture、历史回放及新实验明确区分；不改legacy，不用冻结预测/计划收益冒充新结果。
- 三方合同确认、相邻成员复核和真实日志不能用作者自检代替。

## 4 优先核查的五类风险

1. 断窗时数据在途或ACK未到：R3验证已发数据不凭空消失、重传不重复收益。
2. deadline与接收同刻及跨期限分块：R3验证<=边界与部分接收不能算任务完成。
3. 错误单位和clip掩盖负能量：R2验证36W×100s=1Wh及裁剪前违例。
4. 模型/健康缺失或未来信息泄漏：R1/R4/R6验证结构隔离、available_at和受控fallback。
5. 多策略事件混流、刷新和最后一页日志遗漏：R5验证policy_id、游标和完成后排空事件。

## 5 路线与验收门

| 顺序 | 交付目标 | 主要接收人 | 依赖 |
|---|---|---|---|
| R0 | 本机环境与可追溯基线 | B自检，A复核A模块相关问题 | 当前工作区 |
| R1 / H00 | 公共合同能供A/C独立工作 | A、C | 09与合同草案 |
| R2 | 能量、窗口、队列最小环境 | A | R1 |
| R3 | 发送—接收—ACK无AI闭环 | A核指标，C试读日志 | R2 |
| R4 / H02 | 公平基线、guard、优化教师 | A | R3 |
| R5 / H03 | CLI与五接口，C能联调 | C | R3；正式策略入口依赖R4 |
| R6 / H01/H04 | 正式健康及学习评分接入 | B主验A交付，A复核集成 | R4与A交付 |
| R7 / H05 | 固定测试与统一实验 | A复核，C读取结果 | R4/R6；测试名单须提前冻结 |
| R8 / H06—H08 | 技术供稿、换机、发布签核 | C、队长 | R5/R7 |

### R0：确认环境基线

Files：`.venv/`、`configs/legacy_assets.local.json`、`runs/workspace_baseline/`；必要的环境说明写入README，跨A模块变更先登记。

- [x] 安装仓库固定的直接依赖到独立venv，记录解释器、平台和实际依赖版本；不借用队友venv。
- [x] 检查本机配置引用的NPZ、CSV、权重及来源清单，哈希核对后再做旧资产相关运行。
- [ ] 记录默认配置与本机布局的差异；现有测试硬编码默认配置，先与A约定可复用的配置注入方式，不改legacy原件。
- [x] 用 `.\.venv\Scripts\python.exe -m pytest tests -q --noconftest -p no:cacheprovider` 建立基线；保存命令、退出码及失败原因到runs，不把路径/依赖失败当算法失败。
- [x] A1重跑若需要，使用本机配置和独立输出路径；不覆盖docs/evidence/A1。

2026-10-28执行记录：安装/哈希/真实前向已通过。原命令4通过、5失败、52错误；将pytest临时目录放入工作区后36通过、5失败、20错误，剩余均为默认资产路径缺失。提交9acbd6b的隔离快照仅替换资产配置后61通过。主仓库配置未修改，A尚未复核通用配置注入方案；状态ready_for_review，不能标accepted。证据见 `docs/evidence/B/R0_2026-10-28/README.md`。可继续R1合同工作，不得把这批证据称为通信实验。

出口：依赖/路径问题有明确结论，基线结果可定位。未通过不宣称运行就绪；H00文档工作可继续。

### R1：H00公共合同（第一项产品任务）

Files：创建 `backend/contracts.py`、`configs/schema.json`、`tests/test_contracts.py`、`tests/fixtures/`、`docs/handoffs/H00_contract.md`；完善 `docs/contracts/README.md`。

接口：集中定义Task、Window、HealthEstimate、InFlight、Observation、CandidateScore、Action、Decision、Event、SimulatorState、StepResult、TeacherResult及结果合同。保留00规定函数签名，后续任务不得另造类型。

- [x] 列字段差异：09的decision事件使用latency_ms；仓库Decision使用decision_latency_ms。按09明确事件序列化映射，内部字段与线上字段不能混用。
- [x] 写失败契约用例：负字节、NaN/Inf、deadline<=arrival、错误位置、非法概率、重复候选、非队列任务引用、缺失/多个idle均拒绝；合法缺失RUL保留null+reason。
- [x] 运行契约测试确认失败，再实现最小类型及schema校验。
- [x] 验证Observation不包含真实容量、未来实际任务/信道或接收端未ACK真值；为环境内部状态定义清晰边界。
- [x] 补齐09的事件分页、错误码、decision/snapshot字段和六个契约场景fixture。fixture显式标识非实测；行为实现分别由R3—R6验收。
- [x] 运行 `python -m pytest tests/test_contracts.py -q`，准备A/C字段字典、合法/非法样例、CHANGELOG和H00发送单（尚未代发或签收）。
- [ ] A/C独立检查后填写回执；此前状态只到ready_for_review，不自行标accepted。

2026-10-28：H00候选实现及75项契约测试完成；同环境旧代码回归需本机资产配置。详见 `docs/handoffs/H00_contract.md` 和 `docs/evidence/B/H00_2026-10-28/README.md`。真实guard、仿真与API尚未实现；对09留白的字段细化列入合同CHANGELOG等待A/C确认。

### R2：最小窗口、队列与能量

Files：`backend/simulator/{energy,link,queue,engine}.py`、`configs/parameters.csv`、`configs/scenarios/minimal.json`、`tests/test_simulator.py`。

接口：`observe(state: SimulatorState) -> Observation`；`step(state: SimulatorState, action: Action, dt_s: float) -> StepResult`。

- [ ] 参数台账逐项写数值/范围、单位、来源或synthetic、敏感性范围、负责人及版本。
- [ ] 先写确定性验收：净负载36W持续100s使能量下降1Wh；无窗口发0byte；负能量在clip前被记录；到达前不可调度。
- [ ] 实现一个任务、一个窗口、固定容量的环境；SOC与容量/RUL分离，电源账本包含背景、发送、接收/控制及计算开销并防重复计账。
- [ ] 公共随机过程按时间索引；预测与环境真值分开；不同策略队列/能量独立。
- [ ] 运行 `python -m pytest tests/test_simulator.py -q`，交A手算场景与能量日志。

### R3：分块、ACK与无AI闭环

Files：继续R2环境；增加 `backend/evaluation.py`、`tests/test_evaluation.py`，生成 `experiments/runs/<run_id>/` 六件套。

接口：沿用step；`evaluate(events: list[Event], config: dict) -> dict`，策略不能回读评估真值。

- [ ] 先写断窗ACK丢失→下一窗超时重传→网关去重用例；第一次完整接收时刻决定业务成功。
- [ ] 写期限边界：接收恰好等于deadline成功，晚于失败；跨期限只收部分不算任务完成，但去重有效字节计入goodput。
- [ ] 实现1024/32/16byte、单在途、延迟及超时合同；窗口关闭不抹去已发数据的传播事件。
- [ ] 手算权重2与1的两任务：只有前者按时完整接收，交付率=2/3；未到期任务单列，无成功字节J/bit=null。
- [ ] 导出config、manifest、status、events、results、execution.log，只有完整写出才completed。
- [ ] 运行仿真及评价测试，A复算因果与分母，C检查同run_id事件可用于页面；无AI闭环通过后再扩模型训练。

### R4：guard、基线与优化教师

Files：`backend/policies/{edf,value,guard,teacher}.py`、`configs/teacher.json`、`tests/test_policies.py`、H02交接。

接口：`decode_safe(obs: Observation, scores: list[CandidateScore]) -> Decision`；`solve_teacher(obs: Observation, budget_ms: int) -> TeacherResult`。

- [ ] 先写空队列idle、无窗口NO_VISIBLE_WINDOW、低能量ENERGY_RESERVE、非法评分INVALID_SCORE的测试；同时检查数据位置、在途和功率约束。
- [ ] 实现EDF及价值规则，两者与AI共用同观测和guard；不要制造不懂电量的弱基线。
- [ ] 用期限冲突、能量不足、空闲有利三个小场景验证教师完整任务收益；平局按低耗能、早截止、小task_id。
- [ ] 选择可安装且能报告求解状态/gap的优化器；超时可行解不是最优解，未知gap=null。oracle与在线教师分离。
- [ ] 先20场景计时：最多12任务、4状态、25动作、120有效发送时隙，单候选0.2秒，总8 CPUh；短场景期限覆盖时域，断连段不展开巨量变量。
- [ ] 冻结验证期比较预算：初设在线100ms、宽松2s；必要变更统一适用于比较方法并留记录。
- [ ] 运行 `python -m pytest tests/test_policies.py -q`；向A交一条可独立生成标签的命令、20场景、版本/状态/gap/耗时说明。批量样本管线归A。

### R5：CLI、API与C联调

Files：`backend/cli.py`、`backend/api/main.py`、`tests/test_api.py`、README、依赖记录、H03交接。

入口：`python -m backend.cli run --config <path> --output <dir>`。HTTP为POST /runs及GET状态/events/results/export五接口，遵守09第16节。

- [ ] 先测非法输入422、缺ID404、未完成/失败结果409、容量不足429和统一错误体。
- [ ] 实现不可变config、新run_id、最多两策略对照；event_id在run内跨策略单调递增，每条有policy_id。
- [ ] 分页默认500、最大2000；完成后仍读到has_more=false；测试刷新恢复及两策略隔离。
- [ ] 导出只含本run文件，不接受任意路径；结果含配置/输入/代码及逐策略版本哈希。
- [ ] 运行 `python -m pytest tests/test_api.py -q`；交C正常、运行中、失败fixture及真实基线run、启动命令和字段字典。
- [ ] C确认刷新不重复创建、参数改变生成新run、页面数字与export一致；暂停/单步/倍速仅前端回放。

### R6：验收A的健康接口及AI评分

Files：B维护集成入口及策略测试；A维护 `backend/health/estimator.py`、`backend/policies/learned.py`及模型包。B填写H01/H04接收回执。

消费：`estimate_health(history: list[dict], now_s: float) -> HealthEstimate`；`score_actions(obs: Observation) -> list[CandidateScore]`。

- [ ] 健康验收1成功、1缺失RUL、1错误输入；检查available_at，不把cycle/orbit当秒或raw_fraction当SOC。
- [ ] A未交付时使用明确标注synthetic的健康配置，真实/模拟来源写入manifest；不宣称旧模型复用成功。
- [ ] 验收模型包的权重、配置、特征顺序、归一化、模型卡、smoke样例、训练清单、依赖和SHA；只给pt文件拒收。
- [ ] 测模型缺失/NaN/超时/无解回退；三种扰动为缩短窗口、插入任务、降低能量，检查合理动作变化，不要求必然提高收益。
- [ ] 运行受影响策略/集成测试并保存实际前向日志；B签接收结果，A复核在线信息边界。

### R7：冻结测试、统一评价与收益审查

Files：`experiments/test_matrix.json`、`optimizer_subset.json`、`docs/metrics.md`、每run证据及per_run.csv/summary.csv。

- [ ] 看结果前固定18工况=3负载×3能量×2扰动，每工况10轨迹；优化子集固定每工况前3条，共54条。
- [ ] A签核拆分无泄漏并交三个训练种子模型；不把重复环境轨迹当独立样本。
- [ ] 完善统一指标：加权按时完整率、关键任务成功率、goodput、最低真实SOC/违例次数与时长、J/成功bit、等待与决策P50/P95、超时率。
- [ ] 所有策略共享外部环境；规则模型hash=null；记录失败和未到期任务，保留零/负收益。
- [ ] B运行基线和集成策略，A提供消融配置/模型；A抽两条日志手算，C使用同结果作图。
- [ ] 仅在预定54条配对子集报告相对优化器差距/加速；置信区间按独立轨迹处理，模型种子分别报告。
- [ ] 三人签可写/不可写结论。5个百分点、2%差距、3倍加速是研究目标，不是既有成果或必须造出的结果。

### R8：技术供稿、换机与发布

Files：`docs/contributions/B/`、README、环境/资产清单、H06/H07/H08；C编排正式材料。

- [ ] 给C通信、实验、复现正文及3—4页技术PPT原稿；每张图带源CSV/JSON、命令、单位、图注、run_id及局限。
- [ ] C在第三台机器独立按README启动；记录额外步骤并修复，分别验收回放、真实前向和训练，不用口头补丁冒充一次成功。
- [ ] 冻结代码、模型、数据清单与SHA；A签模型数据、C签页面材料、B签系统，队长负责最终提交。
- [ ] 正式材料规则核验读取Require原件；匿名材料不包含研发包、本机路径、账号或学校信息。
- [ ] 下载发布副本检查哈希与启动，保留真实日志。没有接收回执不标整体完成。

## 6 排期使用方法

按R0→R8依赖推进，不以日历已经过去推定任务完成。B总预算53h沿用任务书：B1合同环境15h，B2基线教师14h，B3接口复现8h，B4实验材料16h；R0消耗准备/缓冲，不凭空增加可用工时。

| 节点 | 09/原计划 | 仓库后续排期 | 本路线处理 |
|---|---|---|---|
| H00 | 10/27 | 10/28 18:00 | 第一优先，实际交接时间如实记，需A/C回执 |
| H02 | 10/29 | B-N2为10/30 20:00 | 记录延期风险，先无AI闭环，再教师 |
| H03 | 10/30 | 10/31 20:00 | 提前给C同schema fixture；不能替代真实联调 |
| 测试冻结 | 11/02 | 11/02 | 不因实现延期偷偷看结果后改测试 |
| 收益审查/技术稿 | 11/04—05 | 11/04—05 | 无收益就降低主张，保留证据 |
| 功能冻结/换机 | 11/06、11/08 | 延用原计划 | 失败优先修复，不加增强项 |
| 发布/内部提交 | 11/11、11/12 | 延用原计划 | 赛事截止另核Require及当日平台 |

本表不是对团队截止的新承诺；日期冲突需同步A/C。优先砍3D、多星、聊天、在线训练和扩样，保留公平基线、数据真实性及验收。

## 7 第一工作日安排（约3.5小时）

1. 15分钟：确认角色、上游和H00字段差异，记录队长/接收人待填项。
2. 30分钟：R0环境与路径基线，明确失败来源；不要在恢复全部旧训练上消耗整天。
3. 90分钟：R1公共合同、合法/非法fixture及契约测试。
4. 45分钟：整理字段映射、错误码、H00发送单，交A/C评审。
5. 30分钟：保存验证日志、更新本人任务状态和下一步；H00提前准备好才开始R2参数台账。

当日目标：可供A/C审查的H00包，不是完成全部B1。不能把等待签收的合同标为accepted。

## 8 执行记录格式

每次交接必须包含：任务ID、版本/commit/schema、输入路径/SHA、产出清单、工作目录与命令、实际日志、失败/未验证项、接收人的检查动作。

状态：not_started → in_progress → ready_for_review → accepted；退回为changes_requested。阻塞写责任人、最小复现和下一动作。只更新本人条目，不代A/C签核。

执行每个任务后做相应最小测试，再提交相关文件到feature/simulator；合入main需相邻角色复核，公共合同需三方确认。本路线无代码实现通过声明。
