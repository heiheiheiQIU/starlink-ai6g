# B 不依赖 A/C 的独立检查交接

日期：2026-11-07。状态：`ready_for_review`。验证源码为 `03cbb225d46472d9bbbfdc463a6bad291fc2c04e`；本轮只新增验证脚本、证据和文档，不改后端/前端生产实现。

## 实际完成

| 工作 | 实际结果 | 边界 |
|---|---|---|
| 真实 HTTP 与 Vite 代理 | 两组配对 EDF/Value、EDF/Learned 均完成，共 4 个策略运行；3 条/页分别读取 36/30 个事件 | 开发场景 r3_normal，不使用 formal_v1 输入 |
| 按 run_id 重连 | 新 HTTP 客户端只读取原任务状态，完成状态正常 | 验证服务端恢复读取；未声称浏览器刷新按钮或 localStorage 已验收 |
| 分页完整性 | 分页事件与导出 ZIP 的全量事件逐项一致，顺序与 ID 无重复 | 非仅检查条数 |
| ZIP 导出 | 每 ZIP 19 个文件，父清单 17 个哈希及子清单哈希一致，子策略输入哈希相同 | ZIP 保留本地运行目录；持久证据保存逐次验证记录 |
| 错误路径 | 未知 run 返回 404；非法游标和三策略请求返回 422 | 不改变现有两策略公共合同 |
| 干净环境 | Git archive 源码新目录、全新 venv、本地 wheelhouse 安装 16 个运行依赖，pip check 无冲突 | 同机 Windows x64 / Python 3.12；不是另一台物理机器 |
| 无 Git 运行 | 源码目录无 .git，服务 PATH 中无 Git；两组真实 HTTP、分页和 ZIP 均成功 | 版本返回 unversioned-source-sha256，保留源码哈希 |
| 模型缺失/损坏 | 仅在独立源码副本中注入，learned 提交均返回 422 / MODEL_UNAVAILABLE；原模型恢复 | 这是启动前拒绝；不混称为运行时 EDF 回退，后者见既有坏包案例 |
| 案例素材 | 三例 JSON、事件 CSV、少于 80 字说明、事件范围、run/policy/input 与源文件 SHA 已齐 | 开发手动脚本/故障注入/高分探针，各自注明来源 |

验证命令：

```powershell
.\.venv\Scripts\python.exe runs/b_independent_20261107/verify_http.py --workspace . --python .venv/Scripts/python.exe --output runs/b_independent_20261107/http_proxy --proxy
.\runs\b_independent_20261107\clean_env\Scripts\python.exe -m pip install --no-index --find-links runs/b_independent_20261107/wheelhouse -r runs/b_independent_20261107/api_runtime.lock.txt
.\.venv\Scripts\python.exe runs/b_independent_20261107/verify_http.py --workspace runs/b_independent_20261107/clean_source --python runs/b_independent_20261107/clean_env/Scripts/python.exe --output runs/b_independent_20261107/clean_http --port 8001 --without-git
```

源码副本由 `git archive 03cbb22` 解压；没有复制原 .venv。wheelhouse 下载阶段联网，安装阶段使用 `--no-index`。运行验证只请求本机 loopback；未在操作系统层切断整机网络，因此不把它描述为硬件断网测试。

## 可交付文件

- 持久证据：`docs/evidence/B/independent_2026-11-07/summary.json`、HTTP/干净目录日志与验证 JSON、运行时依赖锁、wheelhouse SHA。
- 可复跑探针：同目录 `verify_http.py`；指定 output 必须为新目录，脚本仅关闭自己创建的进程。`--without-git` 会在指定独立源码副本短暂移除/损坏模型后恢复，勿对正在使用的工作区运行该故障检查。
- 案例素材：同目录 `case_packet/`，public_snapshots 去掉后验仿真真值；原始事件 ID、时刻和原因码未改。事件 energy_Wh 代表事件耗能，电池状态单独读快照。
- 后端离线准备包：`runs/b_independent_20261107/B_backend_offline_20261107.zip`，23,021,493 bytes；SHA256 `975aba2955cb96f362beb75f0e68e5341cd10462fa2de5019759a6827252ce4a`。

离线准备包包含源码 ZIP、16 个 wheel、运行依赖锁、验证脚本和安装说明；适用于当前平台后端 API/NumPy 推理路径。不含 PyTorch 训练、旧资产健康适配器所需大文件、前端 node_modules 或最终作品材料，不称为完整赛事发布包。Git 不提交 wheel/ZIP；接收人可按 SHA 从本机包验收，或按锁文件另备其平台 wheelhouse。

## 接收复验

先核 `SHA256SUMS.json` 和离线包 SHA，再按包内 README 解压、创建新 venv、无索引安装与 pip check，在新的 output 目录重跑探针。正式输入/模型冻结与结果仍由原三方流程处理；本次没有新训练、正式比较或 claim 状态修改。

剩余独立工作：在另一台实际机器上复验上述准备包；本机可进一步做真实浏览器点击/刷新/下载验收。本回执不替代这两项。正式实验仍受来源审查、holdout 暴露裁决和签核依赖约束。
