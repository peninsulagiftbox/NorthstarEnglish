# Phase 10B-1 数据安全演练证据包

最新结论：B01/B03功能演练PASS，主控汇总文件写入退出1的工具问题完整保留，独立离线审计退出0；等待独立复核，不授权个人库迁移或自动开始10B-2。入口为[STATUS.json](STATUS.json)、[最终审计](isolated-20261027t154428/final-audit.json)及[PHASE_10B_1.md](../../../progress/PHASE_10B_1.md)的“最终数据安全验收”。以下早期文件列表/旧BLOCKED是历史证据，未覆盖或改写。

- `PLAN.md`：目标、步骤、备份依赖、失败条件与预期证据路径。
- `preflight.py`：本轮实际执行的只读脚本；只读取本地文件并执行Git和定向docker inspect，不建立SQL连接，不启停服务。输出文件使用独占创建，禁止覆盖；原目录不能直接重复运行，复跑应另立新证据批次并复核路径。
- `baseline.json`：HEAD、预检时status、190文件SHA-256、8份迁移原字节对比、配置声明及未核实服务记录、JAR库版本/哈希、磁盘余量；不等于实时DB基线。
- `commands.json`、`probe-*.json`：脚本内部外部命令argv、时间和原始stdout/stderr/退出码。8次git show的退出码另在baseline逐项记录。外层脚本退出2见阶段报告/会话工具记录。
- `gate.json`：源容器身份不可验证时硬停止；没有DB连接、备份、迁移或服务操作。
- `acceptance.json`：六项证据及B01/B03总体状态；细项见报告。
- `verify_evidence.py`、`validation.json`：收尾本地机械校验及Git子命令真实退出码；外层校验脚本实际退出0，见阶段报告/会话工具记录，不代表业务测试。
- `SHA256SUMS.json`：本目录交付文件和报告的大小/SHA-256（清单自身除外）。

预检时间保留原始2026-10-26时间，报告于2026-10-27整理；没有伪造新一轮Docker/数据库探测。源码与配置中未确认事实均明确标记。目录不包含密码、个人SQL行或个人媒体；包含本项目绝对路径和本项目服务PID声明，分享前可按隐私要求另制脱敏副本，保留原件用于审计。

## 10B-1-R恢复预检批次

新结果见[恢复报告](../../../progress/PHASE_10B_1_RECOVERY.md)与recovery-20261027。根目录gate/commands/acceptance/validation仍是原轮次事实，没有覆盖。原SHA256SUMS.json针对当时交付；报告/本README追加前的版本已存originals，旧清单应对这些旧版本校验。新交付使用recovery-20261027/DELIVERY_MANIFEST.json，不重新运行会覆盖旧记录的verify_evidence.py。

新增docker_readonly_diagnostic.py、a1_readonly.py均为审查用只读工具；运行会独占创建证据目录，不能在原目录重跑。调用需要逐次核对权限范围；没有隐含批准服务启停、备份或迁移。Docker/SQL原始命令退出码、用户授权及脚本失败说明见恢复报告和对应JSON。

最新剩余预检见readiness-summary.json和readiness-20261027-attempt3；前两次失败独立保留。个人媒体逐文件清单仅.local私有保存，不打包。MAINTENANCE_WINDOW.md及maintenance_backup.py/resume_watchdog.py为待单独批准的窗口方案，尚未运行；candidate为隔离专用冻结候选，MigrationHarness.java已编译但未迁移。before-readiness-delivery保留本轮追加前报告/清单。后续签收仍必须以实际备份恢复和B01/B03为准。

## 最终交付入口

- maintenance-authorization-and-result.json、backup-20261027T154428：获批源18秒暂停/备份/原PID恢复，源无DDL/DML/Flyway启动。
- candidate/candidate-manifest.json：基线commit及4文件冻结SHA-256；仅隔离位置，不进入源应用迁移路径。
- isolated-20261027t154428：12个分项结果、7578条完整命令/原始退出码、每步旧列/schema/history/媒体摘要、5个续学event证据和最终审计。public-logs含10份无私人行/秘密且逐字节匹配原件的Flyway日志。
- 原始行HEX、作文、媒体、账号秘密仅.local；公开日志保留私有原件路径/hash。独立审核需在本机受控查看这些原件，不将ZIP冒称包含全部私人行。
- isolated-final-runtime-check.json：12个容器停止且卷保留，源原PID/health UP/V008；source-final-grants-readonly.json为真实root权限的只读证据。
- controller-finalization-failure.json、execution-attempt1-*等：真实退出2/1原样保留；controller-writer-regression.json与final-audit.json为独立离线修复/审计0，不伪称原整组进程退出0。
- before-final-delivery-20261027保留此次更新前报告/README/清单；最终ZIP仍用新时间戳，不覆盖旧ZIP。最新清单在recovery-20261027/DELIVERY_MANIFEST.json，根SHA256SUMS.json是最初历史清单。
