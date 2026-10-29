# H00候选合同验证证据

日期：2026-10-28（Asia/Hong_Kong）。角色B。基线提交70c5064，交付源码/Schema/Fixture的SHA见delivery-files.csv。状态ready_for_review，**没有A/C验收回执**。

## 交付与验证结论

- 公共类型、严格校验、候选集合检查、内部/事件延迟转换及JSON Schema已实现；六场景和HTTP/结果fixture可被Python及独立jsonschema校验器读取。
- 新增契约测试 **75通过**。
- 主仓库全库 **111通过、5失败、20错误**，失败/错误的用例集合与R0的25项完全一致，均来自旧默认资产路径。没有隐藏或删除旧测试。
- 在当前源码隔离快照中，仅将configs/legacy_assets.json指向已核验本机资产，全库 **136通过**。源码、测试、Schema及样例逐文件哈希比对，只有这一个配置文件不同。
- pip check通过；Schema重新导出的SHA与提交文件一致。旧研发包148文件仍完整，A代码/测试/历史证据及团队默认资产配置未改。

这些结果不证明仿真、guard、优化教师、HTTP服务或页面已实现；更不是新通信实验收益。fixture中的expected_behavior仍为待后续实现的验收条件。

## 实际验证命令与日志

工作目录为产品仓库根，解释器为本仓库.venv。H00不加载旧资产：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_contracts.py -q --noconftest -p no:cacheprovider --basetemp=runs/h00/tmp-contracts-delivery --junitxml=runs/h00/contracts-delivery.xml
.\.venv\Scripts\python.exe -m backend.contracts --schema-output runs/h00/schema-regenerated.json
.\.venv\Scripts\python.exe -m pip check
```

全库默认配置命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q --noconftest -p no:cacheprovider --basetemp=runs/h00/tmp-default-delivery --junitxml=runs/h00/full-default-delivery.xml
```

隔离验证工作目录为 `runs/h00/delivery_checkout`，使用原仓库venv解释器运行同一tests目录，最终指定原仓库内 `runs/h00/tmp-full-hashcheck` 和 `runs/h00/full-delivery.xml`。快照复制当前Git跟踪及未忽略新增文件，再只替换快照资产配置；不存在mock替换模型函数或删测。比对清单为 `runs/h00/snapshot-delivery-comparison.csv`，覆盖源码、测试、配置及交付说明；排除本次验证后生成的H00证据目录，避免报告和哈希清单自引用。

复跑请使用新输出目录/临时目录后缀，避免pytest清理已有有价值目录。快照并非新的开发仓库；后续开发仍在主工作区feature/simulator。

## 先失败后修复的记录

1. 先写契约测试，模块尚不存在时ImportError，见runs/h00/red.log；随后实现类型、schema及fixture。
2. Schema生成初次因过早插入跨定义$ref失败；改为Pydantic完成命名后附加Event条件。已有Schema测试覆盖生成稳定性和独立校验。
3. 独立审查发现Pydantic已有实例/子类可绕过嵌套字段验证。两个回归先失败：已有Observation中的非法健康下界、携带received_at_gateway的Task子类。
4. 公共模型启用revalidate_instances=always后，两项回归通过。
5. 交付SHA检查发现Windows CRLF与Git LF导致字节差异，先用CLI回归复现，再将导出明确固定LF并规范化生成的fixture。最终全部75契约及136隔离全库测试通过。

独立审查只发现上述一个重要问题，已修复并测试；审查者不是A/C，不构成队友签收。详细结论见[review.md](review.md)。

## 证据清单

- verification.json：三组测试计数与范围，保留主仓库默认失败状态。
- delivery-files.csv：交付代码、合同、schema、样例、依赖声明的文件SHA；不把这些哈希当实验模型哈希。
- input-sources.csv：06、09、00原资料文件SHA。
- local-log-index.csv：本机测试日志、JUnit XML、快照比对和安装记录的路径/大小/SHA。
- requirements.freeze.txt：完成H00后的实际Windows环境快照；不覆盖R0历史快照。
- installed-wheels.json：本阶段新增依赖的来源及wheel SHA。

原始日志在被Git忽略的runs/h00，索引不等于日志已发送给队友。需要复核时按索引提供文件或独立重跑；这些内部资料含本机路径，不直接进入匿名赛事材料。

环境为Python 3.12.14、NumPy 2.1.3、PyTorch 2.5.1+cpu、pytest 8.3.5；H00增加Pydantic 2.12.3和jsonschema 4.25.1。未验证GPU、构建分发、第三机安装或HTTP运行。

## 接收与下一步

A/C按docs/handoffs/H00_contract.md执行检查，对首次细化字段提出意见并各自留回执。没有回执不标accepted、不称三方冻结。下一阶段R2实现具体环境；旧资产通用路径适配按R0复核单单独处理，不混入本次公共接口变更。
