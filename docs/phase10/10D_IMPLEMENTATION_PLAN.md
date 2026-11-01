# Phase 10D 实施计划（待审核）

日期：2026-10-31，Asia/Shanghai。状态：**仅完成前置只读审计和计划；尚未授权实施，D01/D02 NOT VERIFIED。**

## 1. 执行边界与审核点

本轮任务要求先计划、确认后实施，因此本轮只新增本计划及脱敏元数据证据，不修改业务、迁移、既有工作树或运行服务。运行模式保持宿主设置，采用计划工作流，不将“正式开发任务”视为越过审核点的授权。

后续默认串行：批准10D-1 → 开发及D01/恢复验收 → `PHASE_10D_1.md` → 停止审核 → 另行批准10D-2 → D02/完整回归及恢复验收 → `PHASE_10D_2.md`、`PHASE_10D.md` → 停止。任何一步都不授权个人库升级、停写、服务重启、替换个人构建、Git提交推送或10E。

沿用Next.js App Router/TypeScript/Tailwind、Java21/Spring Boot/JDBC、MySQL8.4/Flyway。不增加账号、Redis、AI/ASR、复杂CMS、教学编排、OCR或课程批量导入器；不改全局运行时。

## 2. 已核对的实际基线

### 2.1 源码与未提交改动

- branch=`main`，HEAD=`ff0dbe1f8b89a1817c2f5a0e7ba0755d5f971188`。
- 起点已有7个tracked修改与9个untracked文件，集中在10C-2补验/R1：三份生产Java、两个既有报告、QuizScale测试、`.gitignore`，以及新增原子性/报告集成测试、补验报告和脚本。完整清单保存于`planning-baseline.json`。不能丢弃、覆盖或把这些全部算作10D新增。
- 实际源码包含`ReportController.quizFilter`的JDBC绑定、ID的`CAST(? AS BINARY)`、统一`QuizSets.verifiedRunClause/verifiedRun`，以及历史调用路径；R1不是当前HEAD单独可重现的内容。开发基线定义为**HEAD + 当前工作树逐文件SHA-256**，已保存Java/Web/脚本清单。实施前复核漂移，隔离源码副本必须复制这些未提交修复。
- `PHASE_10C_2_R1.md`记载40项Java/MySQL、报告历史与兼容浏览器通过；用户提供的独立验收结论为PASS。本轮只确认修复在源码，不冒称重新运行过这些测试。
- 应用最近聊天清单中，相关10C-2聊天为idle，既有UI聊天为notLoaded，未发现另一条active的同仓库UI聊天；该清单不证明没有外部编辑器任务。起点`apps/web/src`无未提交修改，后续每个UI切片前复查Git及文件hash；发现漂移先保留并核对，不覆盖。

### 2.2 个人运行环境（本轮实时只读）

| 项目 | 事实 |
| --- | --- |
| Web/API | 127.0.0.1:3100 / 8085，两个health均UP，返回011.09 |
| API进程 | PID29357，cwd=`apps/api`，回环监听 |
| Web进程 | PID29370，cwd=`apps/web`，回环监听 |
| 个人MySQL | `northstar-english-mysql-01`，127.0.0.1:3308，MySQL8.4.9，项目身份匹配 |
| 个人schema | `northstar_english`，utf8mb4 / **utf8mb4_0900_ai_ci** |
| Flyway | 最高011.09；39条成功记录，含version=0的历史记录；仓库实际迁移SQL为38份，两种计数不混用 |
| JAR SHA-256 | `45f129a68cf6e1bf11b3e8e6079e687e8f6853065adbf853da639524b8897532` |
| Web BUILD_ID | `QPO_SW0F17dBswwrGvsh-` |

上述JAR/Web身份与原部署报告一致，仍是R1之前的个人候选；011.09不能证明R1已部署。**个人环境更新不是10D前置执行动作**，隔离候选采用修复后的源码即可。

