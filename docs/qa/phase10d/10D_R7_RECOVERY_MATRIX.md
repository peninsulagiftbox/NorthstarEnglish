# Phase 10D-QA R7 恢复验收矩阵（R7-SPEC 待审核）

日期：2026-11-04（Asia/Shanghai）。状态：**SPEC REVIEW REQUIRED / M03–M08 NOT VERIFIED**。本文件先核对编号来源，不把 R7 建议补充写成历史批准用例。用户审核编号映射后，才按冻结候选执行故障与恢复验收。

## 1. 编号来源与边界

| 编号 | 原始定义与来源 | 核定状态 | R6 证据现状 |
| --- | --- | --- | --- |
| D01-M03 | `10D_QA_TEST_PLAN.md` §7：DDL 部分提交、DML 回填失败、Flyway 登记失败演练 | **原始已定义**，但未定义具体 V012 单元、注入命令和分项通过条件 | 普通 SQL 1054 探针及截断备份；未运行真实 Flyway 链，**NOT VERIFIED** |
| D01-M04 | 同上：新表进备份/导出恢复链，包括 ExportController 分类、`data-transfer.py` 白名单 | **原始已定义**，未定义独立容器/卷要求 | R6 在同容器新 schema 恢复，生成列有数据且逐值一致；端到端独立恢复 **NOT VERIFIED** |
| D01-M05 | 同上：旧媒体 hash 不变、恢复后真实续学 | **原始已定义**，未定义非空录音数量和单独容器要求 | R6 恢复后续学子实验通过，录音数为 0；完整媒体及独立环境 **NOT VERIFIED** |
| M06 | 在已审阅的 `docs/phase10/`、`docs/qa/phase10d/`、`docs/progress/`、QA 执行源码中未找到正式定义 | **SPEC_UNDEFINED** | R5/R6 报告有笼统的“M03–M08”，不构成定义 |
| M07 | 同上 | **SPEC_UNDEFINED** | 同上 |
| M08 | 同上 | **SPEC_UNDEFINED** | 同上 |

`10D_D02_QA_RISK_CLOSURE.md` 中的“M05/M06 复用容器”是风险描述，并未给 M06 写目标、步骤和 PASS 条件。`04_MIGRATION_PLAN.md` §2.1、§5 和 `08_TEST_AND_ACCEPTANCE_PLAN.md` 的 B01/B03/F04 对安全恢复提出要求，但不把它们命名为 D01-M06–M08。`03_TARGET_DATA_MODEL.md` 是逻辑设计，`09_PHASE10_IMPLEMENTATION_PLAN.md` 是阶段依赖；二者也不是这些编号的定义。

## 2. 已定义项目的可执行细化（原编号，R7 细节仍待审核）

