# Phase 10C-2 实施计划与工程审计

日期：2026-10-31（Asia/Shanghai）。状态：**AUDIT COMPLETE / PLAN PENDING APPROVAL；尚未实施业务代码或迁移**。

当前工具没有切换 Plan 模式的入口，本文件是书面计划，不声称已经切换模式。依据用户粘贴任务“审计完成后……计划经用户确认后实施”，本轮止于只读审计和计划。批准记录目前为空；后续批准与修订追加记录，不覆盖本轮基线。

## 1. 授权与保护范围

- 后续实施限动态测验、真实历史分母、最小阅读反馈解耦和隔离测试；不进入10D跨课知识、10E导入器或10F评量协议。
- 不迁移个人库，不启动指向个人库的新版Spring，不暂停个人服务，不部署、不提交或推送Git。
- 保留10C-1未提交源码、SQL、报告及音频证据；不更换全局Node/Java、不重建既有数据库或卷、不删除录音/作文/草稿。
- 测试使用新命名独立MySQL容器/卷/UUID、账号、媒体与构建目录。端口选空闲回环端口，身份核验后记录，不能假定旧10C-1资源仍空闲。

## 2. 必读资料及真实基线

已查阅根AGENTS、README、IMPLEMENTATION_PLAN、phase1桌面规范适用章节、10A-R的03/04/07/08/09、10B-3及部署报告、10C-1与最终R_C01报告；核查当前OpenAPI、V004/V007和V009/V010相关约束、测验/练习/发布/报告/导出实现、前端草稿/outbox及相关测试。必读文件均存在。

### 2.1 当前实时证据（非沿用报告）

证据：`docs/handoff/evidence/phase10c2/preflight-20261031T000340.json`，采集于北京时间00:03:40。SQL使用现有应用账号，`REPEATABLE READ` + `START TRANSACTION READ ONLY`；不启动Spring、不调用写API。容器标签、卷、环回绑定由现有`local.verify_container`核验。服务健康GET与SQL是相邻观测，不声称整个个人环境已停写。

| 项目 | 实测 |
| --- | --- |
| Git HEAD | `49239c61f53caed0a996dbce9156c7c6db259dc7` |
| 初始工作区 | 22个已跟踪文件修改，另有10C-1新增Java/六份V010/报告/脚本/证据；原始status保存在预检JSON |
| 个人MySQL | 项目标记匹配，127.0.0.1:3308，schema `northstar_english`；Flyway末条009.15，success=1，checksum=1720131740；完整history在证据中 |
| 个人API | 127.0.0.1:8085，PID83359，cwd为`apps/api`；health UP/009.15 |
| 个人Web | 127.0.0.1:3100，PID83589，cwd为`apps/web`；经同源代理health UP/009.15 |
| 运行命令所指JAR文件 | SHA-256 `c4243bca0b7062e2c94bbe6e78fe7e5603791173c615959a4819a5f6ecdfc310`；归档内没有V010，不把工作区候选当成个人已部署版本 |
| 当前Web磁盘BUILD_ID | `udzk9U3KedJsnKrExMKWg`；不是10C-1隔离候选BUILD_ID |
| 并行UI观察 | recent 20条聊天内，本聊天之外未发现active的本项目聊天；“重设计课程预览 UI”为notLoaded。globals.css/CatalogPages.tsx未列入当前修改。不能排除外部编辑器或之后新改动；实施前再次比对hash |
| 个人历史测验 | 2轮、6条答案，均demo-01-v2，每轮实际3条；逐轮检查issues为空 |
| 孤儿检查 | quiz_choice attempt无quiz_answer=0；指向不存在attempt的learning_evidence=0 |

历史检查覆盖run→版本/课、answer→attempt→题目同版同句同题、选项合法、correct与题库/反馈一致、run.correct与逐题汇总一致、父回执run/答案响应一致、稳定子UUID及子payload_hash重算、子回执/反馈一致，每题恰一条同attempt/event证据。此结果仅覆盖本次快照和已列检查，不能替代隔离回填与完整旧列对账。

