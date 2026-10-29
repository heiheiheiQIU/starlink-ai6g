# R3确定性协议与评价细则

依据09§7/15—17、06§6.4及B任务书B1。用户已授权不依赖A/C推进B工作；本细则仅明确B内部实现，不改H00公共类型。

R3由场景中的可选protocol配置显式启用；缺失时保留R2发送验证行为和历史命令。真实健康模型、随机误包、多策略、guard/教师/API均留后续。所有新增参数为synthetic。

## 时序

数据按既有真实速率积分，完整块在当前step及窗口end前发送完成。receive_at=send_end+data_propagation_s；已发数据遇关窗仍传播。ACK目标到达receive_at+slot_s；控制发射区间为[目标到达-ack_airtime-ack_propagation_s,目标到达-ack_propagation_s]，ack_airtime=16*8/control_bps。控制发送及ACK到达必须处于同一个窗口，ACK到达等于end按丢失。配置须满足ack_airtime+ack_propagation_s<=slot_s。

timeout_at=send_end+2*slot_s，保留R2起点。ACK、接收、到达先于同刻超时与过期处理。超时只清在途并保留同一块重试身份；不会自动发送。已过期任务不再发送，仍处理传播中的数据和ACK。每块ID=已确认载荷偏移//1024；星上remaining只在有效ACK时扣一次；网关按(task_id,block_id)去重。旧ACK可确认同一未确认块，不能清除不同块。

内部待办与网关真值只在环境。step深复制输入，先处理当前待办再检查动作，推进到下一个内部事件/窗口/能量边界。公共事件仅使用H00枚举，重复接收reason_code=DUPLICATE_BLOCK；超时fallback=ACK_TIMEOUT；ACK丢失dropped=ACK_LOST_WINDOW_CLOSED。事件按时刻稳定排序后分配单run、单policy递增ID。

## 能量与资源

数据发射W按实际airtime计；背景/计算持续计；卫星ACK活动接收用增量ack_rx_W（背景已含待机）。控制16byte占独立预留时间，不从数据wire rate再扣一次。重试数据发送不得覆盖已知控制保留区间。发射与接收各记录一次；sent计发射能耗，snapshot计背景/计算/接收增量，账本另列receive_Wh。失败ACK最多按窗口关闭前的实际活动接收时间计。max_power_W同时检查背景/计算与活动功率。储备仅依据Observation下界，真实负值始终保留，不能视为完整R4安全guard。

## 评价与导出

evaluate(events,config)仅用单policy事件及公开配置；拒绝混run/policy、非递增ID、不合法接收块和终点外日志。已到达且deadline<=终点的全部任务（含失败）进入加权分母；已到达但未到期单列pending。去重有效载荷（包括未完成任务的部分块）计goodput和J/bit分母；完整任务按首次全部接收时刻<=deadline判成功。迟到数据仍计有效字节但不计任务按时收益。无交付J/bit=null/NO_DELIVERY，无到期任务交付率null/NO_ELIGIBLE_TASKS。

最低SOC与违例次数依据事后snapshot；精确违例持续时间、未设置关键任务集合、未测模型/算法诊断保留null+reason。此处违例次数是负值账本分段数，非连续负值事件次数，在指标字典明示。

CLI单policy=manual，配置包含scenario/evaluation_end_s及按时间排序的显式Action脚本。执行到时域终点后落盘六件套与能量账本，最后写completed；异常保留failed和日志，不能返回正式成功结果。固定输入事件与指标可复现，run_id单独标识。manifest记录代码和源文件SHA、配置/外部轨迹SHA；模型hash=null，清楚标记synthetic和manual_validation。
