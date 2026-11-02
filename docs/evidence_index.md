# 星地智调证据索引

更新时间：2026-10-29  
用途：为报告、PPT、演示前端与答辩口径提供唯一的结论—证据映射。任何未绑定真实 `run_id` 的内容不得表述为实验结果。

| claim_id | 结论 | 证据等级 | run_id | policy_id | 源文件 | 生成命令 | 图表路径 | 负责人签核 | 可支持 | 不可支持 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C-UI-001 | H00 契约可驱动六步前端流程 | 契约样例 | 待真实 run | fixture-ui-v1 | `frontend/src/domain/flow.ts` | `cd frontend && pnpm test -- --run` | 待真实 run | C：待签核 | 页面结构、字段映射、交互链路 | 算法收益、真实时延、真实资源节省 |
| C-AI-001 | AI 助手能拒绝无证据的收益数字 | 单元测试 | 待真实 run | fixture-assistant-v1 | `frontend/src/domain/assistant.test.ts` | `cd frontend && pnpm test -- assistant.test.ts --run` | 待真实 run | C：待签核 | 防编造边界、引用入口 | 模型问答正确率、真实 RAG 效果 |
| EXP-001 | AI+6G 调度优于指定基线 | 待真实 run | 待真实 run | 待真实 run | 待真实 run | 待真实 run | 待真实 run | A/B/C：待签核 | 暂无 | 任何百分比提升或显著性结论 |
| EXP-002 | 健康风险驱动调度能改善关键遥测新鲜度 | 待真实 run | 待真实 run | 待真实 run | 待真实 run | 待真实 run | 待真实 run | A/B/C：待签核 | 暂无 | AoI、丢包率、时延或能耗改善数字 |

## 使用规则

1. 新增结论前，必须先新增 `claim_id`，再绑定不可变的 `run_id`、`policy_id` 和源文件路径。
2. 前端 fixture 只能支持“接口已打通、界面可交互、证据结构已定义”，不能支持算法优越性。
3. 报告、PPT 与答辩引用数字时，必须能从本表定位到原始产物和复现命令。
4. 真实 run 未完成时统一写“待真实 run”，不得用 `0` 代替缺失证据。
