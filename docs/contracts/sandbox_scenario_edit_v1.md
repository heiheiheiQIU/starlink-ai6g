# Sandbox 参数合同 v1

浏览器向 POST /runs 提交 configs/sandbox/S1.json 格式，顶层 seed 为非负整数，policy_ids 一次选一或两个 edf/value/learned。config 仅含 kind=sandbox_axes、compiler_version=sandbox-axis-v1、axes。非法参数返回 422、code=INVALID_CONFIG、details.errors，其中 loc 定位错误字段。运行中编辑参数应新建运行。

| axes 字段 | 合法值 |
|---|---|
| task_count | 2、6、10 |
| deadline_s | 8、12、18、24 |
| weights | equal、tiered、urgent |
| initial_energy_Wh | 0.8、1.2、10 |
| health | healthy、degraded、critical |
| reserve_Wh | 0 至 20，单位 Wh |
| disturbance | none、mild、strong |
| rate | robust、fast |

策略与 seed 在顶层，与上述八个场景轴共同构成方案的十类参数。机器 schema 见同目录 JSON。额外字段拒绝。

B 固定的构造规则如下。容量 20 Wh，时域 32 秒，窗口 [0,32)，任务到达为 index % 3 秒，期限为到达加期限档。首任务 3072 字节，其余 1024 字节，轮转权重向量分别为 (1,1,1)、(1,3,6)、(6,1,1)。健康档的容量下界比例分别为 1、0.85、0.7，能量下界为初始能量乘 0.98、0.8、0.65；soc_lower=能量下界/容量下界，soc_est=初始能量/20。RUL 保持 null。储备线超过初始能量时允许运行，发送由 Guard 裁决。

robust 档的 robust/fast 速率为 16384/32768 bps，fast 档为 32768/65536 bps。策略仍能比较两种发送模式。扰动档的数据丢失与 ACK 丢失概率分别为 (0,0)、(0.05,0.15)、(0.1,0.65)，使用现有时间索引随机信道和顶层 seed。基础功率 36 W，robust/fast 发送功率为 36/72 W，ACK 接收 8 W。上述数值为 B 选定的合成演示配置。

服务端唯一入口 compile_sandbox_axes 返回完整 RunConfig，actions=[] 表示自动策略运行。已存在的完整配置请求继续可用。sandbox run_id 前缀为 sandbox_run_，数据位于 runs/api/sandbox；正式生成和运行使用独立冻结提交及正式入口。C 的 formal 模式读取签核发布清单。

ZIP 中 config.json 保存原始请求，compiled_config.json 保存完整运行配置，sandbox.json 保存 axes、构造器版本、构造器源码 SHA 和完整配置哈希。根清单逐一校验这些文件和策略文件。结果 config_hash 标识原始请求，sandbox.json.config_hash 标识编译结果，input_hash 标识实际完整 scenario。策略子清单记录运行源码哈希及模型身份。

GET /runs/{id}/events?after=0&limit=500 返回 next_after/has_more。当前实现每个策略完成后原子发布一个真实事件批次，两策略运行可在第二策略执行时读取第一策略事件；同一策略内部事件在该策略完成时发布。客户端应独立轮询状态与事件，按 has_more 排空，completed 后最后排空一次。按 sim_time_s 回放时先按 policy_id 分流；父流按策略拼接，跨策略的仿真时间会重新从零开始。回放速度只控制显示。

在相同完整配置、seed、模型、源码和依赖锁下，对动作、评分、约束、协议事件与物理指标进行复现核对。run_id、实测推理时延和机器耗时分别记录。固定模型可能选择 idle，界面应显示真实评分与动作。

后端启动命令为 .venv/Scripts/python.exe -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --workers 1。前端沿用 Vite /runs 代理，开发启动与构建见 frontend/README.md。真实 HTTP 复验命令为 python -m scripts.verify_sandbox --output 一个新目录。