最高迁移`V011_09__quiz_freeze_guards.sql` SHA-256：`3c901eecd4e0ad0ba37e94f5709fce0d9ea7a4cbb8850272fa2ba1a73bbf24ca`；全部38份见`planning-migrations-sha256.json`。实施前后保持这些文件字节不变。

本轮读取个人库时显式只读事务，仅查询project身份、history及information_schema；未查询个人attempt原文、作文或录音记录。第一次本地健康/Docker访问受沙箱阻止；经只读权限扩展后成功。一次审计脚本因环境未显式配置DB_NAME而中止，随后按application.yaml实际默认值读取，未修改配置。

### 2.3 已有结构与业务约束

实际个人库的字段、PK/UQ/FK元数据完整记录于`planning-schema-readonly.txt`，并与SQL/源码交叉核对：

| 对象 | 实际约束/10D影响 |
| --- | --- |
| knowledge_point | id/lesson_id/version_id/sentence_id、term/meaning/usage_note/example_text；id+version+sentence唯一，同版句FK；保留旧ID/内容 |
| 收藏 | 实际表名为`vocabulary_favorite`，knowledge_point_id PK，favorite/updated_at；不存在要改名的favorite表 |
| reading_question | exercise_id PK，version/sentence/knowledge_point/payload_json；旧题和旧词条同句复合FK不可放松 |
| exercise | id/lesson/version/sentence/kind/algorithm_version；仍有真实主锚点；V007已删除单句单题唯一性，不重加 |
| exercise_attempt | UUID id及唯一event_id，真实lesson/version/sentence/exercise、correct、result_json和server recorded_at；V011.01已有(id,exercise_id,version_id,sentence_id)唯一键 |
| learning_evidence | attempt与event均唯一，组合FK到attempt；知识关联不是新一次学习证据 |
| quiz_run_item | (run_id,exercise_id) PK，attempt唯一，ordinal、set/hash/question_json；与run、冻结item、answer和attempt有复合FK |
| review_item/source | 卡有local owner、target/card_kind、due/reps/row_version；source以attempt为PK，保持同句上下文 |
| review_result | event_id PK→receipt，(item_id,previous_row_version)唯一；只允许again/good，origin=self_rating |

`ExerciseController.command`以回执事务封装听写/阅读；`QuizReviewController.submit`在同一父命令中创建N条attempt/evidence及轮次，保留派生子event规则。必须在这些事务内部追加知识快照，不能after-commit补写。

现有SimpleScheduler：again为服务端现在+1分钟；good按既往成功次数安排1/2/4/8/16/32天，上限32天；again重置reps。旧rate在事务中锁卡、核对rowVersion/到期/翻卡、追加result并更新卡；回执处理优先于重复执行业务。10D不扩大旧rating枚举。

实际缺口：阅读服务端explanation硬编码beside及第6句；听写仍校验`sentenceId + '-dictation'`；发布snapshot白名单不含新知识关系；ExportController内容分类和data-transfer schema版本白名单需同步。新关系不能只建表而不接发布冻结、权限和恢复。

### 2.4 已阅读资料

AGENTS、README、总实施计划、一期桌面设计的布局/知识/复习/证据约束、phase10的02/03/04/06/07/08/09、10C-1和10C-2报告、RETEST、R1及部署报告均存在。依据实际Java/SQL、前端阅读及复习组件、发布/访问控制、导出及恢复脚本制定以下方案。

## 3. 10D-1：概念、出现位置与冻结证据

### 3.1 概念身份、规范化和人工登记

