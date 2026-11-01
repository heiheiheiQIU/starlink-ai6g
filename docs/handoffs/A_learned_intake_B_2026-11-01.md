# learned模型包接收门：B现场状态

状态：awaiting_delivery。11/01重新fetch、查询全部远端learned分支及本地对象库后，仍未取得codex/a-n3-learned@97124d4。仅收到用户提供的A_N3_learned_A_2026-11-01.md，不能独立验收权重或代码。

**后续接收更新：** 上述为上一轮现场。现已取得PR #8固定候选11c00374及模型五文件，五SHA、manifest、配置与权重格式预检通过，状态改为received_pending_functional_review。原待交付阻塞解除；后续按 `B_learned_next_2026-11-01.md` 执行正式验包，不重复索取已到件材料。

## A需给出的可读交付

1. 最终完整40位SHA及源码：可推送评审分支，或先提供只读git bundle/源码归档。区分最终97124d4、训练源码ff0589b、模型包7f18ff2和回归e15048d的角色。
2. 模型目录实际五文件：weights.npz、normalization.json、training_summary.json、model_card.md、manifest.json；npz被忽略时须另交产物，不能只给Git目录路径。
3. configs/learned_policy.json、configs/policy_train.json、训练verification.json、测试名单/命令、失败用例名和完整traceback。
4. R2四项手算及R5公平性两份独立回执；与模型包交付分开处理。

## 到件后B立即执行

- 按附件五个SHA验证文件与manifest引用；用allow_pickle=False核对float32、权重名、形状和有限性。
- 运行dataset/training/learned/runner定向，检查完整20观测候选、idle、结构mask=-1.0、输入未变、错误与100ms网关超时回退。
- 独立核对12/4/4来源划分、train归一化、validation选seed、test在选择后一次评估；不重训或重选模型来追求更好test数字。
- 独立记录加载/推理延迟，出“learned小样本冻结包与接口行为”回执。报告中的79/498通过、模型五SHA、MSE和延迟目前仍为A提供的记录，不写作B复验结果。

API对齐补丁已在A公开基线及B当前版本独立验证，见B_API_lock_2026-11-01.md。依赖候选的模型验收、learned集成与正式AI实验尚未执行；没有生成accepted回执或改写A冻结模型。
