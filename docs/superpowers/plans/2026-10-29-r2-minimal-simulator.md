# R2最小确定性环境 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现可手算复核的任务—窗口—能量—发送最小闭环，完成用户指定四项首轮验收。

**Architecture:** energy分段Wh账本、link真实速率积分、queue因果过滤、engine内部状态与公共Observation隔离；配置显式synthetic，实际损失率只允许0。发送后保留在途，不生成接收成功或最终指标。

**Tech Stack:** Python 3.12、Pydantic 2.12.3、pytest 8.3.5；无新增依赖。

**Spec:** docs/superpowers/specs/2026-10-29-r2-minimal-simulator-design.md

## Global Constraints

- 不修改已冻结backend/contracts.py/configs/schema.json；不修改A/C源码或legacy。
- 秒/W/Wh/bit/s/byte；1Wh=3600J；32byte头、最大1024byte、ACK16byte仅留R3。
- 原117项契约和61项旧资产回归必须继续通过。
- 只输出真实执行的合成验证日志，不生成尚未实现的ACK、成功指标或API。

## Review Focus

- 有未来任务/未来健康/真实窗口时，Observation只包含当前可用信息。
- step跨过速率变化、窗口结束、任务到达和期限时不能凭空发送或提前调度。
- 大dt、0/NaN/Inf/bool及算术溢出不得污染状态或吞掉违例。
- 分段能量扣账与事件energy_Wh不得重复；clip前负值须可复核。
- 配置/Observation/next_state的修改不能污染原state或另一次运行；未ACK不减少队列字节。

### Task 1: 因果队列、窗口和能量原语

**Files:** Create backend/simulator/{__init__,energy,link,queue}.py；Test tests/test_simulator.py。

**Interfaces:** energy.advance_energy(E,capacity,dt,powers,tx_W)->EnergyLedgerEntry；link.transmission_time(windows,start,mode,wire_bytes,dt)->float|None；queue.visible_tasks(tasks,now)->list[Task]。

- [ ] 写失败测试：36W×100s从10到9Wh；0.1Wh遇36W×100s先记录-0.9再clip0；未来/过期任务过滤；无窗口/窗口末端/零速率不可发，8192bit/s发送1056byte耗时1.03125s。
- [ ] 运行pytest tests/test_simulator.py确认失败源于模块未实现。
- [ ] 实现有限数值验证、能量账本、分段速率积分与复制后的任务过滤。
- [ ] 运行上述测试通过并保存日志；提交原语及其测试。

### Task 2: 场景、observe/step与真实合成日志

**Files:** Create backend/simulator/engine.py、configs/parameters.csv、configs/scenarios/minimal.json；Extend tests/test_simulator.py；Create docs/handoffs/B_N2_R2_2026-10-29.md和本阶段证据。

**Interfaces:** 消费Task1原语及H00；create_state(config,run_id,policy_id)->SimulatorState、observe(state)->Observation、step(state,action,dt_s)->StepResult。

- [ ] 写失败测试：四项验收、单在途、无ACK不减remaining、功率/储备拦截、发送只扣实际时长、实例隔离、非法dt/config和预测/真值分离。
- [ ] 运行确认失败，再实现严格场景加载、深复制内部state、因果事件及演示导出。
- [ ] 运行场景和全库测试；演示导出与手算数值核对；验证Schema未改变。
- [ ] 一次独立完整审查，必要时通过失败测试修复重要问题；记录证据与A/C交接。
- [ ] 提交/推送B角色R2分支，创建草稿PR等待A验收；本轮不自动代签/合main。