- `knowledge_concept`：opaque ASCII id（沿用≤64规则）、kind、canonical_key VARCHAR(255)、sense_key、展示名、来源/审校状态、created_at；当前确认解释从追加修订中读取。UQ(kind,canonical_key,sense_key)，四种kind显式CHECK。
- canonicalKey只在登记入口执行NFC、Unicode空白首尾去除与连续空白折叠为ASCII空格；不转大小写、不删标点。按Unicode码点数检查255上限，空值/规范化后超限422，不用Java UTF-16长度冒充MySQL字符数。
- **显式列级`utf8mb4_0900_bin`**作为候选，不能继承个人库ai_ci；在隔离MySQL先验证大小写、重音、直/弯撇号、连字符、补充平面字符、尾空白及唯一性，再确定DDL。NFC等价输入经应用归一后应冲突，不同kind/sense允许并存。DB二进制排序本身不负责执行NFC，登记写入账号只经统一入口，runtime无概念写权限；不声称任意root直接写入也会自动规范化。
- senseKey由人工登记的稳定义项标识决定。bank金融/河岸分开，grammar与vocabulary同名分开；不提供按term猜测、自动合并或相似度归并。
- 最小离线人工登记服务/命令，不新增公网CMS。记录sourceRef/proofRef/reviewer/reviewedAt/status/reason。只有confirmed概念及映射进入学习来源；未确认清单显式可查。
- 用追加式`knowledge_concept_revision`保存解释/审校修订；attempt记录修订ID和当时展示语义快照。改解释不改旧快照；改义项建立新概念。复杂合并工具延期，不提供原地批量重绑或删除被引用概念接口。

### 3.2 出现位置与旧映射

- `knowledge_occurrence`：id、concept_id/revision_id、lesson/version、scope、paragraph/sentence、usage_json、来源及审校信息。建立(id,version,concept)及必要上下文唯一键；版本→课、段→版本、句→版本复合FK。
- scope CHECK：lesson两者NULL；paragraph仅paragraph非NULL；sentence必须sentence非NULL，paragraph可空；若同时保存paragraph/sentence，使用句(id,version,paragraph)支持唯一键+复合FK校验包含关系。服务入口统一验证scope和引用，不依赖UI。
- `legacy_knowledge_link`保留knowledge_point_id原身份，occurrence唯一，显式保存version/sentence/concept、mapping_basis/reviewer/status；双端复合FK锁定原位置。未确认不插入伪映射，用登记结果的未映射清单列出原因。
- 不用相同句序或stable identity证明语义等价。首版使用明确审核的合成fixture映射；真实Demo若无可靠审校材料保持未映射，不能因为有旧meaning就宣称人工审核完成。

### 3.3 练习关系及发布冻结

- `exercise_sentence`：(exercise_id,sentence_id) PK，version_id，role=primary/supporting，同版FK；服务端保证恰一primary等于已有exercise.sentence_id，可用生成列唯一键确保至多一个primary。多来源均为真实句，不增加伪整课句。
- `exercise_knowledge`：(exercise_id,occurrence_id) PK，version/concept/revision、role=target/support；同版exercise及occurrence复合FK。lesson/paragraph级occurrence还须验证与题目真实源句的范围相符；句级occurrence必须在exercise_sentence集合中。target与support显式人工登记，不能全课词汇自动标target。
- 建议增加小型`knowledge_projection`（version PK、登记协议、审核信息、canonical关系hash、frozen标记）。它封存该版的occurrence/legacy/练习来源关系，记录全局概念修订；冻结后禁止增删改成员。新发布先验证并封存，再进入原发布事务；不能对已冻结集合静默补目标。
- 已发布旧Demo的关系只能通过显式审核的单次附加投影登记封存，不改旧payload、content hash、publication快照或quiz-set-v1 hash；旧版既有attempt默认无知识快照，不倒灌为当年已测量。没有可靠材料时保持无映射即可。
- 新版增加知识关联采用显式新profile/投影协议，使现有basic/audio profile与既有validation digest保持可重放；不改旧题集hash算法/旧回执DTO。profile只增加知识关系验证，不实现10E解析导入流程。
- 用实际需要的冻结触发器/最小权限约束保护上述关系，恢复工具须处理冻结触发器装载顺序。不可变性不是仅靠“UI没有编辑按钮”。

### 3.4 attempt快照和事务接入

