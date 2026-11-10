星地智调 · B 最终离线演示候选包
环境：Windows x64，Python 3.12。依赖轮子已包含，运行不需要 Node、Git 或联网。
请先解压到一个全新目录，在该目录执行：
  py -3.12 accept.py
验收将校验文件、创建 env、离线安装、检查页面与 API，执行 S1/S2/S3、健康对照和复跑并导出 ZIP。
所有日志位于 acceptance 下；失败不覆盖，请保留整份目录并在另一全新目录重试。
验收完成后启动：
  .\env\Scripts\python.exe start.py
打开 http://127.0.0.1:8000，选择真实沙盒及 S1/S2/S3 并运行。
若默认端口已用，启动加 --port 8040；验收加 --port 8042。
真实演示中 EDF 为 S1/S3 全交付，Learned 为零交付；S2 两者均为零，保持原样展示。
演示为 synthetic/sandbox，不能替代正式540次结果或当作AI增益。
SOURCE_PROVENANCE.json 是本包来源。历史包不包含在当前运行源码内。
第二台物理机器需实际执行 accept.py；同机重复运行不能算作异机验收。