| 项目 | 用例目标与前置数据 | 拟执行命令与注入点 | 预期结果、恢复步骤、数据保护范围 | PASS 条件与当前状态 |
| --- | --- | --- | --- | --- |
| D01-M03.a | 隔离源自合法 V011/早期 V012 备份启动；至少有旧课、Attempt、复习和媒体摘要。验证 V012 多 DDL 单元部分提交。 | **尚未执行，命令待 R7 QA 启动器落地**。经 UUID/卷/端口守卫启动真实 Spring Boot/Flyway；仅测试启动器在选定迁移 DDL 成功后、下一语句前终止进程。先选迁移 SQL 中实际存在可观测多语句边界的单元，不修改正式 SQL。 | 保存失败目标 schema、history、MySQL 错误及进程退出信号；重启不得误判成功或盲目重复不安全 DDL。源备份与旧值不变；从同一已验备份恢复到**另一个**目标并运行正常迁移及读写。 | 实际 Flyway 日志、退出码、对象逐值对账、失败现场及新目标续学齐全才 PASS；当前 **NOT VERIFIED**。 |
| D01-M03.b | 同一隔离基线；选有实际 DML 回填的迁移。 | **尚未执行，命令待定**。真实 Flyway 迁移执行期间，在受控 DML 边界注入故障，不用独立手工 SQL 冒充。 | 查明 DML 是否回滚及已提交 DDL；Flyway history 与表状态一致可解释；旧行不变。保留失败目标，另建新目标恢复重演。 | 原始 Flyway/SQL 错误、逐行前后摘要、正常恢复与业务读写齐全；当前 **NOT VERIFIED**。若 V012 没有符合条件的 DML 单元，应注明不适用，并以经审核的替代真实迁移单元执行。 |
| D01-M03.c | 隔离基线及真实 V012 迁移；预先确认迁移用户、history 写入路径。 | **尚未执行，命令待定**。受控故障仅阻断该版本 history 登记，发生在 DDL 已提交之后；不得手写 history、repair 或修改迁移 checksum。 | 记录对象已存在而 history 缺失/失败；重启不能正常开放不一致应用。保留原故障目标，从备份到新容器/库正常迁移。保护全部旧表、媒体和备份。 | 已提交 DDL、登记失败、重启阻断、安全恢复四段原始证据齐全；当前 **NOT VERIFIED**。 |
| D01-M04 | 隔离库含知识概念、修订、出现位置、练习与 Attempt 知识快照、概念卡来源和结果，`knowledge_occurrence.location_guard` 有非空行。 | **尚未执行 R7 命令**。先静态比对 ExportController 分类和 `scripts/data-transfer.py` 普通列白名单；在身份守卫通过后调用原版脚本 `backup`，再在新目标调用 `restore`；精确 argv、cwd、版本与退出码写入唯一 runId 日志。 | 新旧表按 PK/普通列逐值比较；生成列重新计算后逐值相同；history、CHECK、FK、触发器一致；无 MySQL 3105。源库不变，失败目标保留。 | 导出分类、全表/列、完整性约束和实际恢复均通过才 PASS；R6 同容器子实验 **PARTIAL**，R7 **NOT VERIFIED**。 |
| D01-M05 | 隔离源含合法旧课学习历史、旧句卡及至少一条有数据库关联的非空原创录音。 | **尚未执行 R7 命令**。经 UUID/卷/媒体根守卫，备份数据库和媒体到独立恢复容器/卷；启动独立 API，调用旧课/音频/复习/提交接口，重启再读。 | 录音文件大小、SHA-256、元数据/Attempt 关联、HTTP 读取及 Range 一致；旧行旧值不变，新增学习事件另列；旧课可续学，重放同 eventId 无重复。 | 媒体、DB、API、续学、幂等及重启均有原始证据才 PASS；R6 无录音，当前 **NOT VERIFIED**。 |

上表的“拟执行命令”均不是实际执行记录。正式执行时须记录完整 argv，不使用本矩阵中的描述作为运行日志。若无法在真实 Flyway history 写入路径精确注入，M03.c 保持 NOT VERIFIED。

## 3. R7 建议补充的编号映射（不是历史批准定义）

| 建议编号 | 目标及前置数据 | 拟执行命令与注入点 | 预期、恢复和数据保护范围 | 建议 PASS 条件 / 当前状态 |
| --- | --- | --- | --- | --- |
| **R7 建议 M06** | 独立灾难恢复：源与恢复目标为不同容器、卷、UUID、端口和媒体目录；源有两课、多版本、知识/Attempt/概念及旧句卡、Quiz、写作历史和非空原创录音。 | **尚未执行，命令待定**。经两端身份守卫，使用原版数据导出/恢复链；核对 `--separate-mysql` 的实际目标身份和媒体路径，必要时新增 QA 适配器，不修改 CORE/迁移。 | 全表原列和新表逐 PK 逐值一致，生成列、history、FK/CHECK/触发器、录音 hash 与 API 读取一致；恢复后合法新增数据单独记账。源和旧 QA 卷不变。 | 新容器/卷恢复、API 可用、原数据保护和复算证据齐全；**SPEC_UNDEFINED / NOT VERIFIED**。 |
| **R7 建议 M07** | 备份和恢复中断安全：同样的非空隔离源，另设每项独立故障目标。 | **尚未执行，命令待定**。分别在备份写入、校验、数据库导入、媒体复制、DB/媒体不一致、恢复后 API 启动边界注入；记录信号和退出码。 | 不完整备份不能标 COMPLETE，不完整目标不得被当作可用；源/失败现场保留；从有效备份到新目标重试成功；无虚假学习记录。 | 八类建议场景逐项有原始日志、状态对账及安全重试；**SPEC_UNDEFINED / NOT VERIFIED**。 |
| **R7 建议 M08** | 恢复后业务兼容：使用 M06 完整恢复目标，含旧 Demo、D01/D02、10C-1、10C-2 历史数据。 | **尚未执行，命令待定**。真实 API/Web/Playwright 与正式集成套件执行读取、练习、概念/句卡复习、同 eventId 重放、录音播放及重启。 | 旧 ID/payload/hash/Quiz 分母/写作父链/音频恢复点不变；合法新增事件、CAS 和来源独立对账；故障不产生客观练习证据。 | D01 全量、旧 Demo、音频和动态 Quiz 关键回归、重启后逐值对账齐全；**SPEC_UNDEFINED / NOT VERIFIED**。 |

