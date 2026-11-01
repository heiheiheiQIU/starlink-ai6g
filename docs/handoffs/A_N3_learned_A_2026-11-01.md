# A-N3 learned 评分器交接

日期：2026-11-01（Asia/Shanghai）
负责人：A
验收人：B
状态：**ready_for_B_review**
分支：`codex/a-n3-learned`

## 本次交付边界

本次交付 A-N3 的小样本 learned 评分器、冻结模型包、训练与推理代码、回退测试和可复核证据。正式入口为：

```python
backend.policies.learned.score_actions(observation)
```

输出始终覆盖 Observation 对应的完整候选键集合；结构上不可执行的发送候选保留在集合中并赋冻结掩码分数 `-1.0`。模型加载、哈希、格式、非有限数和输入错误均转为受控 `LearnedPolicyError`，由既有 `ScorerGateway` 在异常或 100 ms 超时时回退。

本交付没有修改 `backend/contracts.py`、`configs/schema.json`、旧教师数据、legacy 原件或 B/C 接口，也没有把 synthetic 小样本结果表述为真实星上效果或泛化结论。

## 提交与产物

- 训练代码所用源码修订：`ff0589bfa465585158f76818a422ce6def3efc15`
- 冻结模型包提交：`7f18ff240201ce7954f71df2238bf28123ab54dc`
- 网关与训练配置回归提交：`e15048dcb97b155fb85e9ffa3967e3f429b99639`
- 模型目录：`artifacts/models/a_n3_policy_v1/`
- 运行配置：`configs/learned_policy.json`
- 训练配置：`configs/policy_train.json`
- 训练证据：`docs/evidence/A/A_N3_training_2026-10-31/verification.json`

冻结包 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `weights.npz` | `a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a` |
| `normalization.json` | `5c5fd7e843817a63ed6c486ed1c2a525243a724a6573b01681e0aa53811d2449` |
| `training_summary.json` | `fc011b87f2fdeaa0c0cd74b1de7f573d352902098ea0ca83c06f182faab672a3` |
| `model_card.md` | `7574292556c2500451b326ecf0ab4e924790dc84924b2dab253d380fdfaf87d7` |
| `manifest.json` | `949370f65165437a95b5858b23103b6cac892913592d1a4b54a3d3d4d27445a8` |

## 模型与训练约束

- 输入：冻结 `policy-features-v1`，14 个全局特征 + 9 个候选特征，共 23 维。
- 网络：共享 `23-32-16` MLP，utility sigmoid 头与 feasibility logit 头。
- 损失：soft-target utility BCE + `0.25 ×` feasibility BCEWithLogits。
- 数据：20 条 synthetic 教师样本，按 source group 冻结为 train/validation/test = 12/4/4。
- 归一化：只拟合 train split。
- 种子：`20261031`、`20261032`、`20261033`；按最低 validation total loss、同分取较小 seed 选择。
- 选中 seed：`20261033`。
- 训练门槛：12/12 optimal-set hits；train utility MSE `5.849076778474682e-11`，低于 `0.001`。
- 一次性 test 描述值：4/4 optimal-set hits、utility MSE `0.356253057718277`、feasibility accuracy `0.6666667461395264`。

test 指标只用于记录冻结小样本的行为，不证明模型泛化，也不证明优于 EDF/value/其他策略。

## 运行与回归证据

- 20 条冻结 Observation 均返回完整、有限候选分数。
- 冷加载并首次评分：`2.6265 ms`。
- 1000 次 warm inference：median `0.52445 ms`，p95 `0.68487 ms`，max `1.15960 ms`。
- 模型/训练/数据/特征定向：`55 passed`。
- learned 网关和运行时定向：`20 passed`。
- 最终 A-owned 定向集合：`79 passed in 6.17s`。
- 全库有一轮 `498 passed, 1 warning in 27.83s`；最终重复运行得到 `497 passed, 1 failed`，失败点是 B API 的 `RunService.status()` 在 Windows 下读取 `status.json` 时偶发 `PermissionError`。
- 对该 B API 用例连续复跑时前 4 次通过、第 5 次复现同一文件锁错误；A 未修改 B 的 API 实现或接口。
- `pip check`：`No broken requirements found.`

全库测试在当前锁定依赖环境中运行；warning 是 Starlette 对 AnyIO 旧别名的上游弃用提示，与本交付无关。A-N3 定向集合稳定通过，但全库当前不能表述为稳定全绿；B API 文件锁波动需由 B 单独处理。

冻结身份复核：

| 对象 | SHA-256 |
|---|---|
| `data/teacher/a_n3_20_v2/samples.jsonl` | `2df964e78a6bf6220b4c48c92b29f4838d01af13281f41f666a306e96c5b8957` |
| `data/teacher/a_n3_20_v2/splits.json` | `8826732869e9452d2f8e59889240b034e393d7c748429f3dc1020cf90967d1f8` |
| `backend/contracts.py` | `78f783e8fb1f3ea25bf001a474eb4467e1bfcaee74888597901f2a4f352fd814` |
| `configs/schema.json` | `d1a19c098b8c69ba7ebefc19db60c1e3f0f321c38b5f669518e7f05676b89fcb` |

上述四项相对基线 `2cfe89c` 无差异。

## 请求 B 独立验收

请 B 在固定候选提交上独立执行：

1. 核对模型包五个文件、运行配置和训练配置 SHA-256，并检查 manifest 引用一致。
2. 用 `allow_pickle=False` 读取 `weights.npz`，核对数组名、形状、`float32` 类型和有限性。
3. 复跑 `tests/test_policy_dataset.py`、`tests/test_policy_training.py`、`tests/test_learned_policy.py`、`tests/test_policy_runner.py`。
4. 对 20 条冻结 Observation 复算候选键集合、有限分数、结构掩码及输入不变性。
5. 注入缺文件、错哈希、坏格式、NaN、评分异常和超时，确认均产生受控错误或 `MODEL_UNAVAILABLE`/`MODEL_TIMEOUT` 回退。
6. 核对教师样本与 12/4/4 source-group 划分身份，确认训练只使用 train 归一化，test 只在 seed 选择后评估一次。

B 的验收范围应写为“learned 小样本冻结包与接口行为”，不能扩展为策略泛化、真实卫星效果或算法优越性结论。

## 后续接口

B 验收通过后，可按现有五接口把 learned 作为新 scorer 接入；A 不擅自修改 B 的仿真/调度接口。若 B 要求新的规模化教师数据或接口字段，需另立变更记录并重新冻结，不能覆盖本目录或回填本次哈希。
