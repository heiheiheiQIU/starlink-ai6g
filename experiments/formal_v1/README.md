# formal_v1 输入候选

状态为 `candidate_pending_review`。本目录保存协议和180条输入身份清单，生成配置在独立输出目录。A-N4b来源、内容排重与接收人复核待交付后执行，模型字段为null。

## 参数依据

每次决策间隔2s，评价终点24s，最多12个发送决策。每次发送至多1024B，故乐观载荷上限为12288B。2/6/10个任务各2048B，总负载4096/12288/20480B，对应乐观上限的1/3、1、5/3。任务全部在0s到达，期限从8/12/18/24s预先采样。窗口连续到26s，保证评价末端附近的ACK处理；指标在24s截断。

这个上限忽略ACK等待、期限、损失和重传，实际可用容量可能更小。near_capacity表达相对乐观上限的提供负载。所有策略使用同一轨迹，任务随机数使用独立的SHA256派生种子，优先级均匀采样于[1,3]。

三档初始能量为0.8/1.2/10Wh。24s背景耗电0.24Wh，0.8Wh初态在扣除reserve后仅有0.3Wh预算。10Wh初始准确健康作为资源充足反例。健康字段使用初始合成准确值，后续能量下界按现有Runner传播。

温和/强链路分别使用robust数据损失0.05/0.2、fast损失0.12/0.4、ACK损失0.02/0.12；共享随机信道按0.25s时间索引。全部工况含非零预测损失，应单列为当前确定性教师训练域外合成压力测试。支持域内模型行为与这里的全矩阵结果须分别解释。

## 生成与验证

在仓库根目录执行，output必须尚不存在。

```powershell
.venv\Scripts\python.exe -m backend.formal_inputs --output runs/formal_v1_inputs
.venv\Scripts\python.exe -m backend.formal_inputs --verify runs/formal_v1_inputs/manifest.json
```

应输出180条、candidate_pending_review。生成的manifest应与本目录input_manifest.json逐字节一致。源文件身份按UTF-8去BOM和换行规范化记录，配置SHA对应实际UTF-8/LF文件字节，input_hash与现有Runner对ScenarioConfig的哈希一致。

新种子200000–200179与旧开发10000–10179分离。清单同时记录保留身份的input_hash和移除scenario_id/channel.seed的content_hash，检测仅改名或换种子的重复输入。API支持显式excluded_seeds和excluded_content_hashes拒绝已知训练来源冲突，调用方必须提供同一种Scenario内容编码的哈希。A的Observation哈希与Scenario哈希语义不同，须结合来源轨迹核对，不能直接视为已完成交叉排重。

验证会重建清单对应配置，核对协议、生成器依赖、内容哈希与实际文件字节。`verify_inputs(..., require_frozen=True)`会拒绝当前pending包。最终运行入口、模型验收和统计分析按WP5后续任务继续实施。
