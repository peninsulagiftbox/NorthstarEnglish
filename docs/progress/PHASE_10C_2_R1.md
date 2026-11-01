# Phase 10C-2-R1 定向整改报告

日期：2026-10-31（Asia/Shanghai）。结论：**R1 PASS、R2 PASS，等待独立验收**。基线HEAD为`ff0dbe1`，开始时工作区已有上一轮补验的未提交修改；本轮保留这些改动，以开始时源码副本及SHA-256区分R1增量。未提交、未推送、未部署个人环境，未进入10D。

## 1. 范围与改动文件

| 文件 | 本轮改动 |
| --- | --- |
| `ReportController.java` | `quizFilter()`返回固定SQL片段与参数数组；逐轮查询、全部轮数计数、核验汇总复用同一过滤对象；汇总与逐轮使用统一强核验条件 |
| `QuizSets.java` | 集中提供固定别名`r`的核验SQL谓词；`verifiedRun()`从真实数据库轮次读取判定，不再仅比较调用方传入的题数 |
| `QuizReviewController.java` | 历史读取调用统一判定；正式提交、旧协议DTO、eventId/回执生成及重放流程均未变 |
| `QuizReportR1IntegrationTest.java` | 真实MySQL/API参数边界、时间边界及七类异常历史测试 |
| `phase10c2-r1-browser.js` / `phase10c2_r1_browser.py` | 隔离报告/历史页面验证、异常素材生成、旧协议重放与回执哈希检查；复用既有测验兼容脚本 |
| `.gitignore` / 本报告 | 排除本轮原始运行证据，记录整改与验证结果 |

生产改动仅上述三个Java文件。相对本轮开始时的增量见本地证据`r1-only.patch`，不是把上一轮全部未提交改动算成本轮新增。

## 2. R1：统一JDBC参数绑定

`lessonId/versionId/setId`使用绑定参数；不拼接参数值、不用手动引号转义。标识列为`ascii_bin`，以`CAST(? AS BINARY)`比较绑定值，避免Unicode参数引发MySQL排序规则冲突，同时避免把Unicode有损转换成ASCII问号。列本身不转换，标识按字节匹配。现有ASCII标识中的单引号和反斜杠可精确命中；Unicode输入可以安全查询，因现有ASCII标识域不含该值而返回空结果，不修改数据库字符集或标识规则。

`from/to`在HTTP入口解析为Instant，以`Timestamp`绑定；保持UTC、from包含/to不包含。非法时间返回422，不进入SQL执行。逐轮明细查询、全部轮次COUNT、verified的COUNT/SUM均复用同一个`QuizFilter.sql()/args()`，参数顺序一致。

真实API测试：

- 创建含单引号与反斜杠的合法课程及版本标识，通过正式提交API生成一题有效轮次；分别按课、版本、题集，以及五参数组合筛选，明细与汇总均正确命中。
- 三种标识参数各测试8个非法或非匹配值，共24例：单引号、反斜杠、组合注入形式、Unicode、非法路径式标识、空值、额外反斜杠。均按字面值返回空明细及零分母，没有扩大结果集或500/503。
- 测试from恰等于提交时刻、to恰等于提交时刻、边界前后1ms及组合筛选；两种时间参数各5个非法值，共10例，均422。

发现并修复的实际问题：旧拼接实现不能正确匹配含反斜杠的合法标识；初次直接使用`=?`绑定时，Unicode负例触发MySQL 1267排序规则冲突。使用二进制绑定比较后全部通过。

## 3. R2：统一轮次核验

历史详情、测验GET中的history、报告逐轮详情和verified汇总共用`QuizSets.verifiedRunClause()`，至少满足：

1. `total_count`在1..100内，`submitted_count=total_count`。
2. 题集存在且冻结，题集版本与run版本一致，版本所属课程与run课程一致，冻结题集哈希与run哈希一致。
3. 冻结题集成员数、run_item数、quiz_answer数均等于真实总题数。
4. run_item关联的answer、attempt、冻结成员在run/exercise/attempt/version/sentence/option身份上匹配；真实关联的不同attempt数量等于总题数。
5. 每条run_item的setId、setHash、序号及题面JSON与对应冻结成员一致；attempt属于本轮课程，所选选项存在，attempt.correct与冻结answerKey判分一致。
6. `correct_count`等于真实关联attempt的正确数量之和。

SQL谓词只读取数据，不补造证据、不修成绩、不重写回执。未核验轮次仍可出现在历史明细，verified=false、不提供报告accuracy，不进入已核验成绩的分子和分母。

隔离库异常用例均从正式API生成的正常测试轮次开始，在约束允许范围内修改测试数据，并在finally恢复：