- `attempt_knowledge`：(attempt_id,occurrence_id) PK，exercise/version/concept/revision/role，以及schema化来源snapshot_json/hash、server创建时间；复合FK回attempt真实题/版/主句，回冻结exercise_knowledge和occurrence，不级联删除。
- 快照包含当时概念kind/key/sense/展示解释、usage、scope、源段/句ID及全部题目来源句、角色、正确性和算法/证据ID；通过attempt→learning_evidence/quiz_run_item可继续钻取。存储与接口分别执行内容权限，撤回后不能因snapshot内有原文而泄露。
- 服务端从已封存关系生成全部target/support关联；客户端不接受概念ID作为来源。旧无关联题目继续正常提交，返回无概念来源，不产生假关联。
- 阅读、听写、测验N题三个路径在原attempt事务内调用同一来源记录服务。听写从数据库解析真实exercise上下文并保留旧拼接ID兼容；不改变english_token_v1评分或旧请求哈希。
- 回执重放不补写后来的概念来源；同event异payload保持409，失败全事务回滚，N题仍全成或全败。R1统一verifiedRun和报告分母不得因多目标JOIN膨胀，报告不直接累计attempt_knowledge行数。
- 阅读反馈改取对应payload explanation及真实来源集合；旧已存回执/result_json原样读取，不改历史说明。新响应的附加字段通过兼容DTO提供，不改变旧event计算。

### 3.5 10D-1 API与UI

新增`GET /api/v1/knowledge/concepts`（课程/版本可选过滤）、`/{id}`、`/{id}/occurrences?cursor&limit`、来源详情（以attemptId定位）。返回kind、sense、出现的可见课程去重数量及列表、段句位置、相关题、真实attempt和客观复测“未验证”状态。

分页采用稳定唯一键的keyset cursor，有界limit≤100，坏cursor/上下文422；外部值全部绑定，不拼接筛选值。统一复用VersionAccess、课/许可可见性规则；出现数和列表同一权限口径，先过滤再分页。历史撤回来源仅给原ID/日期和受限占位，不给正文、讲解、选项答案或音频路径。

前端在现有VocabularyPanel/阅读反馈增加概念详情及来源入口，保留旧收藏与知识点API、旧句子跳转；新增最小知识详情组件/API类型。维持1440×900、224px侧栏、约2:1学习区、76px播放器；不修改播放器。所有新增视图覆盖loading/success/error/empty、撤回、分页和重试。

## 4. 10D-2：独立概念卡与复习来源

### 4.1 数据及来源规则

- `concept_review_card`：opaque id，owner_key=`local`，concept_id、prompt_kind=`meaning_recall`、protocol_version=`concept_self_v1`，scheduler_version=`simple_v1`，due_at/reps/row_version/status及server时间；UQ(owner,concept,prompt_kind,protocol)，due索引。
- `concept_review_source`：(card_id,attempt_id,occurrence_id) PK；复合FK保证card概念与attempt_knowledge概念一致。只从真实错误attempt的**target**追加；support不触发卡。错误代表“关联题答错”，不宣称已证明每个知识点都是错误原因。
- 一题多个target可进入各自概念卡，但不把同attempt重复计入总体正确率；两课共享概念归一张卡，所有attempt/occurrence来源保留。成功作答不会删除旧错误或自动清空历史。
- 首次错误建卡即到期；后续新错误追加来源并按既有规则使due=min(旧due,server now)、reps=0、row_version+1。仅首次插入新来源时更新一次，event重放不能再次重置。与attempt事务一致。
- `concept_review_result`：event PK→command_receipt、card FK、previous/next due、previous rowVersion/reps、rating/origin/scheduler和server时间；UQ(card,previous rowVersion)，仅追加。

### 4.2 调度、CAS与回执

首版只支持again/good，复用SimpleScheduler和既有reps语义；hard/easy不是本期必需项，不悄悄用good算法映射。保留独立概念卡协议，旧simple_v1历史结果不重算。

