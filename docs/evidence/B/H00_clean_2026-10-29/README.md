# H00干净集成证据

日期：2026-10-29（UTC+08:00）。基线main@f048da9；选择来源B@c54c79d，A回执@db2b513，C回执@143b7d4。

本次从main新建分支，未merge成员整条分支。初始白名单43个文件的Git blob与各自来源逐字节一致。后续只添加冻结/范围说明、集成SHA清单和README/B-N1状态，不改变已签收合同、Schema、测试或回执。检查未包含frontend/、docs/design/、docs/ui_structure.md以及A内部健康估计核心。

原H00两组契约共117项，连同main原61项，全库178项通过。使用main原有configs/legacy_assets.json；本机将只读旧包恢复到其要求的仓库外相邻交付包目录，149文件SHA一致。没有将路径改动混入合同集成，没有上传数据、权重或环境。

复现命令：

```powershell
New-Item -ItemType Directory -Force runs/h00_clean_integration | Out-Null
.\.venv\Scripts\python.exe -m pytest -q --noconftest -p no:cacheprovider --basetemp=runs/h00_clean_integration/tmp-full --junitxml=runs/h00_clean_integration/full.xml
```

原始日志与XML在本机被忽略的runs/h00_clean_integration/。再次执行须使用新的临时目录名。selection.csv记录从c54c79d和A/C回执来源选择的文件及SHA；不将历史证据清单中已排除的工作区入口文档伪装为本分支交付。

本记录证明干净选择和本机回归，不等于前端/仿真实现或新实验结果。A/C accepted原件及冻结生效条件见docs/contracts/FREEZE_2026-10-29.md。

独立范围审查h00_clean_scope_review：43项来源blob/大小/SHA匹配，48项最终变更未含C设计或A核心；独立合同117项通过，Schema字节一致，Critical/Important/Minor均为0。此审查不替代A/C回执，原回执已分别签收同一c54c79d。
