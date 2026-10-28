# H00手工契约样例（非实验结果）

入口是manifest.json。每个JSON文件外层包含kind=contract_fixture、is_experimental_result=false和examples；模型校验或页面开发取examples[].payload，不把外层当API响应。

- observation.json：正常任务/窗口/健康观测与事后snapshot。
- invalid.json：非法字段、类型、边界；schema_rejects=false表示必须由Python语义校验拒绝。
- 01—06：空队列、无窗口、低能量、断窗ACK丢失/重传、模型失败、页面刷新分页。
- http.json：创建/运行中/失败及五个错误码，不表示端点已实现。
- results.json：有交付和零交付时的结果结构；占位哈希和指标不得引用为实测。

六场景的expected_behavior是后续模块应实现的验收条件，behavior_verified=false。H00测试只证明结构和指定语义校验工作，不能证明真实调度、能量守恒、网关去重或页面恢复已实现。

NaN/Inf不是合法JSON，文件用字符串错误样例示意；运行时非有限浮点由pytest直接构造验证。健康参数和输出全部synthetic。

在仓库根运行 `python -m pytest tests/test_contracts.py -q --noconftest -p no:cacheprovider`，可用Pydantic及独立JSON Schema校验器检查样例。完整字段/单位及语义限制见docs/contracts/README.md。