接口`GET /api/v1/concept-reviews?due&cursor&limit`、`/{id}`、`/{id}/answer`、`/{id}/sources`、`/{id}/results`。评价带eventId、rowVersion、rating、answerRevealed和客户端日期；服务端Clock决定now/间隔，客户端日期只供追溯。

复用现有command事务：先处理已保存回执，再锁卡并核对owner/rowVersion/到期/翻卡；INSERT result、UPDATE card和回执同事务。不同event竞争同rowVersion仅一成功；同event同payload并发均获得同一结果；异payload409；提交后响应丢失重试仍返回原due/reps/version。新错误追加与自评并发通过同卡锁串行，不静默覆盖更新。

若来源全部撤回，列表/详情显示受限来源状态，答案与新评价按可见性拒绝；历史result保留，仍允许原成功回执幂等重放。不能在卡提示中泄露撤回语境。概念自评不创建exercise_attempt/learning_evidence，不修改correct_count或报告成绩；无正式客观复测则始终显示“未验证”，10F评量不提前实现。

### 4.3 前端

`/review`分组展示旧句卡和新概念卡；尽量新增ConceptReviewCard组件，复用现有Primitives、outbox和时间展示。新outbox key独立含cardId/protocol，保留原event重试；不清旧IndexedDB或迁移旧卡。

展示到期、词义/类别、提示、翻卡、自评历史及全部多源分页；每条来源可回到原课/版/句/题/attempt。清楚分列题目错误证据、复习自评和客观复测未验证。刷新、双Tab冲突、断网丢回执、无数据及撤回均有真实状态反馈。

## 5. 迁移单元、权限与备份分类

当前最高V011.09；10D新增V012系列，以下为候选编号，实施前复查是否被其他任务占用。旧迁移38份不改。

| 切片 | 候选单元 | 内容 |
| --- | --- | --- |
| D-1 | V012.01 | 必需复合支持键（已有V011键复用，不重复建立） |
| D-1 | .02/.03 | knowledge_concept / concept_revision及审校修订引用 |
| D-1 | .04/.05 | knowledge_occurrence / legacy_knowledge_link |
| D-1 | .06/.07 | exercise_sentence / exercise_knowledge |
| D-1 | .08/.09 | knowledge_projection及冻结守卫 / attempt_knowledge |
| D-2 | 后续单元 | concept_review_card / source / result，各表独立建表单元，必要约束/守卫另拆 |

不为凑编号合并不可恢复的DDL；一个文件多条DDL时逐条列中断状态，不能声称MySQL整文件事务回滚。默认迁移不回填个人历史、不生成复习数据；有依据的旧映射由隔离登记步骤执行。每个新表均有PK、必要FK/UQ/CHECK/索引且明确恢复顺序。

分类：concept/revision/occurrence/exercise_sentence/exercise_knowledge为内容；legacy link与knowledge_projection为映射/审校元数据，纳入不可变内容基线及独立审计分类；attempt_knowledge与概念card/source/result为真实学习数据，不作可重建缓存。ExportController当前只有CONTENT/其余的分类机制，最小增补分类说明/元数据并维持旧协议，不省略任何表。

修改`ExportController`、`data-transfer.py`版本白名单、签名/行数守卫、依赖恢复及对应测试；概念不设反向current_revision外键，revision单向引用concept，当前解释查询最新确认修订，occurrence显式引用选定修订，避免恢复循环。不以disable FK掩盖顺序错误。恢复冻结触发器在受控全新目标装载完成后重建，核对原定义/hash及运行效果。

runtime只获得新学习表INSERT，卡获得必要INSERT/UPDATE，内容与审计只读；人工登记账号单独限权。**现有`grant-study.py`同时操作个人与测试schema，10D不得直接调用该入口**；使用经UUID/容器标签核对的隔离专用授权入口，不授个人库新权限。

## 6. 隔离环境、fixture与数据保护

