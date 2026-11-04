# WP5 开工准备证据

日期：2026-11-04。运行候选：`8ccbd1e`（B WP2 + C b1d5e8b），后续仅准备文档/证据；不是正式冻结版。

- 后端552通过、1平台跳过、1既有警告；前端70通过和生产构建通过。
- 实际uvicorn/Vite代理，两配对请求的input_hash一致，事件分页和ZIP哈希通过，4次模型成功决策；不是浏览器点击验收。
- 12个原冻结路径SHA一致；旧数据目录Git内容一致；C的73个源码/脚本/材料路径与交付一致，逐样本审计卡20条内容复核无差异。
- 再次核算：idle位于最优集合19/20；可行最优集合并列6/20。两个数不能混用。
- 附件与C仓库作战方案统一换行后的文本相同；附件SHA记录在verification.json。图片内容为人工阅读整理，见B交接单，不视为新测试证据。

本轮原始运行在 `runs/b_wp5_readiness_20261104/`，ZIP和完整运行目录按仓库规则不提交；关键日志、JUnit和HTTP记录保存在本目录。verification.json带原始文件SHA和运行身份；SHA256SUMS.json核对本目录提交文件（自身除外）。

## 复跑

先建新的输出父目录，以下现有输出不能覆盖复用：

```powershell
New-Item -ItemType Directory -Force runs/b_wp5_readiness_retest | Out-Null
.venv\Scripts\python.exe -m pytest tests -q --tb=short --noconftest -p no:cacheprovider --basetemp=runs/b_wp5_readiness_retest/tmp --junitxml=runs/b_wp5_readiness_retest/backend.xml
pnpm --dir frontend check
.venv\Scripts\python.exe docs/evidence/B/WP2_learned_2026-11-04/verify_http.py --output runs/b_wp5_readiness_retest/http
```

如复跑verify_readiness.py，需将上述命令输出分别保存为backend.log、frontend.log、http.log，并用 `--runs` 指向该目录，`--attachment` 指向用户提供的作战方案文件。它只读取文件/Git并写指定证据JSON，不生成新训练数据或正式实验输入。后续C远端更新时应固定本轮的 `b1d5e8b` 再对照，不能把未来远端变动归因于本候选。

已知缺口：A新包未收到；A对WP2独立复测未到；真实浏览器验收未做；formal_v1输入、统计脚本和540次正式运行未实施。材料claim时延/术语、C页面失败路径及门禁缺口已在交接单列明，本轮未修改C实现。
