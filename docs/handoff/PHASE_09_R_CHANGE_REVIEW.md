# Phase 09-R 候选变更审查

2026-10-26。用户已批准打包修复、本地候选 commit/tag、隔离测试与真实库 V008 元数据只读查询；没有推送、业务逻辑修改或真实学习库写入授权。

## 原有未提交改动（相对 Phase08 21b5651）

| 文件 | 差异与影响 |
|---|---|
| .env.example | 增加恢复实例端口说明；没有实际凭据 |
| README.md | Phase09运行和验收说明；09-R删除互相矛盾的重复“未开始”行 |
| apps/web/src/app/globals.css | 原Phase09已将辅助色 #687b96 改为 #5f7088；09-R不改产品样式 |
| scripts/local.py | 既有容器只start、新容器no-recreate；拒绝覆盖运行中缺失构建；校验Web转发端口 |
| scripts/data-transfer.py | 原Phase09新增独立恢复目标；09-R另加 --phase09r，源DDL/依赖查询也只访问专用测试容器 |
| docs/BACKUP_RESTORE.md | 独立恢复、只读回访与续学步骤 |
| docs/DEPENDENCIES.md | 历史依赖和验证记录；不是本次复验结论 |
| docs/DESIGN_DEVIATIONS.md | 对比度及布局偏差记录 |
| docs/IMPLEMENTATION_PLAN.md | Phase09执行状态与CLI测试路径更新 |

## 原有新增文件

- infra/compose.recovery.yml、scripts/recovery_mysql.py：原Phase09独立恢复实例、端口/容器/卷身份检查。
- scripts/regression-runtime.py：原Phase09三种运行模式与构建副本；09-R改用专属工具，不调用其默认主容器路径。
- scripts/check-snapshot.py：逻辑表/列/值与ready录音哈希比较，可创建新0600快照。
- scripts/full-learning-loop.js、release-boundaries.js、release-revisit.js、release-accessibility.js、release-fresh.js、release-continue.js：学习闭环、故障、重启回访、UI抽样、零数据、恢复续学。
- scripts/release-browser.sh：浏览器入口、隔离标记、trace与结果检查。09-R增加精确专属容器和API进程检查，输出独立证据目录。
- scripts/release-safety.py：来源/绑定/错误/JS秘密/日志检查。09-R仅对专属实例和构建副本运行。
- scripts/tests/test_recovery_guards.py：原Phase09恢复守卫测试。
- docs/progress/PHASE_09.md、docs/TEST_REPORT.md、docs/RELEASE_CHECKLIST.md：历史阶段结论与未验证边界。
- docs/handoff/、northstar-packages.sha256：原独立交接报告、打包工具和证据；旧失败记录全部保留。

## 本次新增或修复

- freeze_sources.py：补.java；主源码和测试文件集合、数量、哈希必须与真实工作区一致。
- verify_packages.py：检查精确ZIP条目集合、内部SOURCE_FILES.json及32个Java文件集合与哈希。
- package_handoff.py：源码包说明绑定候选SHA；继续秘密扫描和路径脱敏。
- scripts/phase09r.py：两台专属MySQL、独立源码/构建副本、媒体/进程、最小表权限、逐命令原始退出码、候选哈希、真实报告计数比较。只创建新卷，不删除或重建既有数据。
- scripts/phase09r/MigrationProbe.java：只读元数据与Flyway validate；无migrate、repair、baseline或历史写入。
- scripts/tests/test_phase09r_guards.py：错误身份/绑定/端口/卷及私人库名拒绝测试。
- release-boundaries.js：补充播放拒绝和回放前后人工自评边界；六个JS脚本截图改到phase-09r目录，旧截图不覆盖。
- evidence/phase09r/previous/：旧交付清单与包哈希；旧ZIP保留在本地忽略目录。旧日志不编辑或删除。

## 冻结与证据边界

候选commit包含原Phase09范围与09-R测试/打包修复；Java业务源码、迁移SQL和产品交互逻辑本轮不改。候选后仅新增证据和更新验收文档/包元数据。候选源码变动必须另建候选并重跑受影响测试。

全程不启动主站、不使用私人学习快照。真实库仅以既有app账号查询V008和user_setting列元数据，并运行Flyway validate；不读取学习行、不写历史表。源码ZIP仍不含待审音频，完整音频复现仍需要本地原哈希素材，不代表授权已通过。
