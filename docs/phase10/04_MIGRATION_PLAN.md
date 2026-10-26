# Phase 10A · 04 兼容迁移与数据保护

状态：待审方案；本轮没有运行任何SQL、备份、Flyway命令或服务操作。所有V009以后编号仅为分组提议，实施前按可独立恢复单元继续拆号，不修改已执行文件。

## 1. V001–V008逐项分析

依据为 `apps/api/src/main/resources/db/migration/` 全部8份SQL，以及 `ContentSeeder`、`StudyController`、`ExerciseController`、`QuizReviewController`、`ExportController` 和 `scripts/data-transfer.py`。

| 历史迁移 | 可保留的不变量 | 新模型影响/预检 | 兼容策略与校验 |
| --- | --- | --- | --- |
| V001 | local设置、项目身份FK、速度/保留策略、row_version | 不需要多用户/账号；新增功能不能重置偏好 | 不改；所有原列逐值比较；新列另算 |
| V002 | 许可、册课版身份、内容哈希、current复合FK、句序/稳定键 | book只catalog_only；kind缺普通original、source_kind缺original_recording；start=0、音频唯一；无paragraph | 只在新增迁移放宽指定CHECK/UNIQUE、增段落/身份/状态；保留旧PK、payload、hash与所有上下文FK |
| V003 | local单恢复点、CAS、课版句FK、六Tab | 缺按课恢复；后续任务不是新增Tab的理由 | 保留最近入口；增按版恢复表并确定性拷贝已有一条；不推断丢失的浏览历史 |
| V004 | receipt幂等、attempt/evidence/event、草稿与五态、原错题来源 | 新关系应使用现有event链；位置原为独立句文件偏移 | 不移动学习记录；position_ms继续句内偏移，服务检查改为end-start；导出包含新关联表 |
| V005 | 旧课内knowledge_point、favorite、reading/question/answer/progress | reading FK同句；全局概念不应替换旧表 | 增concept/occurrence/links，不批量改旧词条ID或同句FK；旧favorite与answer逐值不变 |
| V006 | 不可变writing_revision、source/parent链、录音状态/哈希、三选一evidence | 媒体独立、startup reconcile会写；段落输出需新任务关系 | 备份SQL+全部登记录音状态+文件清单；恢复前后原文/父版本/文件hash一致；迁移不启动reconcile |
| V007 | quiz_run/answer、复习唯一卡/到期/CAS/结果历史 | correct_count≤3；无total；旧review_source同句；旧DML拆卡/删无源卡不能重放 | 新迁移按每轮真实答案回填total，新增快照；不重跑V007数据改写；概念卡另表；due/reps/row_version逐值一致 |
| V008 | recording_enabled及偏好历史 | Phase08曾DDL提交后历史登记异常；09-R只读validate已核对当时元数据 | 重新预检schema/history/checksum，不把历史报告当当前证明；不再次ADD列、不repair/手工复制历史 |

初始化的 `project_identity` 来自 `infra/mysql-init.sh`，Flyway自建history，不编造V000。保留这两张表并验身份。

## 2. V009起的增量顺序

| 组/拟编号 | 阶段 | DDL、回填与部署顺序 | 完成门槛 |
| --- | --- | --- | --- |
| V009 课程组织 | 10B-1演练候选；10B-2读取；10B-3身份/发布 | 独立单元扩展lesson.kind增加original、audio_asset.source_kind增加original_recording（保留原CHECK值，来源许可枚举不变）；paragraph、identity/映射、版本publication/content_readiness字段及最小发布审计、lesson排序、册availability CHECK；先可空列→确定性回填Demo段落/人工确认身份→校验→必要NOT NULL/FK | Demo原列不变；新段句同版；新版程序不再用启动器验证全局四册catalog_only或覆盖指针 |
| V010 共享音频 | 10C | 先补同版引用所需索引；解除音频唯一与start=0；保留/新建非负及区间CHECK；增lesson_audio、对齐审校元数据 | 独立句和共享音轨均能读取；所有旧区间仍0..duration；播放器/恢复点新版同时部署 |
| V011 动态测验 | 10C | 加题集/本轮快照表与可空total/submitted等列；DML按quiz_answer回填；核对一致后改NOT NULL/新CHECK并取消0..3 | 不盲填3；每轮correct与实际答案一致；旧轮恰好3仍保留；非法历史阻塞迁移 |
| V012 跨课知识 | 10D | concept/occurrence/exercise/attempt关联和新概念复习表；旧点人工映射；新表复合索引/FK | 旧卡不重排；历史只有确定关联可投影，来源可溯且不伪造新的学习时间 |
| V013 导入审计 | 10E | import_batch/import_entry、包hash/目标版本/预期指针/结果状态；复用10B-3最小发布审计 | 内容DML与状态提交规则清楚；import账号权限受限；失败不影响已发布指针 |
| V014 教学/评量 | 10F | learning_plan/step/task/instance/progress/task_evidence/output/assessment、attempt_context、跨课客观复测关联 | 一项证据去重；五层报告可复算；旧记录exposure unknown，绝不改成独立评分 |
| V015 恢复点/查询索引 | 10F | 按课版本恢复表，复制当前一条；测量确认后加(lesson_id,version_id,recorded_at,id)等索引 | Explain及容量测量支持必要性；旧入口CAS仍有效；备份/恢复工具支持全部新表 |