尚不能证明：父命令原始请求字段/Map顺序未持久化，未重算父payload_hash；旧表不保存完整题面和独立ordinal；没有浏览器IndexedDB枚举，不声称旧本机草稿/outbox为空。迁移不得改写旧回执来消除这些限制。

### 2.2 V010冻结清单

当前最新候选为010.06，六文件均在未提交工作区，**个人库尚未应用**。与10C-1报告中的SHA-256一致；全部迁移的当前hash另存预检JSON。

| 文件（位于apps/api/src/main/resources/db/migration/） | SHA-256 |
| --- | --- |
| V010_01__sentence_audio_support_index.sql | `7bc1fa8d6922d0ec7da5664207ab8e46e2d556fa684a4f41fe8cd1585bdda4ff` |
| V010_02__shared_sentence_audio.sql | `0ac726507959edc2dc00e6e0bff260295c339fbeb2d55af0ae4a2df95f51a67a` |
| V010_03__nonzero_sentence_interval.sql | `5baee0d899d1a3bca327fe0c6b42ee220ca978eac3a7ce814c3b100fa99c85f8` |
| V010_04__lesson_main_audio.sql | `41389882ef45462ffdb51acfc62fd63cc7e275c9e436a0e571a36e522ca7cec4` |
| V010_05__audio_alignment_review.sql | `b119897658fddc176f4398ef41c274a2526fc03c2be52c46be2b302e0950de1c` |
| V010_06__explicit_playback_resume.sql | `30573cd3b6618a13a15cd50fb4ed7816de5dd0ce4e322b203c096a7504f484f4` |

实施前再次固定相关源码hash（本轮16个关键文件见audit-source-hashes.json）与迁移集合。如有外部变化，重新审查影响，不能覆盖其他聊天改动。

## 3. 真实代码审计结论

| 位置 | 当前事实 / 最小影响 |
| --- | --- |
| V007 quiz_question | `exercise_id`就是PK，并通过(exercise_id,version_id,sentence_id)引用exercise；知识点也有同版同句FK。不存在“所有题目还需重新分配exercise_id”的缺口，保留原ID |
| V007 quiz_run / answer | run只有correct_count和时间，没有分母/题集/题面快照；CHECK为0..3。answer的PK已禁止同run重复exercise，attempt唯一；已有FK只校验attempt同版同句，仍需收紧到同exercise |
| QuizReviewController | DTO恰3，运行时questions.size/answers.size恰3，按exercise_id排序，GET仅去answerKey/explanation；历史没有分母、排序快照。响应已经包含答案/解释结果快照，应保留 |
| ExerciseController.command | `SHA256(operation + ':' + mapper.writeValueAsString(value))`；先重放，再一个TransactionTemplate插父回执→业务→写响应→提交，DuplicateKey后回查。测验子事件使用nameUUID(parent:exercise)，child hash算法另为SHA256(parent:exercise)。全部保留 |
| ContentPublication | quiz_question已纳入关系快照，但发布校验只接受0或3；新增题集也必须进入验证快照，防validated后变更 |
| ContentSeeder | 显式空库初始化中的冻结Demo仍要求3题，且有特定please知识点映射。这是Demo适配，不能删掉后误改冻结原包，也不能当新课程模板 |
| QuizPanel | 布局本来已map动态渲染，硬编码集中在文案、结果/历史分母及从sentenceId.slice(-2)猜句序；草稿键只有versionId，历史文案查当前选项而非本轮快照 |
| ReportController / LearningReport | 总分母COUNT(*)*3，UI“每轮3题”；无筛选。零记录当前是暂无数据，不应退化为默认100% |
| 阅读路径 | 词条排除`version-kp-please`；服务端反馈固定beside/第6句，ReadingQuestion新结果与历史标签也写死第6句。VocabularyPanel已按用户选择和实际句子查词，不需要重做默认首词逻辑 |
| 导出恢复 | ExportController按实际表枚举，但CONTENT显式分类；data-transfer按FK拓扑恢复并有显式权限名单/schemaVersion白名单，必须同时修改，不能只依赖自动发现 |
| 既有测试 | QuizReviewIntegrationTest只覆盖Demo三题、部分非法请求、并发重放、复习CAS与重启；没有1/5/12/100题、快照分母及四个故障点的对账。ReportExportIntegrationTest校验correct，缺少混合分母验证；现有Node测试没有完整动态测验草稿覆盖 |

