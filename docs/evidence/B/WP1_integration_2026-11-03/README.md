# WP1 统一集成验证（2026-11-03）

范围：集成R2→R5、已签收A候选、A原回执和C前端；完整运行候选87a4220，最终文档提交另看分支head。main没有在本轮直接更新。

## 已运行

| 检查 | 结果 | 记录 |
|---|---|---|
| 开始前B基线 | 312 passed | baseline.xml |
| 实际R2合并版本 | 219 passed | R2.xml |
| 实际R3合并版本 | 248 passed | R3.xml |
| 实际R4合并版本 | 293 passed | R4.xml |
| 实际R5合并版本 | 312 passed | R5.xml |
| A与原回执组合 | 519 passed | A.xml |
| 最终A/B/C组合 | 519 passed | final.xml |
| 冻结pnpm依赖安装 | exit 0，锁文件未改 | verification.json |
| 前端测试、类型和生产构建 | 61 passed；构建通过 | frontend-check.log |
| 真实HTTP、Vite代理、分页、ZIP和独立模型评分 | 全部通过 | verification.json中的http、两份http日志 |

XML保留当时完整字节，含内部本机路径，不作为匿名参赛附件。后端除R2/R3外有一条既有AnyIO弃用警告。安装时有包下载重试，最终退出0；不据此声称完全离线安装或换机成功。

verification.json包含每层命令、集成与来源SHA、测试数、关键源码身份、模型身份与HTTP摘要；rulings.md记录范围和路径取舍。source_checks中前端记录Windows CRLF差异，规范化源码一致；README文字修正明确排除。

## 复跑

先按根README恢复旧资产和依赖。仓库根PowerShell：

```powershell
$reviewRoot = Join-Path 'runs' ('wp1_repeat_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $reviewRoot | Out-Null
.\.venv\Scripts\python.exe -m pytest tests -q --tb=short --noconftest -p no:cacheprovider --basetemp "$reviewRoot/pytest" --junitxml "$reviewRoot/tests.xml"
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend check
.\.venv\Scripts\python.exe docs/evidence/B/WP1_integration_2026-11-03/verify_http.py --output "$reviewRoot/http"
```

HTTP脚本需要8000和4179端口空闲，使用已构建前端，创建一个新synthetic规则run，最终回收自己启动的服务。运行目录必须新建；原始run保存在本机runs/api，ZIP与验证记录写入指定输出。脚本不是浏览器操作，也不调用learned运行。

本轮仅提供规则运行和独立评分证据，不支持AI收益、成熟优化器比较、真实卫星表现、完整页面闭环或换机结论。当前A模型仅20条合成观测的管线验证，限制仍生效。