## 4. 执行与签收规则

1. 先审核 M06–M08 建议映射，以及 M03 的具体迁移单元和注入机制。审核前建议项不能计入正式 M03–M08 PASS；未取得历史原定义也不能称其为“原始用例”。
2. 所有数据库写入只允许在新建、UUID/卷/端口/媒体根均已验证的 R7 专属目标。个人 3308/3100/8085 和已保留 3348/3349 仅可只读识别，不连接进行写入或 Flyway 启动。失败目标原样保留。
3. 每个实验用唯一 runId 保存 argv、cwd、开始/结束时刻、退出码/信号、stdout/stderr 与 SHA-256、冻结候选清单 SHA、DB UUID、迁移前后对象/history、普通列逐值及媒体摘要；失败日志不能被成功重跑覆盖。
4. R6 `r6-restore-result.json` 只证明同容器新 schema 的非空数据和生成列恢复；`r6-fault-probe-result.json` 自称 PARTIAL，不能证明 Flyway history 注入。R6 B08/B09、Node/Java/浏览器结果仍是各自候选和场景的历史证据，不自动扩展为 R7 PASS。
5. 本轮 R7-SPEC 未创建数据库、未运行迁移或应用测试。Docker 只读列表在当前沙箱返回 socket `permission denied`；因此当前容器及个人服务实时状态尚未核实，任何后续执行都需重新完成只读身份检查。

参考：`docs/qa/phase10d/10D_QA_TEST_PLAN.md` §7；`docs/phase10/04_MIGRATION_PLAN.md` §2.1、§5；`docs/phase10/08_TEST_AND_ACCEPTANCE_PLAN.md` B01/B03/F04；`docs/qa/phase10d/10D_D02_QA_R6_FINAL.md` §M03–M08；`qa/phase10d-final-r6/evidence/r6-restore-result.json` 和 `r6-fault-probe-result.json`；`scripts/data-transfer.py`。这些文档提供要求和历史结果，但不补造 M06–M08 的原定义。

## 5. R7 执行补充（2026-11-04）

用户已确认按 R7 建议映射执行：建议 M06 为独立灾难恢复，建议 M07 为备份/恢复中断安全，建议 M08 为恢复后兼容回归；M03 仍按 D01-M03 原始编号执行。本节只记录实际运行后的结果，上方原始核定文字保留不改。

