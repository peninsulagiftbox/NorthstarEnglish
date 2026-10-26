# Phase 01–09 逐阶段审计

2026-10-26。源码根为解压后的项目根。阶段目标依据 `docs/IMPLEMENTATION_PLAN.md`、`references/phase1/Northstar_English_Phase1_桌面Web详细设计与验收.md` 和原 `docs/progress/PHASE_XX.md`。计划顶部仍停留 Phase 08，不能作为当前状态的唯一依据。历史报告不随本包直接分发；关键原始证据见 `evidence/historical/`。

以下“历史”均非本次运行。当前实际检查汇总见 [TEST_EVIDENCE](TEST_EVIDENCE.md)；所有数据库集成和业务写入 E2E 本次均 NOT VERIFIED。

## Phase 01：工程、数据库与健康检查

- 目标：指定前后端栈、安全本地部署、真实数据库健康及持久化基线。
- 实现：npm workspace；Next App Router；Spring MVC/JDBC；项目独立 MySQL；Host/Origin 防护；带项目身份/Flyway 版本的健康检查；监督进程身份校验。不是账号系统。
- 代码：`package.json`、`apps/api/pom.xml`、`apps/api/src/main/java/local/northstar/config/{DatabaseGuard,LocalAccessFilter}.java`、`health/HealthController.java`、`apps/web/src/components/HealthPanel.tsx`、`scripts/{local.py,service_runner.py}`、`infra/{compose.local.yml,mysql-init.sh}`。
- DB/API：初始化 project_identity；V001 user_setting；GET health/capabilities/settings；Flyway clean 禁用。后续权限变化不能套用最初只读账号结论。
- 覆盖：历史 Phase 01 报告记载健康/迁移保护/真实 MySQL/重启/浏览器；现有 `api-verify-resume.log` 支持健康、保护和集成套件曾成功。本次前端客户端测试通过；Mockito 健康/保护单测被环境阻塞，Python 10 项有 2 个权限 Error。
- 问题：新机器安装未重现；权限阻塞和无身份认证本地部署边界。
- 验收：**CONDITIONAL PASS**。

## Phase 02：版本化原创课与媒体

- 目标：归档参考、冻结原创 10 句、来源字段、目录/课文/音频读取。
- 实现：Demo 01，v1/v2 双版本；4 册 catalog_only；SHA-256 内容和音频验证；许可状态显示；媒体按资源 ID 读取并支持 Range。
- 代码：`content/demo-01/{active.json,v1,v2}`、`scripts/{extract-demo.py,validate-content.py}`、`apps/api/src/main/java/local/northstar/catalog/{ContentPackage,ContentSeeder,CatalogController}.java`、`docs/CONTENT_MANIFEST.md`。
- DB/API：V002 content_license/book/lesson/lesson_version/audio_asset/sentence；GET books/lessons/lessons/{id}/licenses/{id}/audio/{id}；versionId 可显式查询旧版。v2 由冻结内容包发布，不另加迁移版本。
- 覆盖：本次两版 Python 验证均退出 0（IDs、源句关系、MP3 哈希/格式/估计时长）；ContentPackageTest 两项通过；历史 CatalogIntegrationTest 在 20 项套件成功。本次 HTTP/浏览器实播 NOT VERIFIED。
- 问题：文本和声音 pending_review，releaseReady=false；包内不分发 MP3；固定 demo-01/10 句。
- 验收：**CONDITIONAL PASS**，不能公开发布素材。

## Phase 03：可恢复桌面工作台

- 目标：正式路由和组件化交互，浏览恢复、防剧透、草稿隔离。
- 实现：首页/课程/课内六 Tab/复习/报告/设置路由；224px 导航、76px 播放器及抽屉；URL 上下文与恢复点；If-Match 并发冲突。早期 localStorage 草稿后续逐步升级。
- 代码：`apps/web/src/components/{shell/AppShell,lesson/LessonWorkspace}.tsx`、`apps/web/src/lib/state/{LessonProvider.tsx,context.ts}`、`apps/api/src/main/java/local/northstar/study/StudyController.java`、`scripts/workspace-browser-smoke.js`。
- DB/API：V003 study_resume；GET/PUT study/resume、POST study/sessions；当前版本号冲突 412、缺版本 428。恢复浏览不算练习。
- 覆盖：本次 context 单测/类型/lint/build 通过；历史 StudyIntegrationTest 及新版 Phase 09 闭环包含刷新恢复和键盘焦点。历史各窗口截图未在本次逐图复核。
- 问题：浏览恢复可能防抖未落库；浏览器权限和存储关闭边界；本次 UI 与真实数据恢复 NOT VERIFIED。
- 验收：**CONDITIONAL PASS**。

