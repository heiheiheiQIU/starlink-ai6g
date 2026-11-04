# B 输入候选验证记录

本轮实施WP5 Task1。协议与清单在experiments/formal_v1，恢复命令见其README。完整运行产物在runs/formal_inputs_20261104，包含两份重复生成配置，每份180条。Git保存可恢复身份，ZIP和生成目录保存在本机运行目录。

先运行新增测试，缺backend.formal_inputs模块，见red.log。首版离散优先级导致内容重复，改为预登记uniform[1,3]后9项定向通过，见core.log。

独立gpt-6-astra high审查接受5项Important。review_red.log记录8失败/9通过，覆盖审核字段、训练域描述、实际协议字节、额外文件、Windows junction和源码缓存。修复后review_green2.log为17通过。随后对源码常量再做回归，constants_red.log为1失败/1通过，加入导入时源快照检查。最终全库结果见final.log/final.xml和verification.json。

人工复核的5项修复包括manifest精确字段/状态、协议描述和算法规则、协议文件实际字节SHA、180配置完整清单与目录归属、已加载代码与当前源文件一致性。根目录README/前端/模型/公共合同均沿用已有实现，本轮只新增输入模块与协议。

待处理Minor为冲突拒绝消息缺少具体轨迹/值。输入仍会被拒绝，调用方应保留已知来源冲突清单。

验证边界包括A-N4b跨来源审计pending、模型null、A/C接收复测待交付。formal_policy_runs为0。EDF/value各一条是输入身份兼容性测试。

全库命令使用现有venv，`python -m pytest tests -q --tb=short --noconftest -p no:cacheprovider --basetemp=runs/formal_inputs_20261104/final_tmp --junitxml=runs/formal_inputs_20261104/final.xml`。每次复跑应使用新的basetemp及输出目录。