| 编号 / 用例 | 状态 | 关键证据 |
| --- | --- | --- |
| D01-M03.a DDL 多语句边界中断 | **NOT VERIFIED** | 未构造“DDL 成功后、下一条语句前进程终止”的独立注入；已有用例只覆盖 history 登记失败。 |
| D01-M03.b V011.06 事务内 DML 回填失败 | **PASS** | 第二套 3390 目标命中 `exercise_set_item` INSERT 的 MySQL 1142；前一事务写入回滚，history 尾部为 `011.06 success=0`。3389 首套因夹具重复键 1062 未达注入点，`result-correction.json` 标记不计 PASS。 |
| D01-M03.c V012.10 history 登记失败 | **PASS** | 3387 目标中 V012.10 DDL 已提交但 history 未登记；重试被阻断且旧行不变。故障前备份在 3388 新卷恢复并迁移至 012.11。 |
| D01-M04 全量独立恢复 | **PASS** | 3397 final2 目标与 3385 源库 UUID、卷、端口独立；59 表逐值一致，生成列 3 行，录音 SHA-256 一致。 |
| D01-M05 恢复后真实续学 | **PASS** | 3397 恢复副本读取旧课/概念/来源/录音，新增 Attempt 后同 eventId 重放回执相同；重启后关键表哈希一致。 |
| R7 建议 M06 | **PASS** | 3386 与 3397 两次独立容器/卷恢复均通过；3397 是包含完整写作历史的最终用例。 |
| R7 建议 M07 | **PARTIAL** | 截断备份、校验和错误、非空录音缺失均在建目标前拒绝。但删除 `COMPLETE` 后原版 restore 仍返回 PASS 并创建新目标，属于确认缺口；备份过程、恢复过程、媒体复制与 API 失败中断四类未执行。 |
| R7 建议 M08 | **PARTIAL** | 知识规范化、音频、Quiz 原子性、3397 续学和浏览器旧课播放通过；旧 Quiz 复习套件确认 `review_result` 可 UPDATE。混合 20 套件运行因共享库污染与音频环境变量缺失失败，不计产品缺陷。 |

## 6. 2026-11-05 P0/P1 修复补充

- P0：`scripts/data-transfer.py` 已新增 `COMPLETE` 存在性与内容一致性预检；缺失或不匹配时在任何 API 预检和目标创建前拒绝。
- P1：新增 V012.12 `review_result_no_update` 触发器，禁止 UPDATE；不添加 DELETE 触发器，避免影响既有测试清理路径。
- 修复验证：`QuizReviewIntegrationTest` 在全新隔离容器通过；history 到 012.12，触发器存在。P0 的缺失/不匹配 `COMPLETE` 单元测试通过。
- M07 整体仍为 PARTIAL：备份过程、恢复过程、媒体复制中断和 API 失败可诊断性仍未验证。M08 仍为 PARTIAL：D01 全量、旧 Demo 完整闭环和 10C-2 全量未重跑。

## 7. 2026-11-05 剩余门禁执行结果

| 编号 / 用例 | 状态 | 关键证据 |
| --- | --- | --- |
| D01-M03.a V012.02 多语句 DDL 边界中断 | **PASS** | fault-ddl2 容器：语句 1 提交、语句 2 服务端 KILL + JVM SIGKILL、history 缺失；重跑 1061 + `012.02 success=0`；API 启动失败可诊断；基线备份在新容器迁移至 012.11 并续学/重放。`qa/phase10d-final-r7/evidence/fault_ddl2/m03a-inject-result.json`、`m03a-retry-result.json`、`m07-api-failure-result.json`、`m03a-recovery-result.json` |
| R7 建议 M07 备份/恢复/媒体/API 四类中断 | **PASS**（8/8） | `qa/phase10d-final-r7/evidence/r7-m07-interruption-result.json`：备份目录 SIGKILL 无 COMPLETE、restore 拒绝且未建目标、重试 PASS；恢复中断目标仅 1 表且关键行缺失、重试逐表一致；媒体复制阶段 SIGKILL 无 PASS、重试媒体齐全；API 启动失败证据同 M03.a |
| R7 建议 M08 全量兼容回归 | **PASS** | ROOT 全部 47 项测试分两组通过：`suite_full5/r7-full5.log`（46 项）+ `suite_full6/r7-full6.log`（1 项）；旧 Demo 完整闭环 7 项检查通过：`r7-demo-loop-result.json` |

分组原因与 P2 观察见 `10D_R7_FINAL_ACCEPTANCE.md`「2026-11-05 剩余门禁收口」。首轮注入现场（fault-ddl 容器：两条 DDL 已提交、history 缺失、重跑被 1061 阻断）原样保留作操作风险记录。