## Phase 04：播放、听写、状态与证据

- 目标：逐句音频控制、非空正式听写、草稿、幂等事件及错误复习来源。
- 实现：AudioController 的顺播/循环/速度/句内 A–B；v2 词边界；听写对照；IndexedDB/outbox 与服务端草稿 CAS；开始/暂停/跳过和真实作答分离，答错也产生真实练习证据。
- 代码：`apps/web/src/lib/media/{AudioController.ts,MediaProvider.tsx,timeline.ts}`、`apps/web/src/components/exercises/DictationEditor.tsx`、`apps/web/src/lib/persistence/{db.ts,outbox.ts}`、`apps/api/src/main/java/local/northstar/exercise/{ExerciseController,TokenAligner}.java`、`scripts/dictation*-browser-smoke.js`。
- DB/API：V004 exercise/command_receipt/exercise_attempt/learning_evidence/study_event/study_stage/exercise_draft/review_item/review_source；扩展恢复播放位置；attempts、study/events、stages、drafts、reviews/items。
- 覆盖：本次 media/timeline 与 TokenAligner 单测通过；历史 ExerciseIntegrationTest 成功；今天历史完整闭环验证错误听写/同 event 重放/实播。跳过专项历史报告有记录，本次不重复写入验证。
- 问题：audioPlayed/answerExposed 是客户端观察，不是防作弊测量；A–B 非采样级；无整课共享音频和波形；跨浏览器/后台节流未测。
- 验收：**CONDITIONAL PASS**。

## Phase 05：词汇、阅读及知识点

- 目标：语境词汇、收藏、阅读作答与证据句回溯。
- 实现：5 个词语块定位源句；收藏不算掌握；版本化阅读题/选项；正式判题、历史保留、错答复习来源。
- 代码：`apps/web/src/components/exercises/{VocabularyPanel,ReadingQuestion}.tsx`、`apps/web/src/lib/api/reading.ts`、`apps/api/src/main/java/local/northstar/exercise/ExerciseController.java`、`scripts/reading-browser-smoke.js`。
- DB/API：V005 knowledge_point/vocabulary_favorite/reading_question/reading_option/reading_answer/reading_progress；扩展 exercise；GET reading、PUT knowledge/{id}/favorite、POST reading/{id}/attempts/events。
- 覆盖：历史 ReadingIntegrationTest 在套件通过；今天历史完整闭环验证错答与返回第 6 句。本次仅前端公共逻辑测试及构建，不把它当阅读业务覆盖。
- 问题：未提交阅读选项仅页面内保留，不是服务端草稿；跨课知识点复用未实现。
- 验收：**CONDITIONAL PASS**。

## Phase 06：录音回放和写作版本

- 目标：真实录音、回放/人工自评、可恢复写作与不可变版本。
- 实现：MediaRecorder 捕获/轨道释放；上传失败 Blob 在 IndexedDB 缓冲；回听满 250ms 的客户端观察；删除墓碑；写作草稿 CAS 与版本递增；规则提示，无 ASR/AI 评分。
- 代码：`apps/web/src/lib/media/recorder.ts`、`apps/web/src/components/exercises/{RecorderPanel,WritingEditor,RevisionHistory,RevisionDiff}.tsx`、`apps/api/src/main/java/local/northstar/practice/{RecordingController,WritingController,PracticeCommands}.java`。
- DB/API：V006 writing_task/writing_source/writing_draft/writing_revision/personal_recording/practice_progress/recording_observation；learning_evidence 扩展；recordings、audio、playbacks、ratings、delete、writing/draft/revisions、practice/events。
- 覆盖：本次 recorder 单测通过；历史 PracticeIntegrationTest 成功；今天历史闭环保存两个作文版本，边界日志有虚拟麦克风/权限路径，不能等同物理设备验收。
- 问题：录音文件未加密，与 SQL 非原子；端上回放证据不是服务端语音评测；真实 Chrome/Safari 麦克风未测。
- 验收：**CONDITIONAL PASS**。

