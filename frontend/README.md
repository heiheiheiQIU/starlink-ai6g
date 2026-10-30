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

仓库内 `.npmrc` 关闭pnpm自动替换自身版本的行为；在无网络但已有本机pnpm缓存时可使用
`pnpm install --offline`，它仍然受冻结锁文件约束。

`pnpm check` 会顺序执行全部 Vitest 测试、TypeScript 检查和 Vite 生产构建。

## 本地演示

```powershell
pnpm dev
```

未配置后端时，整个平台保持显式 `FIXTURE / 非实验结果` 标识，可断网演示。

## 连接真实运行服务

```powershell
$env:VITE_RUN_API_BASE_URL = "http://127.0.0.1:8000"
pnpm dev
```

真实服务当前只用于按 `run_id` 检查状态、事件、结果和导出包。新建运行继续等待
B端冻结场景预设合同；前端不会自行拼装或推测通用仿真配置。

页面规则：只有后端返回 `completed` 后才读取并展示正式结果；`queued`、`running`、
`failed`、`cancelled`、离线和合同错误都不展示最终指标。