实际每组可包含多个DDL，必须为每条编写前/后置断言和中断状态表；若恢复单元过大，实施前拆为多个连续版本并更新此表，不能为凑编号牺牲安全。新的Flyway文件第一次应用后永久冻结。

### 2.1 10B-1前置硬门禁与证据包（R4）

**任何候选迁移只能先在隔离恢复副本和空数据库执行；没有两条路径及失败恢复的实际PASS证据，不得迁移现有个人学习数据库，也不得把指向个人库的Spring启动当验证。** 10A-R只写计划，不连接DB。10B-1是独立待授权阶段；10B-2、10B-3另行验收与批准。后续每次新增/修改迁移，均重做对应两条路径及相关恢复，10B-1通过不是对未来DDL的通行证。

10B-1交付本地受限证据包（公开报告仅放摘要/路径/hash，不含私人行值）：

| 必记证据 | 记录内容与通过条件 |
| --- | --- |
| 当前数据库与Flyway基线 | 只读确认源项目身份/schema/端口/运行版本、schema定义与history全部行/校验和；迁移候选源码hash；V008实际列与history一致，异常即停止 |
| 备份与媒体 | 一致停写快照的SQL/内容/全部登记录音状态与文件清单、大小/SHA-256、时间与备份ID；备份可读且实际恢复验证，缺文件差异逐项解释 |
| V008→目标新版本 | 在该备份的隔离恢复副本上，记录每条迁移/回填前后状态、Flyway原始日志/退出码、schema与历史摘要；固定目标迁移集合/hash |
| V001→目标新版本 | 新建隔离空库，只执行项目身份初始化和冻结迁移链，不baseline、不复制history；记录V001起完整初始化及重启/重复执行一致性 |
| 失败恢复演练 | 在副本模拟DDL部分成功、history登记失败、DML回填失败；识别状态并停写，从同备份恢复到另一个新目标，验证旧版读取/真实续学/重启；保留失败副本，不改history或clean |
| 旧数据完整性对比 | 迁移前后按PK对所有旧表旧列逐值比较，摘要辅助且逐项解释白名单；ID、payload/hash、event/receipt、作答、草稿、作文父链、复习到期/版本及媒体hash/状态无意外变化 |

以验收矩阵B01/B03逐项PASS为数据安全Go；环境受限或任何实际演练缺失标BLOCKED/NOT VERIFIED，不能仅凭SQL评审/编译替代。10B-1完成后停止提交报告，未获后续批准不切换现有库、不开始10B-2。未来切换还需固定候选通过、备份新鲜度复核、停写窗口及用户的执行授权。

## 3. 迁移前预检：不启动Spring来做“只读”

Spring启动可能触发Flyway、ContentSeeder和录音reconcile。拟用独立只读预检程序，核验目标schema/项目身份/连接回环/端口/进程cwd/账号角色；拒绝其他项目库和未声明目标。读取配置只提取必需字段，秘密不进命令行、报告或Git。

预检必须输出（私人行值仅保存本地受限备份，不进公开文档）：

1. `SHOW CREATE TABLE`、列/索引/约束实际定义、Flyway完整签名与本地V001–V008哈希；无failed/pending异常，V008列与history匹配。自动CHECK名称从information_schema确定，不能猜 `sentence_chk_N`；DDL执行前验证表达式确为start_ms=0。
2. 全表行数、按主键排序的规范化行摘要；所有旧表原列快照；lesson.current、各版本/许可/媒体hash、receipt与作答/证据/草稿、作文父版本、review_source/result/due/reps/row_version。
3. quiz每轮：answer数>0、correct_count等于关联attempt.correct之和、无重复题/外课/外版、receipt/证据完整；原Demo轮若不是3题即阻塞，不能以3补平错误数据。
4. FK孤儿检测、句区间合法、文件路径/大小/hash、登记ready/missing/pending/deleted状态；已知缺文件列清单并人工确认，不通过启动reconcile掩盖差异。
5. 剩余磁盘≥实测SQL+媒体+隔离恢复副本+迁移临时空间再加20%余量；执行窗口/数据量/表锁预算、源DB与媒体实际路径。未同步浏览器草稿/outbox先提示同步或单独导出，不能丢弃或代提交。

