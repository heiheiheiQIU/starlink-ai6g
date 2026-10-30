# R3对C回执的修复记录

输入：origin/feature/frontend@abeda03中的docs/acceptance/B_R3_C_2026-10-29.md；原回执逐字保留在本分支，changes_requested未改。

I-01：retry_required_key锁定超时块；同task/block重试、有效ACK解锁、过期且残留事件处理完后退休。跨任务失败测试已先失败再通过。
I-02：Observation通过公开能量账本从最近可用健康观测的observed_at_s传播能量下界，包含太阳、背景、计算、收发；新观测重新锚定。多块储备、隐藏初始能量改变不影响公开下界、延迟健康及太阳输入三种行为均有回归。
I-03：只提供H00兼容离线文件，未提供EventsPage适配/五API，未声称C端到端已接入。
M-01：新日志显式LF。M-02：完整scenario进入input_hash/trace_hash。M-03：交接命令先建runs。M-04：无Git时使用显式发行标识或unversioned-source-sha256及逐源码SHA，不伪装Git提交。

6项新增回归：RED 6失败→GREEN；原64项加新6项定向70通过。修复实现提交e4953f4；本目录两例为其真实执行样例，不改写历史R3证据。第一次全库测试因测试期间提交使两个results.code_revision不同而失败；固定HEAD后重跑结果见verification.json。

R4已保留在feature/policies-r4，尚未交付签收；其教师边界审查还有两项已发现问题待修（巨大历史载荷的构建预算、非对齐剩余块状态）。独立审查会话因配额结束，不能宣称该次审查完整通过。后续须同步本R3修复并重新核验。
