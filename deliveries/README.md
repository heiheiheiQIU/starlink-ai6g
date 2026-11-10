# B 原始离线演示包

本目录向 C 交付上轮已验收的原始 ZIP，保持逐字节一致，没有重新打包。

| 项目 | 固定值 |
|---|---|
| 原包 | [B_final_demo_20261110.zip](B_final_demo_20261110.zip) |
| 大小 | 17,532,109 字节 |
| SHA256 | `8b79351f35447fd8764451bfa0151447316dbd90f16b0be1d8f15bbd212664f4` |
| 载荷文件 / ZIP 成员 | 110 / 111（含根哈希清单） |
| 运行源码与前端来源 | `fc44e252394c350a0bbc65a626b4f1dbb18327c0` |
| 冻结模型权重 SHA256 | `a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a` |

请在 C 自己的电脑上先独立计算原包 SHA256，再解压运行。本机 B 的计算结果不能代替 C 的收包记录或第二台物理电脑验收。

```powershell
Get-FileHash -Algorithm SHA256 .\deliveries\B_final_demo_20261110.zip
```

比对本目录 .sha256 文件及上表，保持原始 ZIP。向一个不存在的新目录解压；电脑需预装 Windows x64 / Python 3.12：

```powershell
Expand-Archive -LiteralPath .\deliveries\B_final_demo_20261110.zip -DestinationPath .\B_demo_acceptance_C_01
Set-Location .\B_demo_acceptance_C_01
py -3.12 accept.py
```

accept.py 自动建立新环境，使用包内轮子离线安装依赖，检查页面/API，并执行 S1/S2/S3、健康对照、同种子复跑与 ZIP 证据校验。无需安装 Node 或 PyTorch。失败时保留日志，换新目录重试；不要在失败记录上改写 passed。安装前提不满足时，应记录环境缺项。

成功后启动页面：

```powershell
.\env\Scripts\python.exe start.py
```

打开 http://127.0.0.1:8000，按[第二台电脑验收交接单](../docs/handoffs/B_C_原包与第二机验收_2026-11-10.md)完成手工检查，保留全部 acceptance 目录及截图。端口占用时，自动验收加 `--port 8042`，页面启动加 `--port 8040`。

本包已通过 B 本机全新环境验收。C 收包、C 独立哈希和第二台物理电脑验收目前均待真实记录。工程闭环验收与 AI 正式结果发布分别判断；正式 AI 实测仍为负，不能将演示数据正差值作为收益证据。