## Phase 07：测验与到期复习

- 目标：完整交卷、错题回流、显式翻卡、自评及可追溯调度。
- 实现：固定 3 题测验，不可变轮次；错题按知识点形成卡；simple_v1 调度（again 1 分钟，good 递增天数）；CAS 防过期提交、eventId 幂等。
- 代码：`apps/api/src/main/java/local/northstar/exercise/{QuizReviewController,SimpleScheduler}.java`、`apps/web/src/components/exercises/QuizPanel.tsx`、`apps/web/src/components/review/ReviewQueue.tsx`、`scripts/quiz-review-browser-smoke.js`。
- DB/API：V007 quiz_question/quiz_run/quiz_answer/quiz_progress/review_result，review_item 调度/知识点/版本列，迁移已有 review_source；quiz/attempts/events、reviews/due、reviews/{id}/answer/results。
- 覆盖：本次 SimpleScheduler 单测通过；历史 QuizReviewIntegrationTest 成功，今天历史闭环验证错答→翻卡→人工自评→未来计划。
- 问题：固定 3 题渗透 SQL、DTO、UI、报表；自评不等于客观记忆能力；历史兼容和迁移本次未运行。
- 验收：**CONDITIONAL PASS**。

## Phase 08：真实报告、设置与备份

- 目标：真实行为统计、偏好、导出预检及不覆盖现库的恢复。
- 实现：事务汇总提交数/分母/证据；六步当前状态和累计证据分列；偏好 CAS；逻辑 JSON 快照、只读预检；SQL+私人媒体恢复到新时间戳库。
- 代码：`apps/api/src/main/java/local/northstar/report/ReportController.java`、`exportimport/ExportController.java`、`apps/web/src/components/{LearningReport,SettingsPanel,DataTransferPanel}.tsx`、`scripts/{data-transfer.py,backup.sh,restore.sh}`。
- DB/API：V008 user_setting.recording_enabled；GET reports、PUT settings、GET data/export、POST data/import-preview。预检不是导入 API；恢复在本地 CLI。
- 覆盖：本次 Python 快照格式/SQL 值单测通过；历史 ReportExportIntegrationTest 成功；Phase 08 报告记载 37 表逐值/媒体哈希/续学/重启，但本次没有重新恢复，包内不含私人快照。
- 问题：全表内存导出与报告无分页；只接受同内容/结构基线恢复；V008 历史人工补迁移登记需独立复核，见 KNOWN_ISSUES。
- 验收：**CONDITIONAL PASS**。

## Phase 09：最终回归与发布门禁

- 目标：完整闭环/故障回归、启动复现、全量恢复与安全发布。
- 实现：隔离 runtime 管理、学习闭环和边界脚本、独立恢复 MySQL、发布安全检查及清单。多数仍未提交。
- 代码：`scripts/{regression-runtime.py,full-learning-loop.js,release-boundaries.js,release-browser.sh,recovery_mysql.py,release-safety.py,check-snapshot.py}`、`infra/compose.recovery.yml`、`docs/{RELEASE_CHECKLIST,TEST_REPORT}.md`。
- DB/API：未新增 V009，也未发现 Phase 09 新业务路由；属于运行/测试工程化，恢复工具可新建并写入隔离库，本次不运行。
- 覆盖：本次前端 25 单测、build/typecheck/lint、Java 6 纯单测/编译成功；历史当天 MySQL 20 项全通过及两个浏览器最终成功日志。也保留浏览器前序失败、release-safety初次Build assets missing、重复启动初次构建失败；后续安全/重复启动/恢复成功日志另列，不隐去失败。
- 问题：旧报告 BLOCKED 与今天部分成功日志未统一；审计期间继续产生恢复、重访、安全、重复初始化成功日志（见TEST_EVIDENCE），但不是本次重跑，原退出码未知；脚本有并行漂移，实体麦克风/另一台新机复现未验；本机权限重试被自动审批拒绝。
- 验收：**NOT VERIFIED**。不能由两份 E2E 成功日志签发完整通过。
