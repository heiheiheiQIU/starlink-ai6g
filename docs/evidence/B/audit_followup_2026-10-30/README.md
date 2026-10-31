# B1 审计修复证据

被测基线 d68d3cb 加本次未提交的源码差异；文件哈希见 verification.json。

| 文件 | 实际结果 |
|---|---|
| red.xml | 2 failed，干净副本无法导入 backend，复现错误根目录 |
| red_mkdir.xml | 2 failed，修复根目录后缺父目录，复现递归创建问题 |
| green.xml | 2 passed，两个启动目录、每个重复执行两次 |
| full.xml | 首次修复后全库309 passed，1条既有弃用警告 |
| final.xml | 输出改为新目录后全库309 passed，1条既有弃用警告 |
| verification.json | 7份R0证据与70c5064 blob一致；旧seed脚本与d68d3cb一致；当前文件及XML哈希 |

修复前裸pytest曾因默认临时目录权限出现236 passed、71 setup errors；该首次失败未输出JUnit，本说明保留结果与归因。随后指定工作区basetemp的基线为307 passed。原始本地日志在 runs/b_next_20261030/，不以其存在代替队友复跑。

两次git fetch均因GitHub 443连接失败，866df43尚不可用；没有生成A数据验收结论。B教师的20状态预检仅为本地入口计时，不能代替A样本或规模化数据。

独立只读审查指出R0归档换行转换及接口稿对候选完整性检查的歧义；均已修正。R0重新按Git blob恢复并设置字节保留属性；接口稿明确该检查是learned接入待实现要求。最终验证以final.xml与verification.json为准。
