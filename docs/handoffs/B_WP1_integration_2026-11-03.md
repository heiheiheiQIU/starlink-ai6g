# B WP1：统一集成候选交接

日期：2026-11-03（UTC+8）。任务：优化方案WP1。状态：**ready_for_review**，统一运行候选已形成；尚未更新共享main。本文不是learned完整接入或AI效果验收。

## 来源与层次

基于远端main@75f1c52，在当前检出建立B分支 `codex/b-wp1-integration-20261103`。原分支、PR及未提交的优化方案文档均保留。依赖集成产生以下提交，完整SHA与来源见证据verification.json：

| 层次 | 来源 | 集成提交 | 本轮全库 |
|---|---|---|---:|
| R2 | d4716bf | a0254f8 | 219 passed |
| R3 | cac4b90 | d554472 | 248 passed |
| R4 | 9304766 | 32b7662 | 293 passed |
| R5及后续B修复 | 971f221 | 0d376f5 | 312 passed |
| A冻结模型、特征、训练及健康适配 | 1c90246 | 82e4819 | 与回执一起验证519 passed |
| A R2/R5原始回执 | ddcca9c | b79b7bf | 包含在A组合验证 |
| C前端与回执 | 49d9385 | 87a4220 | 后端519 passed；前端61 passed及构建 |

源码运行候选为87a4220；其后的本轮提交仅整理入口文档、任务板、证据和证据文件属性。发布/复核时同时记录最终head和verification.json中的runtime_commit，不将历史来源SHA伪装成组合head。

## 实际验证

- 开始前B基线312 passed；每层新建工作区basetemp并保留JUnit，失败/错误/跳过均为0。
- A并入后全库519 passed；C并入后再次全库519 passed。均有一条既有AnyIO弃用警告。
- Node 24.15.0、pnpm 11.25.0：`pnpm --dir frontend install --frozen-lockfile`退出0；唯一锁文件未改变。安装有下载慢与重试，最终成功。
- `pnpm --dir frontend check`：16文件61项测试通过；TypeScript noEmit与Vite生产构建通过。
- 真实uvicorn及Vite生产预览代理：经前端代理POST创建EDF/value新run，轮询完成，读取结果，按limit=2读18页、36条事件，下载ZIP；事件逐项与ZIP一致，子运行seed和全部manifest产物哈希通过。
- run_id：`run_152f00fd26b74a2ea86cf2a31308c88b`，seed=7。请求、运行均为synthetic；不表示新AI结果。原始运行保存在本机runs/api，ZIP在runs/wp1_20261103/http，未将ZIP重复提交Git。
- 冻结模型全部manifest文件哈希通过，对一条冻结Observation实际评分；每任务robust/fast与唯一idle齐全且评分有限。POST learned受控422，准确反映WP2尚未实现。
- 验证启动的两个服务均已停止。HTTP/代理检查不是浏览器点击、视觉或第三台机器验收。

## 冲突决策与跨角色影响

1. A与C合并均仅在 `docs/task_board.csv` 产生文本冲突。保留B最新有限验收状态，采用C最新C-N3实施进度；历史签收不扩大为完整产品签收。
2. A原配置把旧资产放在仓库内ignored交付包；当前B配置使用兄弟交付包，且本机已有冻结资产。保留B的 `configs/legacy_assets.json`，README记录恢复布局；未改旧数据、旧权重或原包清单。
3. API service/worker、合同及Schema与B@971f221逐字节一致；A的health、learned、training、五文件模型与其候选一致。C除README外的61个文件经Git规范化与原分支一致；Windows core.autocrlf使部分前端文本工作副本为CRLF，证据明确记录该差异，不声称所有工作副本原字节相同。
4. 重写根README，将过时入口存入docs/history。仅修正C的frontend/README.md：使用现有同源代理、准确环境变量名及现有pnpm锁文件，说明页面导出仍待联调。没有改C运行源码。请C复核该文档变更。
5. .gitattributes仅增加本轮XML/log的原字节保留规则；不修改公共合同、接口数量或策略上限。

## 下一步

- A/C：复核本统一候选、任务板状态与上述集成决策；原回执仍按各自范围生效。本次新组合候选的复核是进入main前的交接要求，不因原分支测试通过而代签。
- B：按WP2接入learned完整候选检查、Guard、受监督推理进程和五接口。保留正常idle、同块重传和失败回退；当前独立模型推理不等于运行接通。
- C：在统一候选开展真实页面消费、预设请求、ZIP下载与双分辨率验收。现有比较页仍有fixture内容，不能写成已完成现场重算。
- 正式18×10、强优化器、扩样/消融、换机和参赛材料按优化方案继续；本轮未产出learned收益结论。

证据与复跑：[WP1验证目录](../evidence/B/WP1_integration_2026-11-03/README.md)。
