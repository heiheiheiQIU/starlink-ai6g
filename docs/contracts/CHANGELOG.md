# 公共合同候选变更记录

## 2026-10-28 H00候选实现（schema_version仍为1.0，等待A/C签收）

依据：09详细手册第15—17节补充优先，00提供基础类型及签名。当前尚无已验收H00，以下记录首次实现对草案的具体处理，不能作为A/C已经接受的证明。

| 原草案或留白 | 当前候选实现 | 原因及影响 |
|---|---|---|
| decision.data直接使用内部Decision字段 | 内部decision_latency_ms通过to_event_data显式映射为线上latency_ms；拒绝线上旧别名 | 遵循09；C必须读latency_ms，B解码返回仍用原内部字段 |
| 00 Decision.model_scores | 按09及仓库草案使用candidate_scores | 保留候选task_id/mode/score；不同时接受两套名称 |
| RunResult含五种status | 正式RunResult只允许completed；RunStatusResponse保留五种状态 | 落实未完成/失败不返回正式成功指标；partial保存留R5实现 |
| run级model_hash含义不明确 | 共同hash或混合时null；by_policy每项另有model_hash | 支持规则null与多模型对照；需A/C确认 |
| block_id未定类型 | 非负整数，同任务块索引 | 便于(task_id,block_id)去重；R3前共同确认 |
| forecast_energy_band/checks结构未定 | EnergyBandPoint及ConstraintCheck具名结构 | 为C提供可读Schema；无区间时null+reason_codes |
| Snapshot真值字段位置不明确 | snapshot.data.evaluation_truth，label固定posthoc_simulation | 明确事后展示；Observation无此字段 |
| 多指标只有名称描述 | PolicyResult固定字段与单位，缺测null+metric_reasons | 字段详见README；科学统计细则仍由R3/R7冻结 |
| 环境内部完整结构尚无实现 | SimulatorState Protocol + StepResult dataclass | 只定义接口边界，不提前编造环境或暴露真值 |
| config业务参数尚未冻结 | RunRequest.config当前为有限JSON对象 | H00只冻结HTTP封装；R2补场景参数，不能声称完整配置语义验证 |
| 未提供机器可读schema | 严格Pydantic类型生成configs/schema.json | C可导入命名$defs；跨字段/时间等语义仍由Python验证 |

配套：新增Pydantic 2.12.3运行依赖、jsonschema 4.25.1测试依赖；没有改A的backend/health、training、测试，也没有改C目录。新增Fixture仅供契约开发，不是新实验。

独立代码审查发现已有Python模型实例/子类可能绕过嵌套字段校验。已启用revalidate_instances=always，新增失败后修复通过的回归用例；这不替代A/C验收。

交付哈希检查发现Windows默认Schema输出CRLF会被Git规范化为LF。导出器现固定LF，新增CLI回归；fixtures和哈希清单统一LF，requirements.lock.txt增加明确LF属性。仅换行规范化，不改变业务字段或旧资产。

后续变更需记旧字段、新字段、原因、兼容性、影响文件及A/C复测结果。当前不创建虚假的accepted回执。