## 4. 备份、演练与切换

采用停写维护窗口，单用户不需要在线迁移复杂度：

1. 核验并停止仅本项目写服务，保留DB运行；确认无导入器/浏览器outbox写入，记录停写时间。冻结内容发布与媒体变更。
2. 使用已有备份入口的能力并先审查其配置，生成SQL结构+数据+Flyway历史及内容/私人录音文件副本、权限与hash清单；快照JSON可作辅助，不能替代媒体/DDL备份。凭据独立保存，不纳入共享包。
3. 在新命名隔离schema及新媒体目录恢复V008快照，用冻结旧程序验证全部表原列逐值、录音hash、旧课播放、作文/错题可读。原库/卷不删除或覆盖。
4. 优先在该恢复副本执行V009起的目标迁移、升级程序和回归；保存每条DDL前后状态与Flyway原始日志。失败停在副本，原库不受影响。
5. 只有隔离副本升级、空库初始化、故障恢复及完整性比较全部实际PASS并审核后，才讨论现有库切换；先重新比对旧表原列，只有审批列出的新增字段/投影允许变化。可选择将验证过的新副本作为新本地库，需记录切换目标与权限、媒体目录并核验配置。原库保留；若另行批准原库就地升级，也必须先有同一候选迁移hash的上述完整实际演练、新鲜备份，并保持整个窗口停写；10B-1本身不授权该操作。
6. 验证成功才恢复写入；记录schema版本、源码commit、内容清单与浏览器origin。不因换DB而换Web origin，避免丢失IndexedDB。

不把某条DDL称为可整体事务回滚。MySQL的DDL隐式提交与单语句atomic DDL不是多语句事务：[MySQL 8.4事务文档](https://dev.mysql.com/doc/refman/8.4/en/commit.html)。Flyway说明MySQL失败不能干净回滚：[迁移事务处理](https://documentation.red-gate.com/fd/migration-transaction-handling-273973399.html)。本方案据此选择小步、状态检查与副本恢复。

## 5. 失败分类与恢复路径

| 失败位置 | 可保留状态 | 处置 |
| --- | --- | --- |
| 预检/备份失败 | 源数据未变 | 停止迁移，修复前置条件；不继续上线 |
| 第一条DDL后/后续DDL前失败 | 部分DDL可能已提交 | 停止写入；记录实际schema/history，不能直接ROLLBACK后重试整份SQL；优先丢弃“作为候选”的资格并保留失败副本供审计，在另一个新schema重建副本再演练，不删除已有库 |
| DDL全部成功但Flyway登记失败 | schema可能领先history | 隔离目标，人工核对每项；本计划不授权repair、baseline或手写history。默认从备份到新目标重演；确需协调history另提专项审核 |
| 回填DML失败 | 若独立事务可回滚DML，DDL仍保留 | 标记阻塞，检验无部分回填；不要给出“全部已恢复”结论 |
| 文件搬移/校验失败 | 文件可能有孤儿，DB可能尚未提交 | 内容不发布；保留文件/批次日志，不自动清理源文件；重试验证与恢复详见06 |
| 新程序读/写回归失败 | 维护窗口内无新学习数据 | 保持停写，切回保留的旧库+旧二进制+旧媒体，核验哈希与旧契约 |
| 放开写入后发现问题 | 新库已存在新event/作文/录音 | 禁止直接切旧库丢增量；停写、立即备份新库/媒体，单独设计增量前向修复/合并，逐event保护；不承诺通用自动降级 |

禁止Flyway clean、重建原卷、删除现有库、忽略checksum、批量disable FK、全局版本更换。旧二进制也可能拒绝新schema或重设内容，因此“仅回滚代码”不作为默认恢复方案。

## 6. 跨schema历史备份与验收

当前 `ExportController.preview` 严格要求同schema/CONTENT一致，应保留拒绝行为。V008快照先在隔离目标用V008工具恢复，再通过新增迁移升级；不能在新库编辑JSON的schemaVersion假装兼容。新内容表必须加入CONTENT、学习关联表按FK顺序恢复；`scripts/data-transfer.py` 的schemaVersion=008硬编码、迁移签名、表依赖/白名单/计数守卫一并更新与测试。现工具依赖图从实际FK读取，运行账号INSERT/UPDATE表名单仍显式配置，新增表必须明确分类和授权，不能只让自动枚举“碰巧备份到”。

Go条件：升级路径和空库从V001起路径均成功；旧表旧列100%逐值一致（仅批准的扩展列例外）；全部旧媒体hash/状态可解释；主键/外键负例有效；重复启动零重复、零current覆盖；恢复副本实际续学、重启后再次一致。任一差异无法解释即No-Go，不以测试总数代替数据校验。
