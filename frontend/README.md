# 星地智调前端运行说明

本目录统一使用 `pnpm`。`pnpm-lock.yaml` 是唯一依赖锁文件；不要生成或提交
`package-lock.json`、`yarn.lock` 等第二套锁文件。
支持Node.js 20—24与pnpm 9—11；正式证据记录实际使用的小版本。

## 首次安装与验证

```powershell
corepack enable
pnpm install --frozen-lockfile
pnpm check
```

在无网络但已有本机pnpm缓存时可使用
`pnpm install --offline --frozen-lockfile`，它仍然受冻结锁文件约束。

`pnpm check` 会顺序执行全部 Vitest 测试、TypeScript 检查和 Vite 生产构建。

## 本地演示

```powershell
pnpm dev
```

未配置后端时，整个平台保持显式 `FIXTURE / 非实验结果` 标识，可断网演示。

## 连接真实运行服务

```powershell
pnpm dev
```

开发和预览服务器默认将 `/runs` 代理到 `http://127.0.0.1:8000`；后端按仓库根目录
README启动，无需额外设置环境变量。如果使用 `VITE_API_BASE_URL` 直连其他地址，
目标服务必须配置相应CORS；当前后端默认未启用跨域，优先使用同源代理。

真实服务当前只用于按 `run_id` 检查状态、事件和结果；API客户端已具备导出能力，
页面ZIP下载联调尚待完成。新建运行继续等待
B端冻结场景预设合同；前端不会自行拼装或推测通用仿真配置。

页面规则：只有后端返回 `completed` 后才读取并展示正式结果；`queued`、`running`、
`failed`、`cancelled`、离线和合同错误都不展示最终指标。

## 接入formal_v2正式分析

策略评估页可读取由正式分析与三方结果签核流程生成的只读JSON：

```powershell
$env:VITE_FORMAL_SUMMARY_URL='/evidence/formal_v2/summary.json'
pnpm dev
```

未设置变量时页面明确显示“未完成”，不产生占位结果。配置后若文件无法读取、结构不符合
`formal-analysis-summary-v1`、18格/540次计数不一致或签核门禁冲突，页面失败封闭，不回退到
fixture。原始`experiments/analyze_formal.py`输出在三方结果签核前必然保持
`result_signoff=pending`、`formal_verdict=未完成`；禁止人工修改JSON冒充签核结果。

场景验证页的沙盒结果画像只读取当前`run_id`的后端`results`。调整工程参数或seed并重新运行后，
条形、指标与策略差值按真实结果更新；它只用于单次合成工况解释，不作为formal_v2总体增益结论。