- 独立`.local/phase10d/source`构建、测试媒体目录和证据目录，复制当前工作树R1源码；不在个人`target/.next`构建，不运行个人dev-up/down/db-test。
- 新建且只创建10D命名空间的容器/卷/schema，写前核验容器ID/标签/server UUID/项目标记/端口及schema。候选3335/API8176/Web3196须先探测空闲，冲突时选择新端口并记载，不停止占用方。
- 现有C2 runner的`prepare-tests`会DROP现存测试schema，不直接复用；只复用命令日志、UUID核验、快照比较等安全部分，10D创建唯一新schema，不删除/重建任何已有库或卷。既有3334 C2容器保持原状态。
- 固定旧备份只在私有目录读取并先校验manifest/hash；选定实际存在的基线备份，记录其真实版本与时间范围，先用对应旧工具恢复，再升级011.09→D-1→D-2。不能称它包含备份之后的个人新增学习数据。无需对个人库新备份或停写。
- fixture A“Community Workshop”：2段12句；fixture B“Riverside Science Day”：3段24句；原创完整不同文本，许可/审核字段明确为合成测试。共享bank金融义项，另有bank河岸；加入grammar、collocation、pattern及同名跨kind，多个occurrence。包含同题两源句、多个target及support、lesson/paragraph/sentence scope。
- 通过正式API分别产生两课真实错误及正确尝试，不能INSERT attempt冒充已走提交流程；否例直接SQL仅限隔离约束/异常测试，标明用途。配套合法测试媒体满足实际听写音源门禁，不引用个人录音或未经许可教材。
- 全部旧表旧列逐PK逐值比对（含回执原文/hash、时间、due/reps/rowVersion），38份迁移、内容/录音媒体逐文件SHA-256比较；新增学习行为的增量单独记录。失败库/卷保留，不清理、repair、改history或伪造baseline。

## 7. 验证矩阵及执行顺序

所有下列均为**待执行**；规划期没有应用测试通过结论。每次命令记录北京时间/UTC、cwd、argv（脱敏）、HEAD+源码manifest、原始exit、日志hash；失败原件保留，后续重跑另建文件。

| 验收组 | 实际执行要求与通过条件 |
| --- | --- |
| D01 1–7 | Java规范化+真实MySQL：空格、撇号、连字符、NFC/NFD、Unicode空白、多空格、空/超长、255/256码点、大小写/标点/重音；共享义项复用、bank两义、跨kind同名分开；UQ正反例 |
| D01 8–14 | A/B全部结构和三scope；有依据映射及未映射；多源句、多target；错课/错版/段句包含错/外题/外occurrence逐项服务及FK负例 |
| D01 15–17 | 客户端伪concept参数不能影响来源；同event重复/并发/异payload；听写/阅读/quiz逐路径知识写入故障注入，所有attempt/receipt/evidence/来源全成或全败 |
| D01 18–20 | 课→版→段句→题→attempt→occurrence→concept/revision完整钻取；新版本/新解释不改历史；撤回后正文/答案/音频/来源数均不绕权利控制 |
| D02 1–6 | 两课正式错误归一张卡、所有来源追加；义项/kind独立；重复事件不重置；source重复和FK负例；真实服务端due/reps及调度边界 |
| D02 7–11 | 同卡双客户端/不同event竞争、stale rowVersion、同event并发、异payload、commit后丢响应/重试；新错误与自评竞争；结果写入/卡更新/回执故障；重启due/reps/version原值不漂移 |
| D02 12–18 | 旧卡全部原值保留；自评不生成attempt/客观成绩；多源UI/刷新/空队列/错误/撤回；最终备份恢复后全部来源/状态与CAS/event重放一致 |
| 迁移 | 固定旧备份升级、V001空库、每个主要DDL边界中断、DML回滚、history登记失败识别；从原备份到另一个全新目标恢复，不repair |
| 恢复续学 | D-1恢复后实际听写/阅读/quiz并重放；D-2恢复后实际概念自评及旧句卡复习/重放，再重启逐值核对；新表schema/索引/FK/触发器及媒体hash一致 |
| 旧回归 | Demo完整闭环、10B身份/显式发布、10C-1共享/独立音频与恢复坐标、10C-2动态题量/冻结题面/历史分母/原子性、R1绑定边界及7类异常verifiedRun |