没有独立Quiz Repository：当前控制器直接JDBC，DTO是内部record。本阶段沿用JDBC与现有事务能力，只提取有明确职责的题集读取/哈希和测验服务，避免为对称而新增层级。

## 4. 目标数据模型与冻结策略

1. `exercise_set`：opaque id、version_id、purpose、protocol_version、context_group_id可空、set_hash、frozen标志/时间；当前只启用practice + quiz_choice_v1。新增同版UQ以支持复合FK。每版明确一个默认practice题集；无题版本不造可提交空题集。
2. `exercise_set_item`：set_id/version_id/exercise_id/sentence_id/knowledge_point_id/ordinal，以及冻结题面、选项、answerKey、explanation、题目hash。PK(set_id,exercise_id)，UQ(set_id,ordinal)，ordinal>0；同版FK到set、quiz_question、exercise及知识点。1..100与连续顺序在冻结门禁校验；不只靠客户端数量。
3. `quiz_run`：增加total_count、submitted_count、set_id、set_hash、exposure_status、measurement_policy_version。历史与当前普通练习均不能凭空声称独立测量，缺少证据时为unknown；不推断延迟保持或迁移能力。
4. `quiz_run_item`：run_id/exercise_id/version_id/sentence_id、ordinal、set_id/set_hash、题面/评分快照、attempt_id/option_id；PK(run_id,exercise_id)，UQ(run_id,ordinal)、attempt唯一。同版FK到run/set/item，且与quiz_answer的run/exercise/attempt一致。为attempt补同题复合候选键，封住“同句另一题”的来源漏洞。
5. 保留quiz_answer及全部旧PK/原列；快照为新增投影，不移动历史对象。新完整run必须total>0、submitted=total、0≤correct≤submitted。accuracy只派生，不持久化成唯一权威成绩。

哈希覆盖版本、purpose、评分协议、上下文、有序题目身份、题面、选项（含顺序）和正确答案。实施时固定UTF-8字节规范与golden vectors；SQL回填和Java必须输出同一hash。优先使用MySQL规范JSON文本作为冻结字节，Java读取该文本计算，不混用Java重新序列化与数据库JSON表示；有序逐题hash拼接须有明确长度/边界并覆盖100题，不受GROUP_CONCAT默认长度截断。若无法做到一致，停止冻结，不采用两个各算各的hash。

题集与课程版本共同冻结。新课程通过既有显式初始化/发布流程建立题集，禁止普通启动补题集或修改current；新内容不使用Demo适配。发布验证涵盖新表及hash、合法选项、真实来源、数量和顺序，已冻结题集禁止UPDATE/DELETE及追加item（迁移/内容权限与数据库冻结保护共同约束）。换题面/答案/顺序必须新LessonVersion、新setId/hash；读取旧版本不跟随current。

历史回填前将旧题库与冻结Demo原包及其hash、旧反馈answerKey/选项/来源逐项核对。ordinal按旧服务端`ORDER BY exercise_id`确定性重建，标记为legacy reconstruction；不声称保存了用户屏幕上的随机选项顺序。题面无法可靠还原的轮次输出异常明细并阻塞对应回填，不拿最新题目覆盖旧事实。旧字段、父子回执和result_json不更新。

## 5. V011迁移单元与中断恢复

以下是预留单元；实施前确认不存在新V011，按实际DDL依赖细拆，文件第一次执行后冻结。**本轮未创建任何V011 SQL**。

