# B-R3：可独立复跑的通信交付闭环

2026-10-29；发送B→A（协议/能量/指标复算）、C（事件/结果消费）。开发使用synthetic健康输入，不依赖A/C产物。状态ready_for_review，未代任何接收人签收。最终R3新增23项、R2 41项、全库242项通过；源实现提交0c18f6d，四例最终运行均据此生成；独立审查两项Important已修复。

## 交付范围

- 可选protocol配置启用R3；R2配置/历史发送验证继续有效。内部protocol.py与r3_engine.py实现单在途、1024byte最大块/32byte头/16byte ACK、接收、确认、超时回队和去重。
- evaluate(events, config)从同run/policy事件重算任务与字节指标。任务完整成功按网关首次全部接收时刻判断；星上队列只等ACK扣账。详细定义见docs/metrics.md。
- backend.cli提供固定入口`python -m backend.cli run --config <path> --output <dir>`，目前只支持manual单策略实际合成验证。配置含显式动作脚本，运行结束写六件套及能量账本，最后写completed；失败保留failed与日志。

## 复跑命令

在仓库根PowerShell运行；输出目录用新名称：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_protocol.py tests/test_evaluation.py tests/test_run_export.py tests/test_simulator.py -q --noconftest -p no:cacheprovider --basetemp=runs/r3_receiver_tmp
.\.venv\Scripts\python.exe -m backend.cli run --config configs/scenarios/r3_ack_loss.json --output runs/r3_receiver_ack_loss
```

不需加载旧权重、调用A健康估计或启动C页面。全库旧资产测试需要本地v3包；某些Windows沙箱不允许其临时目录联接测试，此时须在允许目录联接的终端复跑，不能据此删测试。

## 接收人应复核

1. 正常与多块：`r3_normal.json`去重接收1024byte；`r3_multiblock.json`分块1024/1024/452，去重2500byte；ACK前remaining不减，ACK后仅减一次。
2. 断窗`r3_ack_loss.json`：0秒sent，1.03125秒网关收齐，2.03125秒ACK因关窗丢失，3.03125秒超时，4秒重传block0，5.03125秒重复接收，6.03125秒ACK。deadline=4秒，业务按首次接收仍成功，有效字节只计1024。星上未确认队列过期的dropped事件不撤销网关成功，不能由dropped事件直接猜业务失败。
3. 能耗：断窗例背景36W*8s=288J，两次发射36W*1.03125s*2=74.25J，接收增量8W*(0.09375+0.125)s=1.75J，总364J；364/(1024*8)=0.04443359375J/bit。零交付`r3_no_delivery.json`为0有效字节、J/bit=null/NO_DELIVERY。2:1加权分母的独立测试在tests/test_evaluation.py。

## 来源、证据与限制

所有物理参数为明确的synthetic仿真假设，见configs/parameters.csv与R3时序细则；不是卫星实测。实际运行及核验记录在docs/evidence/B/R3_2026-10-29/，manifest含实际源文件与产物SHA。

status.json是运行包是否完成的唯一状态依据：仅status=completed且必需文件/哈希完整时可消费正式结果。可捕获异常/键盘中断会留下failed并将已写结果移为results.partial.json；强制结束进程或断电无法保证执行清理，可能留下running包，必须视为未完成。

单run单policy、零随机误包、完整块在一个step内发送。精确违例持续时间、关键任务集合及模型/决策耗时未测，结果中为null+reason；违例次数目前指负值账本分段数，不能当独立负值事件频率。未实现统一R4 guard/公平基线/优化教师/学习接入/五API；不宣称策略优越性或完整B-N2已验收。

R2 PR #3保持原有验收范围；本次为独立依赖R2的分支，待R2入main后再整理目标分支。A/C在各自回执中填写实际提交SHA、命令、文件哈希、结果和accepted/changes_requested，B不代填。
