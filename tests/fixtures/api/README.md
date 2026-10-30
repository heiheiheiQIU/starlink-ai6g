# B-N3 接口样例

request.json是可直接POST的完整合成配置；actions为空，仅比较edf/value。

running.json、completed.json、failed.json是手工UI状态样例，均标记contract_fixture / is_experimental_result=false；包装内的status/events分别符合RunStatusResponse/EventsPage。不可将样例状态当真实实验结果。完成样例的结果/事件来自标记清楚的合成运行副本；真实五接口验证另见docs/evidence/B/B_N3_2026-10-29/。

running或failed时results/export返回409。running的空页并不表示完成，UI继续查询同run；completed后仍需分页读取末批。