| 单元 | 内容 | 前/后置与故障检查 |
| --- | --- | --- |
| V011.01 | 必需同版/同题支持索引 | 检查真实index/FK，不猜自动名称；核验旧行值完全不变 |
| V011.02 | exercise_set | 表/唯一键/版本FK；每条DDL有独立状态记录 |
| V011.03 | exercise_set_item | 顺序/成员唯一、源题/版/句FK及冻结字段 |
| V011.04 | quiz_run新增可空字段 | 保留旧CHECK，历史原列不变 |
| V011.05 | quiz_run_item及必要复合引用 | 新表为空，旧answer/attempt关联可验证 |
| V011.06 | 只读断言后确定性回填DML | 独立事务建立旧题集/成员、run字段和item；任一异常SIGNAL并回滚，不留下半批；空库允许零历史 |
| V011.07 | 旧correct CHECK替换 | 从information_schema确认实际约束；单表ALTER保留上下界并改为真实分母关系，不能先无限制再另补 |
| V011.08+ | 非空/复合FK/冻结保护 | 先断言所有轮次已核验再收紧；触发器等按实际独立恢复单元继续拆号；最终版本号以批准实施后的清单为准 |

每单元记录实际schema/history/源hash及预期差异。DDL成功而history未登记、DDL部分完成、回填失败都必须能被状态探针识别。MySQL多语句DDL不是事务；恢复路径为保留失败目标，在新隔离目标用固定备份+冻结迁移重演，不repair/clean/手写history/删除失败库。DML故障验证新回填全回滚、旧行不变、既有DDL仍在。

个人只读预检不等于停写一致备份。本阶段使用经hash核验的旧受控备份恢复演练，不暂停个人服务生成新备份；报告明确备份截止时间。另在隔离副本复现本轮观察到的结构检查，不把隔离续学造成的增量当个人历史。若旧备份没有足够历史，使用真实原创题目经正式提交API产生隔离历史，不能直接INSERT虚构attempt。

## 6. 协议兼容、原子交卷与读取

- 保留旧`POST /quiz/attempts`、旧QuizSubmit record字段/顺序和operation=`quiz-submit`，保持旧payload hash算法与响应重放原文。只对已核验的冻结Demo默认三题执行旧协议的新提交；旧成功回执仍在业务门禁前重放。禁止把新字段加进旧record导致null也参与哈希。
- 新协议建议显式`POST /quiz/sets/{setId}/attempts`，DTO含protocolVersion、eventId、lessonId、versionId、setId、setHash、answers、clientOccurredAt，独立operation=`quiz-submit:v2`。路径与body的setId必须一致。沿用/api/v1命名空间，OpenAPI完整定义两协议。
- 服务器在现有统一command事务中取冻结集合，执行版本/许可/撤回门禁、set上下文、hash与答案键精确相等、每题选项合法校验；先全部评分，再写入。空集、漏题、额外题、错选项、跨课/版422，旧hash409，撤回410，许可门禁沿用现规则。客户端correctCount/total不是权威输入。
- 成功恰1父receipt、1 run、N item、N answer、N attempt、N evidence、N稳定子receipt；错题review_source等按已有真实业务规则追加，quiz_progress同事务更新。不另造study_event作为形式上的“事件计数”。
- 故障点：首题写后、末题写后、父响应回执写前、事务beforeCommit。通过测试专用注入/数据库拒写覆盖，不开放生产HTTP故障开关。所有失败用独立连接查询run/answer/item/attempt/evidence/receipt/review_source/状态，与失败前快照对账。
- 同event同payload并发借助父receipt唯一键及原command机制只成功一轮；异payload409。网络丢响应重放相同结果；不同event生成不同真实轮次。旧hash/子UUID算法不重定义。
- 旧成功响应没有totalCount，仍按原文重放；新UI依据响应runId查询已核验历史轮次取得分母，不用当前题集长度补齐旧回执，也不改写已保存response_json。
- GET `/quiz`保留旧questions/history/state，增加setId/hash/protocol/totalCount、每轮total/submitted/验证状态和来源sequence。可选setId读同版题集。历史结果使用run快照，不能查当前题面拼成绩。必要的历史分页使用新增独立端点，保留原响应形状。
- 历史测验专用读取应与“允许开始新学习”门禁分开：撤回版不接收新命令，但已保存run可读；正文受权利限制时只显示原标识/快照可用性，不泄露被撤回的受限内容。