每个切片先定向Java单元/真实MySQL集成，再运行隔离副本中的完整Maven verify；必须启用实际DB配置并核对0 integration skipped。Web运行项目Node22的`npm test`、`npm run typecheck`、`npm run lint`、`npm run build`；Python运行`python3 -m unittest discover -s scripts/tests -v`及新增迁移/恢复脚本测试。沿用现有Playwright工具/脚本，禁止测试写请求连接个人3100/8085，先核验测试DB响应头及UUID。

浏览器D-1验证两课概念浏览、多义项、多源阅读/attempt钻取、版本切换与撤回；D-2验证多源卡、旧新分组、自评/刷新、双Tab CAS、断网与丢回执，留1440×900截图及必要响应尺寸回归。播放器代码不改不重做240次声学测量，但实际播放/定位/恢复必须回归。实体麦克风/Safari等未测单列NOT VERIFIED。

DDL失败库记录schema领先history状态，不将ROLLBACK当DDL恢复；无回填DML的迁移单元标N/A并说明，人工映射登记事务仍注错验证回滚。history插入失败在专用故障目标演练，另起恢复目标重新跑。任何旧值无法解释的变化、半条来源、卡源被覆盖或R1回退均NO-GO。

## 8. 文件范围、证据与交付

预计业务文件：新增Java `knowledge/`关系/登记/查询/快照服务和`conceptreview/`控制器；定向修改ExerciseController、QuizReviewController、ContentPublication、ExportController及必要Catalog访问复用。保持ReportController/QuizSets的R1逻辑，除非集成测试证明必须调整且单独说明。

前端预计：新增`lib/api/knowledge.ts`、`lib/api/conceptReviews.ts`、知识详情/概念复习组件；定向修改VocabularyPanel、ReadingQuestion、ReviewQueue、API类型及最少样式。不改播放器、不整站重构。新增V012 SQL、Java/Node/Python/浏览器测试与原创fixture、隔离runner、data-transfer恢复适配、OpenAPI及本阶段报告。

证据目录`docs/handoff/evidence/phase10d/`当前仅含规划基线，后续按D-1/D-2/故障/恢复/浏览器拆目录。原个人备份、完整私密日志、学习正文及录音留私有`.local`，共享证据只含合成数据和脱敏摘要。

最终生成`output/review/northstar-phase10d-sanitized-evidence.zip`：逐文件白名单收录计划/报告、SQL、关键Java/TS/测试、原创fixture、真实命令/exit/成功失败日志、截图、恢复与对账摘要、SHA-256清单和独立校验脚本。排除.env/密码、Token、Cookie、个人SQL/学习/作文/录音、未授权教材；分别记录原始与脱敏文件hash，说明可独立复算项和只能看摘要项。不能直接zip整个目录。D-1交付先生成对应切片证据，不提前写D02通过。

最后结论按实际结果选择PASS / CONDITIONAL PASS / FAIL / NOT VERIFIED，核心D01/D02/恢复缺失不能用conditional掩盖。10E进入条件为10D实现、实际证据与独立验收通过，再单独审批。

## 9. 本轮检查结果与待批准内容

已完成：Git/源码R1静态核对；38份迁移SHA-256；个人health、MySQL版本/字符集/排序规则/history与真实字段/键的只读查询；本地JAR/Web身份及进程cwd核对；实际实现与阶段资料审查。仅新增计划及三份规划证据。未运行Maven、Node、Python业务测试、MySQL迁移实验或Playwright，D01/D02及10D实现状态均NOT VERIFIED。

待用户确认：接受上述设计及串行边界，**仅开始10D-1代码开发、全新隔离环境和D01/恢复验收**。确认要求来自用户本轮任务§2.3“先输出计划，取得用户确认后实施”，以及AGENTS“阶段报告后停止等待审核”；不附带个人升级、部署、提交或10D-2授权。
