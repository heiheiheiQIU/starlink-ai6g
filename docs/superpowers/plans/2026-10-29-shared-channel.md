# B R5 共享随机信道与规则对照

沿用executing-plans及失败先行测试；依据06§6.4/7、09§11，保留H00和已有确定性场景。先交独立可核验的随机环境及规则运行，不把枚举教师称作成熟优化器。

1. backend/simulator/channel.py：ChannelConfig(seed,step_s,ack_loss_prob,version)与纯函数uniform_at(config,time_s,stream)。SHA256按时间格索引，无可变RNG状态；数据和ACK两个独立stream；同一时刻不同策略/模式读同一外部数值。时间格内相关，不声称每包独立。
2. ScenarioConfig增加可选channel；没有channel仍拒绝实际非零误包。R3执行按发包起点读取data损失概率及外部数值，数据丢失无接收/ACK、等待超时；ACK在其到达时刻读取ack数值，丢失仍记录接收耗能与重传。策略Observation不暴露真实信道或seed。
3. CLI/manifest记录真实环境seed，API channel.seed必须等于请求seed，保留旧零损失行为。预测概率属于公开输入，但规则仅按既有策略评分；教师遇非零预测损失仍明确unsupported。
4. backend/experiments.py：按已登记18×10 seed名单生成有明确synthetic参数的配置，EDF/value共享不可变输入与种子；逐运行真实输出、per_run.csv、summary.json/manifest，不跑AI/优化器、不伪造缺失方法。
5. tests/test_channel.py及tests/test_experiments.py：公平性、数据全丢、ACK全丢、去重和耗能、旧配置兼容、观察隔离、seed/trace哈希、180清单与54子集、同seed科学复现。独立整体审查和全库验证后保存源码提交，再实际跑独立小样例及矩阵。

合成参数决策：24秒评价时域；负载2/6/10任务，各任务1或2块；低/中/充足初始储能0.8/1.2/10Wh，容量20Wh、reserve0.5Wh；mild/strong误包robust=0.05/0.2、fast=0.12/0.4，ACK损失0.02/0.12；非实测、非调优、未三方冻结。所有轨迹含同一固定窗口、固定任务到达时刻、载荷/期限的seed扰动，保留充足储能且准确健康估计的反例。

验收重点：丢失数据不能产生ACK；丢失ACK后不得重复计成功字节；不同发包次数不推进外部序列；背景/收发能量不漏计；失败运行保留状态；已有签收代码和证据不改写。
