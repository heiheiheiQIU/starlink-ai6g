# B 数据审计接收与教师支持域复验

日期：2026-11-04；代码组合c9d4bdd（WP1@9f8491b + A657f39c + C63c7740）。用途：接收审计、回答A的reserve和扩样范围请求、准备WP2。不是新训练数据或算法效果实验。

## 实际运行

- `python -m training.audit_policy_dataset --output-dir runs/b_next_20261104/audit`：退出0；输出audit.json和README.md与A提交逐字节一致。
- `python docs/evidence/B/A_N4_readiness_2026-11-04/check_readiness.py runs/b_next_20261104/support`：退出0；直接读取冻结样本独立复算八项计数，6项reserve探针和10项教师支持域检查均通过。
- 全库：`python -m pytest tests -q --tb=short --noconftest -p no:cacheprovider --basetemp=runs/b_next_20261104/pytest --junitxml=runs/b_next_20261104/full.xml`：524 passed，1条既有AnyIO弃用警告，39.74 s。

解释：A原分支508项是其历史交付记录；B从WP1原519项纳入5项审计测试，实际524项。未重新构建前端：该目录源码和锁未变，沿用WP1记录。

## 文件

- verification.json：B独立计数、reserve成本/浮点边界、十类支持域及关键输入SHA。
- sources.json：本轮固定来源、候选、原始A审计的输出身份。
- full.xml：实际组合全库JUnit，保留原始字节。
- check_readiness.py：可复跑检查脚本；需要当前代码和测试夹具，不会写训练目录或训练模型。
- SHA256SUMS.json：本目录文件原始字节哈希（不含清单自身）。

复跑时使用新的输出目录，先创建runs及basetemp父目录，避免本机Temp权限问题。脚本对冻结20条仅重算统计，没有重新求解它们的全部标签；reserve/支持域探针是新构造的少量合成Observation，结果不进入训练集。A审计所列旧求解耗时不作为B的新性能测量。

边界详见[B支持域确认](../../../handoffs/B_teacher_support_2026-11-04.md)与[B有限签收](../../../acceptance/A_N4_dataset_audit_B_2026-11-04.md)。
