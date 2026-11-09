# A 对 formal_v2 实际候选的来源、划分与泄漏复核

> 日期：2026-11-10  
> B审查对象：`codex/b-formal-handoff-20261109@b4faac9d687c3a5b47db19d06f9e5b72cd185e05`  
> C库存复核：`codex/c-formal-candidate-review-20261109@d98052d03db0246c2280143744e1dd7c68fafdb5`  
> 生成代码：`48157a8f4a1cdd7770685b79deb3fe4524b1bf7d`  
> A裁定：`accepted_with_notes`  
> 正式运行授权：`false`

## 1. 裁定

A接受本批180条实际候选的来源排除、训练/验证/测试划分边界以及当前可验证的泄漏检查。A/B/C三份生成前回执已由冻结生成器核为同一subject；此前“缺少C原始生成前回执”的判断已经过期。

本回执完成A负责的第二阶段人工复核，但还不是 `review/A.json` 最终冻结签名，也不授权540次正式运行。交付包中的 `review/leakage.json` 仍为 `status=pending`；A/C必须共同确认最终 `accepted` 字节，A/B/C再把同一个最终SHA写入正式回执，冻结工具通过后才可启动正式运行。

## 2. 冻结对象

| 对象 | SHA/版本 |
|---|---|
| candidate manifest | `2b0814db44b7c70cd94e44608e34c762ffaa86969ea6f955e4736b7b3cdcd31f` |
| 当前 leakage 草稿 | `8bc1909e6d83f51c9a54813d989f4388c0d4aeb64ea5e00e793e717b06dbe0e8` |
| binding | `d2b596d852758c9514f2aa7b735f4cd1f31dbfbee0c23af50619fd51ecad5e2a` |
| code content | `88e44ec10e33e7f15e81b335894762197d8aec95698e932b1ef314f894cc9889` |
| model config | `518c447945783600060ab6c404186f9dc2e78f107be317fa9b26b62a448fdee2` |
| analysis protocol | `649ecfc8c94c37f8118ae4996947df215ce6c7ed13a8e2ee55db267a5e0c1e1f` |
| frozen model weights | `a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a` |

## 3. A独立机器复验

1. 在导出的冻结提交 `48157a8` 上运行正式链路、冻结、分析、划分、特征和Learned策略测试：`124 passed`。
2. 冻结生成器接受三份原始生成前回执，并验证候选清单为180条。
3. 从三份回执重新生成候选目录；182个文件与B交付逐字节一致，manifest SHA仍为 `2b0814db...`。
4. 独立重跑 `prepare_formal_v2_review`；生成的 `leakage.json` 与B草稿逐字节一致，SHA仍为 `8bc1909e...`。
5. 18个工况各10条；seed严格为600000—600179；trajectory/config/input/content五类哈希各180个唯一值；三策略共享同一份轨迹配置。
6. 正式策略运行仍为 `0/540`。

## 4. 训练来源与划分

### 4.1 A-N3旧教师20条

- 原始输入文件 `data/teacher/sources/a_n3_20_v2.jsonl`：20条，SHA `6f099d8845dfa997c271399db5b43c348fa330c7a2b7316d8a5aaa20d89caf8d`；
- 教师输出 `samples.jsonl`：20条，SHA `2df964e78a6bf6220b4c48c92b29f4838d01af13281f41f666a306e96c5b8957`；
- 每个sample与其原始输入的 `sample_id`、`source_group_id` 和Observation逐项一致；
- source group共20个，划分为train/validation/test=`12/4/4`；sample、scenario、source group及Observation内容哈希的三组交集均为空；
- `splits.json` 中字段 `source_jsonl_sha256` 按实现绑定的是教师输出 `samples.jsonl`，不是原始输入文件；原始输入由dataset manifest的 `source_sha256=6f099d88...` 单独绑定，两条链均一致；
- 旧教师记录没有完整场景seed，因此不能声称完成“旧教师seed逐项比较”。本轮使用公开Observation投影补充检查，20个旧投影与180个候选投影交集为0。

### 4.2 A-N4b先导数据

- 30个source_id全部唯一，seed为410000—410029；
- source级划分为train/validation/test=`18/6/6`，三组source_id交集为空；
- 来源文件及划分文件均包含在泄漏审查副本和SHA索引中；
- A-N4b继续封存，不训练、不替换旧冻结模型。

### 4.3 开发与退役输入

- 泄漏审查汇总390个排除seed、374个排除场景内容哈希；
- 180个候选与排除seed、排除内容哈希及旧教师Observation投影的交集均为0；
- 该结论覆盖退役formal_v1、18×10开发矩阵和A-N4b先导来源，但不把“旧教师缺少seed”伪写成已检查。

## 5. 备注与剩余门禁

A的 `accepted_with_notes` 只批准候选来源与划分进入最终三方签字步骤。以下条件仍未完成：

1. `review/leakage.json` 从 `pending` 形成A/C共同确认的最终 `accepted` 字节；
2. A/B/C三份正式post-generation回执绑定同一个最终leakage SHA；
3. `scripts.prepare_formal_v2_review --index` 与冻结工具接受三份回执；
4. B记录正式预跑和容量估算后，才可执行540个唯一运行键。

Hybrid、重训练、模型替换、删除tie、重跑挑结果或修改统计协议均不在批准范围。正式结果出来前，报告/PPT/前端的胜、等效、负、未完成数字继续留空。