## 7. 前端最小修改

QuizPanel保持现有六Tab与布局，继续按题目map渲染，增加已答/总题数及未答题提示；顺序来自ordinal，答案集合完整才启用交卷。支持loading/empty/error/retry/success，错误不丢选项和原event。

草稿与新outbox作用域为lesson+version+setId+setHash，保存协议版本。先获取题集再解析草稿；换作用域清空上一课的组件显示状态，再加载对应缓存。旧键`northstar:quiz:${versionId}`保留：只有成员/选项与已核验legacy默认题集完全兼容才可导入为新草稿；旧待同步命令按原path/body/event重试，不能升级payload。遇到未知成员/选项或新题集，显示“旧草稿与当前题集不兼容，已保留”，允许查看/导出，不能自动覆盖或删除。

成功/历史都用服务端真实totalCount，历史题面/选项/解释来自本轮快照。替换slice(-2)猜句序为实际source sequence或“返回来源句”；无源明确提示。保留首次/重做多轮历史，不以slice截断替代历史。首次GET与未提交DOM不得包含answerKey、解释或其他可直接反推答案的评分字段。

## 8. 报告口径与阅读解耦

ReportController保留原metrics.quiz.correct/total/runs，改为核验run的SUM(correct_count)/SUM(total_count)。增加verifiedRuns/unverifiedRuns及口径说明；未核验历史不猜分母，也不把其correct计入已核验分子。单轮和汇总由计数派生accuracy；1/3+4/5=5/8=62.5%，不平均两次百分比。

旧`GET /reports`默认无筛选行为兼容；新增可选lessonId/versionId/from/to/setId/purpose，仅对测验指标及新增逐run明细应用筛选，并在响应明确quizScope，不把未筛选的其他训练误标为同口径。时间采用UTC、from包含/to不包含；有purpose但无已实现协议时明确拒绝，不生成延迟/迁移指标。每个汇总可通过run详情复算，无正式run显示“尚无测验数据”。草稿/skip/pause、自评不进分母。

阅读反馈使用本版reading_question.explanation与其实际源句/sequence；无讲解显示“暂无本地预置讲解”，无可用来源显示明确提示。去除`-kp-please`全局字符串排除，词条展示按本版合法来源配置（冻结Demo仍按原payload词汇列表）；不改变已有Demo历史result_json。ReadingQuestion历史标题读取保存来源或实际对应句，不强写第6句。保留Demo初始化中合法冻结映射；不建立concept/occurrence/多源关系表，不扩展写作规则任务。

## 9. 测试与隔离验收（均为待执行）

| 组 | 必测与判定 |
| --- | --- |
| C02数量 | 1/3/5/12/100题经正式API交卷；逐对象计数及合法同版FK；100题完整提交、时间/payload/SQL实测，不静默截断 |
| C02拒绝 | 0题、漏题、外题、错选项、重复ordinal/成员、跨课/版、旧hash、撤回/许可失效；数据库零半轮残留 |
| 原子性 | 首题、末题、回执写前、beforeCommit四类故障，每类失败前后逐对象对账，恢复后原event可提交一次 |
| 幂等 | 同event同payload并发、丢响应/刷新重试、异payload409、不同event正常独立轮次；旧回执原响应/hash重放 |
| C03 | 1/3+4/5=62.5%；3/5/12多版本混合；新版本发布后旧分母/题面/答案不变；空/无记录/草稿/暂停/跳过/自评分离；异常历史拒绝回填或明确未核验 |
| 浏览器 | 5/12题进度、顺序、禁用/未完成提示、提交反馈/多轮历史、刷新草稿、跨课/跨版/跨题集、旧草稿隔离、旧outbox重试、断网/500重试；100题完整UI可操作；提交前无答案泄露 |
| 迁移 | 固定旧备份→V010→V011，V010.06基线→V011，空库V001→目标；真实历史预检、异常副本拒绝、UQ/CHECK/FK正反例、DDL/DML/history故障及新目标恢复 |
| 保全 | 旧表旧列逐PK逐值；Flyway旧history不变；作文/草稿/事件/回执/复习/录音状态与文件hash不变；后续真实续学增量单列 |
| 备份 | set/item归CONTENT；run_item加入学习导出与INSERT授权；schemaVersion白名单/同基线签名/拓扑恢复更新；真实导出→新隔离恢复→续学→重启；不能仅验证JSON可解析 |
| 回归 | Demo完整学习闭环，多课/多版、发布CAS、稳定身份、音轨与句音频、听写/阅读/录音/写作/复习/恢复点；不改播放器则不重做240次声学签收 |

