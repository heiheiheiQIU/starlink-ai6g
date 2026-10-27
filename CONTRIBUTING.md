# 星地智调协作规则

本仓库是三人唯一代码协作入口。正式截止为2026-11-13 20:00（北京时间），内部提交为11月12日20:00。

## 分支与合并

- `main`：仅放已经验收、可复现的集成状态；禁止直接开发。
- `feature/ai`：成员A，数据、健康估计、学习策略、训练与消融。
- `feature/simulator`：成员B，公共合同、仿真、基线、教师、API、集成与复现。
- `feature/frontend`：成员C，前端、接口联调、证据索引、报告/PPT/视频材料。
- 每人只在自己的分支提交。需要跨目录修改时，先在`docs/handoffs/`写原因和影响，再由目录所有者复核。
- 合并到`main`必须经至少一名相邻角色复核；公共合同变更需要A/B/C三方确认。
- 禁止强推`main`，禁止重写已经交接的提交历史；错误通过新提交修复。

建议提交信息：`类型(模块): 动作`，例如`feat(health): add conservative estimate`、`test(api): cover running result conflict`、`docs(handoff): deliver H02 teacher interface`。

## 开工与收工

开工前：

```powershell
git switch <自己的分支>
git pull --ff-only origin main
git merge --ff-only main
```

每日收工前：

1. 更新`docs/task_board.csv`对应任务状态和产物路径。
2. 运行本人任务的测试及相邻合同测试。
3. 在提交信息或handoff中记录命令、结果、未验证项。
4. 推送自己的分支，发起PR到`main`；PR模板不得删减。

## 目录所有权

| 路径 | 主负责人 | 必须复核者 | 说明 |
|---|---|---|---|
| `backend/contracts.py`、`docs/contracts/`、`configs/schema.json` | B | A、C | 公共合同，未经三方确认不得破坏性修改 |
| `backend/health/`、`backend/policies/learned.py`、`training/` | A | B | 健康输入和AI评分；不直接执行通信动作 |
| `backend/simulator/`、`backend/policies/{edf,value,teacher,guard}.py` | B | A | 环境真值、基线、教师、安全解码 |
| `backend/api/`、`experiments/` | B | C | API、运行目录、统一评价 |
| `frontend/` | C | B | 只消费公共合同，不自算另一套指标 |
| `docs/report/`、`docs/slides/`、`docs/video/` | C | A/B按技术章节 | 材料整合和匿名检查 |
| `docs/contributions/A/` | A | C | A的技术原稿和证据索引 |
| `docs/contributions/B/` | B | C | B的技术原稿和证据索引 |
| `tests/fixtures/` | B主、A/C评审 | 三人 | 契约样例必须标识fixture，不冒充实验结果 |

## 数据与大文件

- `.pt`、`.npz`、ZIP、虚拟环境和运行产物不提交Git；在文档记录来源、SHA256、大小和恢复步骤。
- 当前A1冻结资产来自v3团队包，路径由`configs/legacy_assets.json`解析；团队电脑路径不同可用环境配置适配，禁止改写冻结资产。
- 每个实验数字必须能定位到`run_id`、配置哈希、模型哈希、代码提交和原始日志。

## 完成定义

任务只有同时满足以下条件才能标`accepted`：代码/文档存在；验证命令通过；日志或run可定位；接口未私改；失败和未验证项已写明；接收人完成复测。`mock`、`fixture`、旧指标和设计目标不能写成新系统实测结果。
