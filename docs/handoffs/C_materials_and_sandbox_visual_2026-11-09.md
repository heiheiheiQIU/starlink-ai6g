# C线：正式结果材料生成与沙盒结果可视化交接

日期：2026-11-09
状态：代码完成，等待真实签核结果和换机验收

## 1. 本轮解决的问题

1. 正式结果到达后，不再由成员手工抄写数字和重画图；
2. 未签核结果不能提前进入报告或PPT；
3. 沙盒参数改变后，后端返回的真实指标除了表格，还会形成随结果变化的视觉画像；
4. Learned为零、落后或指标缺失时，页面仍原样展示，不用零替代缺失。

## 2. 正式结果图件生成器

入口：`scripts/generate_formal_results_materials.mjs`

正式使用命令：

```powershell
node scripts/generate_formal_results_materials.mjs `
  --input <三方签核发布目录>/summary.json `
  --output docs/figures/generated/formal_v2_<日期>
```

输出目录必须不存在，防止覆盖已有证据。生成器仅接受：

- `schema_version=formal-analysis-summary-v1`；
- `result_signoff=accepted`；
- 完成、失败、缺失合计540次策略运行；
- Learned–EDF和Learned–Value各18个工况格；
- 正式结论与冻结统计结论一致；
- 冻结清单和运行索引SHA-256有效。

输出：

- `B-F07_正式策略比较总览.svg`：完整度、森林图、推理证据、来源哈希；
- `B-F08_十八工况配对差值矩阵.svg`：两项比较的18格配对差值；
- `CAPTIONS.md`：可直接进入报告/PPT制作环节的图注母稿；
- `manifest.json`：输入与图件SHA-256。

生成器不会修改报告、PPT或实验JSON。PNG/PDF由最终材料流程从SVG母版统一导出。

## 3. 沙盒动态结果画像

入口：`frontend/src/components/SandboxResultVisual.tsx`

数据只来自当前`run_id`的后端`results`，展示：

- 加权按时交付率；
- 关键任务成功率；
- 成功载荷；
- 能量违规与待处理任务；
- Learned相对同次运行基线的百分点差。

改变八项工程参数或seed并重新运行后，条形长度、数字、差值方向和正负颜色随真实结果更新。
该画像只解释单次合成工况，不升级为正式总体增益结论。

## 4. 三人后续接口

- B：完成正式运行与结果签核发布脚本，交付签核后的`summary.json`；
- A：复核模型/统计事实和18格解释，不修改原始运行事实；
- C：运行本生成器，核对manifest后，将SVG接入报告/PPT并进行换机视觉验收。

## 5. 当前禁止事项

- 禁止将pending分析JSON改成accepted；
- 禁止手填胜负、提升率或置信区间；
- 禁止把沙盒单次差值写成正式增益；
- 禁止用“等效”替代“未检出稳定差异”。
