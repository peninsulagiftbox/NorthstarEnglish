# 10B-1 独立代理技术复核及签收

日期：2026-10-28（Asia/Shanghai）。审查者：`/root/phase10b1_review`，独立审查代理。用户授权主代理自行审核、获取签收并在签收后开始10B-2。本记录是独立代理的技术审查，**不是用户、人工专家或第三方机构签字**。

## 结论与生效范围

**PASS_WITH_CONTROLLER_NOTE：B01/B03证据签收，通过10B-2隔离代码开发及测试的前置门禁。** 主控汇总程序真实退出1继续保留，不修改为0；该工具故障不否定已独立重算通过的数据安全演练。机器签收见 [INDEPENDENT_10B1_SIGNOFF.json](INDEPENDENT_10B1_SIGNOFF.json)。

签收只针对冻结V009.01–V009.04及历史隔离演练，不授权个人库迁移、替换运行中服务、正式发布、教材导入或10B-3。10B-2若新增/调整排序DDL或改变最新schema初始化顺序，必须重新完成其升级、空库初始化及故障恢复验证，不能沿用本签收。

## 审查方法与实际结果

没有启动数据库/服务，没有执行SQL、Docker或进程控制，也没有读取浏览器缓冲。审查独立实现离线PK/旧列比较、关系/历史CRC校验、恢复差异白名单和媒体清单校验；没有直接运行会独占写旧证据目录的原 `audit_completed_rehearsal.py`。

实际执行：

```text
PYTHONDONTWRITEBYTECODE=1 python3 docs/handoff/evidence/phase10b2/independent_review_10b1.py > docs/handoff/evidence/phase10b2/independent-10b1-review-run.log 2>&1
```

**实际退出0**。原始输出见 [independent-10b1-review-run.log](independent-10b1-review-run.log)，审计源码见 [independent_review_10b1.py](independent_review_10b1.py)。另行执行 `git diff --check` 实际退出0。原10B-1报告、STATUS、final-audit、失败result、日志、私有备份/媒体均未改写。

| 六类门禁 | 本次重新核验 | 结果 |
| --- | --- | --- |
| 源身份与Flyway历史基线 | 原证据中的固定source UUID/container与12隔离目标不同；源历史快照37表、V001–V008，旧迁移8份与HEAD逐字节一致；隔离目标完整身份/独立UUID及已停止记录 | PASS，历史证据复核，非当前在线数据库审计 |
| 一致备份与媒体 | 私有备份COMPLETE、32文件大小/SHA-256、依赖排序restore.sql无关闭FK/危险清理；全部12角色内容文件、11角色原私人录音逐文件hash重算 | PASS |
| V008升级路径 | 原备份→隔离恢复→旧应用读取前后逐值不变；四候选逐步后所有旧列值/旧约束不变；白名单仅paragraph及sentence.paragraph_id | PASS |
| V001空库路径 | 无BASELINE的12条实际SQL history、逐条Flyway CRC；V008显式旧Demo播种后四步升级，schema与升级路径一致；两路径两次启动快照不变 | PASS，仅覆盖历史播种顺序 |
| 故障与新目标恢复 | 三个DDL边界、真实history INSERT权限失败、DML事务失败的残留schema/history；5个新恢复目标回到旧基线，真实写作提交/幂等回执/父链保护、允许差异及重启逐值不变 | PASS |
| 旧列/媒体/引用保护 | 原列按PK比较；2段20句同版关联；FK1452/CHECK3819/UQ1062负例；原内容/事件/作文/复习/录音保持；恢复只新增获准隔离作文/evidence/receipt和对应投影 | PASS |

辅助完整性：检查7578条原执行记录，其中7367条具有rawLog的记录，其原始文件hash全部匹配；44份快照summary指向的私有快照hash匹配；10份公开Flyway日志与受控原件逐字节、hash一致。隔离候选JAR SHA-256为 `0aa22702023aa20d33405c2572e0469707fc41948ff985a687dc7fcec3ce3005`，本轮核实实际文件和其嵌入4份候选SQL完全匹配。

## 主控退出1的处理

保留的事故记录明确为12分项完成后独占创建既有 `result.json` 的 `FileExistsError`，错误处理再次碰撞；最终raw commands仍由finally保存。当前脚本已改用 `result-success.json` 和唯一失败文件名，修复夹具退出0而未重跑整组。

本次逐条原始日志hash、实际Flyway结果、各阶段快照和媒体/恢复重新核算均通过，未发现数据库阶段失败被汇总错误掩盖。旧 `result.json` 仍为历史BLOCKED；不能把当前已修复脚本当作原执行字节，也不能声称整组主控退出0。事故原进程退出来自保留的controller-finalization-failure记录，独立复核没有重新执行故障进程。这一工具问题作为明确注记签收。

## 版本时序与限制

- 10B-1当时源库V008，是历史快照；后续个人迁移最终报告及其20261027T204758证据记载V009.04，主代理上一轮现有API只读health也返回009.04。二者不是冲突。不得将STATUS中的sourceStillV008当作现状或改写历史证据。本代理本次没有连接当前个人MySQL验证完整history或私人行。
- ZIP receipt的PASS仅为打包完整性，未当作独立审查结论；此前用户豁免仅覆盖个人迁移，本次签收是新发生的独立代理技术审查。
- 原空库演练是V001–V008→旧Demo播种→V009.04；不证明10B-2“最新schema后初始化”已通过。普通启动重设current等既有业务问题必须由10B-2改造并测验，本次安全演练没有声称旧播种器对任意已有current安全。
- 本复核不证明当前全局无用户写入，不提供数据库全局审计、不代替真设备/实听/麦克风验收，也不确认正式素材授权。

原证据足以签收冻结迁移的历史安全性与恢复链，未发现阻止10B-2隔离开发的技术缺项。主代理可依用户本轮明确授权继续10B-2，但必须保留上述边界并在阶段结束如实报告未验证项。