沿用项目Node22/Java21及固定Playwright CLI，在独立源码副本/构建/媒体/服务执行，**不直接在主目录覆盖target或.next**。命令经现有阶段runner模式注入隔离配置并记录argv/cwd/时间/exit/log hash：Maven verify（数据库测试实际启用且不得skip）、npm test/typecheck/lint/build、Python unittest discover、相关Playwright脚本及Demo全闭环。环境阻塞保存原退出码，不能降级H2或借旧报告冒充新PASS。

## 10. 实施顺序与预计文件范围

1. 批准本计划后再次核验Git/迁移/hash/运行与端口，创建10C-2专属隔离runner，固定旧备份身份/hash。
2. 实现预检异常清单、V011小单元、题集与历史重建；先空库/升级/故障恢复，未通过不进入业务验收。
3. 实现新协议服务及旧协议桥接、快照读取、发布冻结、原子性/幂等/来源集成测试。
4. QuizPanel/草稿/历史及报告筛选和分母，最小阅读反馈改造，OpenAPI与类型同步。
5. 导出恢复分类/授权、完整回归、保全对账、最终候选重复启动与证据归档。

预计修改：api的exercise/quiz、report、catalog发布/显式初始化、exportimport及测试；web的QuizPanel、LearningReport、ReadingQuestion/reading类型与必要草稿辅助；docs/openapi；scripts/data-transfer及相关Python/浏览器测试；新增V011 SQL和10C-2隔离runner。保留10C-1播放器/音频/迁移文件字节。实际文件清单以最终SHA-256为准，不提前大范围重构。

## 11. 交付、风险和停止条件

完成实施后更新`docs/progress/PHASE_10C_2.md`，逐项给C02/C03及兼容/迁移/恢复PASS/FAIL/BLOCKED/NOT VERIFIED，绑定HEAD+工作区源码hash、新迁移SHA-256/Flyway实际checksum、命令退出码及失败原件。证据放`docs/handoff/evidence/phase10c2/`；个人行值/SQL/媒体放受限.local，仅分享脱敏摘要。

最终生成`output/review/northstar-phase10c2-sanitized-evidence.zip`，白名单包含报告/计划、完整新增迁移、关键Java/TS及真实测试源码、日志/对账摘要/截图、逐文件hash与独立校验脚本。排除个人SQL、答案/作文/录音、凭据/Cookie及未授权教材；不能只打包PASS文本。本轮尚未实施，不提前生成“完成交接包”。

主要风险：旧题面/顺序缺少独立历史字段；父请求原序列化不可直接从表还原；MySQL DDL领先history；新旧协议哈希串用；草稿作用域迁移丢稿；发布快照遗漏新内容表；共享工作区改动漂移。对应门禁如上，不用修历史数据或重算旧hash换PASS。

只有动态数量、事务/幂等、真实分母、草稿/历史、全部迁移恢复与保全检查达到用户验收规则，才建议10C-2 PASS。缺少真实数据库/浏览器/恢复证据就保持未通过。阶段完成后停止待审核；10D仅以已冻结的题集/本轮来源为前置，不在此阶段提前实现。

## 12. 审核入口

请确认本计划后再实施。确认仅授权本文件所列代码与隔离演练，**不包含个人库V010/V011迁移、服务部署、Git提交或推送**。

批准记录：尚无。