| 异常 | 结果 |
| --- | --- |
| 题数和提交数正确，但correct_count错误 | 历史、详情和汇总均判未核验；PASS |
| run.setHash不一致 | 同上；PASS |
| run_item.setHash不一致 | 同上；PASS |
| run_item题面JSON与冻结成员不一致 | 同上；PASS |
| attempt.correct与真实选项判分不一致 | 同上；PASS |
| 缺少一条run_item | 同上；PASS |
| 额外quiz_answer及attempt未被本轮item覆盖 | 同上；PASS |

每例都检查历史GET、测验GET、报告逐轮verified标记，及verifiedRuns/unverifiedRuns/correct/total/accuracy。恢复后正常轮次重新核验通过，汇总恢复原值，原父回执payload_hash及response_json逐值不变。未关闭FK或修改迁移来制造通过。

## 4. 实际命令与结果

全部数据库测试使用UUID/容器标签核验后的专用MySQL（3334、`northstar_phase01_test`），服务8175/3195，源码/JAR/Web构建位于`.local/phase10c2/source`。准备干净隔离库会执行既有迁移链；没有重复迁移个人3308数据库。

原始命令、argv、cwd、HEAD、退出码和日志哈希由既有runner保存在`docs/handoff/evidence/phase10c2/execution-commands.jsonl`；本轮筛选记录和脱敏副本集中在`docs/handoff/evidence/phase10c2-r1/`。

| 检查 | 实际结果 / 原始日志文件名 |
| --- | --- |
| 基线复现：`mvn test -Dtest=QuizReportR1IntegrationTest` | 2项失败：引号/反斜杠合法标识未命中、错误correct_count仍verified；`r1-before-corrected-fixture-1793432409207868000.log` |
| 定向修复回归 | 2/2通过；`r1-boundary-final-1793432819886778000.log` |
| 干净隔离库全量`mvn verify` | **40项，0失败、0错误、0跳过，BUILD SUCCESS**；`r1-final-java-1793432977262630000.log`。包含Java单元、API、报告/导出、历史兼容、动态题量和原子提交回归 |
| 隔离Web生产构建 | exit=0；`web-build-c2-1793432984290157000.log` |
| 报告/历史真实浏览器 | 4组检查PASS、pageerror=0；`r1-browser-report-history-1793433277454638000.log` |
| 既有测验兼容浏览器脚本 | 5组检查PASS、pageerror=0，覆盖草稿刷新、断网重试、旧outbox原路径提交、旧草稿隔离/导入；`r1-browser-quiz-compat-1793433528230207000.log` |
| 原回执保全 | 浏览器旧协议重放前后，三条合成测试父回执原始数据库字节哈希相同；Java异常测试也逐值核对payload_hash/response_json未变 |
| 边界文件保全 | 38份既有迁移SQL与5份播放器文件SHA-256均与本轮开始时一致 |
| 个人部署只读核对 | 3100/8085均UP@011.09，JAR哈希及Web BUILD_ID与原部署一致；`r1-personal-readonly-1793433592570197000.log` |
| 语法/空白 | Python编译、JS语法、git diff --check通过 |

浏览器截图：`output/playwright/phase10c2-r1/report.png`、`history.png`。截图为隔离合成数据，不包含个人学习历史。

## 5. 失败原件与限制

保留全部初始失败日志：首次素材复制复用了受唯一约束保护的storage_key，已修正测试素材为独立路径；在隔离副本切换基线源码复现后，Maven增量class时间戳使一次回归仍加载旧类，已通过隔离`mvn clean test`重新编译；Unicode排序规则冲突属于实际缺陷，已修复并单独保留失败与成功日志。

浏览器重放检查最初错误地要求JSON对象键序相同，MySQL JSON规范化键序会导致误判；测试改为JSON内容比较，同时检查数据库原回执字节哈希。生产回执和重放实现没有为此改动。既有草稿脚本在全新会话中需先打开正式测验页初始化IndexedDB，该测试前置已补齐，原脚本未改写。

前端业务源码本轮未修改；不把Web构建或浏览器检查表述为重新做过播放器声学、麦克风或真实设备验收。本轮修复只在隔离候选验证，尚未覆盖个人运行版本。

## 6. 交付与停止点

脱敏证据包：`output/review/phase10c2-r1-sanitized-evidence.zip`。包含本报告、三个完整修复Java文件、相对本轮基线的补丁、测试源码、原始命令/退出码的脱敏副本、失败/成功日志、截图、SHA-256清单及独立校验器。个人数据库备份、凭据、个人原回执正文及个人录音不纳入；原始命令和日志仍完整保存在本地，脱敏副本另列原始/分享版哈希。

本轮已停止隔离服务，保留证据及测试数据。不提交GitHub、不部署个人环境、不进入10D，等待独立验收。
