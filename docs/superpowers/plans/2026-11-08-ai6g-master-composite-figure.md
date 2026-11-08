# AI+6G 四联证据主图实施计划

**Spec:** `docs/superpowers/specs/2026-11-08-evidence-dense-master-figure-design.md`

## Task 1：冻结图件数据合同

- 新建 `docs/figures/source_data/v4_master_figure.json`，只摘录已签核数值并记录远端 ref、路径和 blob。
- 测试校验教师评分、事件时间戳、能量末值和结果指标，防止后续手工漂移。

## Task 2：生成科研型四联图

- 新建 `scripts/generate_report_master_figure_v4.mjs`。
- 输出 `docs/figures/generated/v4/report/C-F00_AI6G闭环证据主图.svg` 与 300 dpi PNG 预览。
- 使用真实坐标轴、窗口区间、事件标注、能量曲线、阈值/边界、图例和证据限定语。

## Task 3：视觉核验与审计

- 自动检查尺寸、背景、面板标记、关键数字、禁止主张和来源信息。
- 渲染后人工检查遮挡、箭头、图例、对齐和缩放可读性。
- 生成 `docs/figures/generated/v4/report/README.md` 与 manifest。
- 样图不接入报告，待用户确认后再扩展整套图版。
