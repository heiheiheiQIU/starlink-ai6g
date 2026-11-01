# PR #8 learned冻结包：B独立验收

日期：2026-11-01（香港时间）。固定候选：`11c00374d88dbbc5138c7b2c65029317befa989c`。

**整体结论：changes_requested。正常冻结包推理、归一化和既有网关回退子项通过；坏ZIP容器的受控错误约定需A补一项修订后复验。** 本回执不签收learned已接入Runner/API或算法效果。

## 已由B独立验证

- 模型五文件、运行/训练配置及manifest引用SHA一致，权重8数组的名称、形状、float32和有限性通过；数据/划分/合同/schema保持冻结。预检详情见 `A_N3_learned_intake_2026-11-01/intake.json`。
- 正式定向：**46 passed，1条既有Starlette/AnyIO警告**；固定候选全库：**501 passed，同一警告**。这是B实际结果，不引用A的79/92项计数。
- 20条冻结Observation实际推理的候选键完整、含唯一idle、分数有限，输入未变；额外inflight观测的发送候选=-1.0，无任务时保留唯一idle。
- B使用train的12个sample ID及其编码，以独立NumPy均值/标准差计算核对normalization；未使用validation/test拟合，全部匹配。
- 按三seed的validation total_loss独立核对选中20261033；源码先选seed再评test，冻结摘要一致。历史“test只执行一次”的运行次数不能仅靠产物独立证明，本回执确认的是代码控制流及记录一致，没有重训或重选冻结模型。
- 缺权重、错哈希、非ZIP文本格式错、NaN权重、非法Observation返回约定受控错误；独立评分异常和超时通过实际网关回退，分别记录MODEL_UNAVAILABLE、MODEL_TIMEOUT。
- B最终一次计时：冷加载并首评分约2.22ms；1000次warm median约0.499ms、p95约0.681ms、max约1.112ms。环境为本机B解释器，详细版本和原值见verification.json，不能当作目标卫星时延。

## 必修项：真正坏ZIP泄漏BadZipFile

位置：`backend/policies/learned.py::_load_bundle` 的np.load错误转换。

现有except覆盖OSError、ValueError、TypeError，但真正带ZIP签名而容器损坏的npz抛 `zipfile.BadZipFile`，不属于这些类型。B使用 `b'PK\x03\x04broken archive payload'` 并将测试配置哈希设为该损坏文件实际SHA，以到达格式检查；期望 `LearnedPolicyError(code='MODEL_FORMAT')`，实际泄漏BadZipFile。

新增接收人回归 `test_damaged_zip_is_controlled_model_format` 在固定候选上 **1 failed**；原501项全绿没有覆盖这个边界。普通文件损坏且哈希未变时仍会先被MODEL_HASH拒绝；现有ScorerGateway也会捕获一般评分异常并回退，因此本缺陷不等于已经证实API会崩溃或损坏权重被执行。

请A在加载器中将坏ZIP/CRC容器异常转换为MODEL_FORMAT，补真正损坏ZIP的回归，检查归一化/权重冻结产物不被改写。最小修订不要求重训、不改权重或重新选seed。A交新完整SHA及定向/全库结果；B对新版本复验该失败用例、正常包和回退后再升级签收。

## 证据及复现

证据：`docs/evidence/B/A_N3_learned_review_2026-11-01/`，含audit.py、verification.json、targeted.xml、full.xml、test_corrupt_npz.py及corrupt_npz_red.xml。

在B根目录执行接收人回归：

```powershell
python -m pytest docs/evidence/B/A_N3_learned_review_2026-11-01/test_corrupt_npz.py -q -p no:cacheprovider --basetemp runs/receiver_corrupt_npz_tmp_01
```

默认使用 `runs/b_learned_intake_20261101/source` 的隔离候选。异机或修订版通过环境变量B_LEARNED_SOURCE指定实际源码目录；必须与本机B代码隔离，避免导入另一个版本。修订前该回归预期失败，保留原始证据。

测试副本通过目录联接访问既有legacy资产，Git搜索上界设在审查目录父层，防止错误继承B仓库HEAD。测试涉及临时训练回归，但没有覆盖/重生成冻结训练目录或权重。

独立审查确认train统计与validation选择及20观测正常推理通过，并发现上述BadZipFile缺口，B随后独立运行接收人回归复现。初版审计用dict构造inflight产生一次Pydantic序列化警告，改为InFlight类型后重跑通过；未改A模型代码。

## 接入边界

这仍是20条合成初始观测的冻结小样本包。test四条命中不能支持泛化或策略收益结论；冻结摘要中idle基线test同样4/4，应在后续正式实验中使用EDF/value/learned及适当优化器对照。

B已准备接入路径，但正式模型包验收先按本修订收口。API三策略请求合同、服务监督推理进程、模型身份贯通和真实HTTP验收均独立推进，不能把已有线程超时回退当作生产进程回收已完成。main仍等待A的R2四手算及R5公平性两份回执。
