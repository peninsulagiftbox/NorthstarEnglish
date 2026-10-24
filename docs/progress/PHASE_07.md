# Phase 07｜课时测验、错题复习与简化调度

日期：2026-10-24（Asia/Shanghai）。用户明确要求“现在开始实施第七阶段，先看下这个阶段的提示词，再进行实施”，随后要求继续收尾。本阶段已完成，等待审核；不进入 Phase 08，不提交或推送 Git。

## 1. 输入与范围

已核对根 `AGENTS.md`、`docs/IMPLEMENTATION_PLAN.md`、`Northstar_English_Codex/prompts/07_PHASE.md`、最近的 `PHASE_06.md`，以及根 `references/phase1/Northstar_English_Phase1_桌面Web详细设计与验收.md` 的 P08/P09、AC11/12 与闭环要求。初始 Git 工作区干净。执行期间出现另一项正在进行的听写/录音 UI 与第六阶段报告改动，本轮保留，不将这些产品改动归为 Phase 07 成果，也未覆盖其主 Web 进程。

只实现测验轮次、错误来源、翻卡、人工自评和简化调度。报告汇总、导出备份产品、账号、云服务、AI/ASR/专业语音评测仍不在本阶段范围。

## 2. 改动文件与设计

- `apps/api/src/main/resources/db/migration/V007__quiz_runs_and_review_results.sql`：新增 quiz_question、quiz_run、quiz_answer、quiz_progress、review_result；扩展既有 review_item 的目标、错误类型、知识点、due_at、reps、row_version、scheduler_version。唯一键为本机 owner + 内容版本 + 确定目标键 + card_kind；同一句的 beside 与 please 句型可有独立卡片。保留听写卡原ID，将既有阅读来源迁到对应知识点的阅读卡；不丢弃真实 source/attempt。只追加迁移，不改已执行 V001–V006。
- `apps/api/src/main/java/local/northstar/catalog/ContentSeeder.java`：把冻结 v1/v2 内容包中原有三题、选项、答案及解释播种到数据库，并校验题目JSON与原版本一致。增加第6句 please + verb 的本地知识点，来源是本课原句/原题解析；未改冻结包、hash、音频或授权状态。精读仍只展示原有5个词条。
- `exercise/QuizReviewController.java`：完整3题同事务交卷；保存不可变轮次、逐题 attempt/选择/正确性/来源/时间及 learning_evidence。parent eventId 在 quiz_run，逐题 child eventId 由 parent + exerciseId 稳定派生。错答创建/更新同卡并追加真实来源；重做用新事件保留历史。错题重新激活时增加卡版本、重置连续自评次数，避免旧页面覆盖新错误。
- `exercise/ExerciseController.java`：复用原命令回执事务实现；听写/阅读错误接入新的卡片目标、版本保护，旧来源查询兼容知识点字段。既有听写、阅读 API 保持兼容。
- `exercise/SimpleScheduler.java`：simple_v1 使用服务器 UTC 时间；again = 60 秒并重置成功次数，good 按连续自评成功次数安排1、2、4、8、16、32天，上限32天。review_result 只追加，origin=self_rating；不把人工自评写成客观掌握或专业算法结果。
- 自评命令先查原回执，再锁定卡行验证 rowVersion、上下文与到期状态。相同事件重试不会重复推进时间；旧版本/未到期卡拒绝计数。运行账号仅有新历史表INSERT权限，无改写历史权限。
- `apps/web/src/components/exercises/QuizPanel.tsx`：真实三题、五种当前状态、选项即时本机草稿、完整交卷结果、首次/重做历史、对应源句/错误轮次入口。选择先即时反映UI，在本机保存失败时回退；存储期间同步锁防止交卷越过草稿。草稿与正式提交分离，成功交卷不覆盖旧轮次；没有选项/只有跳过不会产生练习证据。
- `apps/web/src/components/review/ReviewQueue.tsx`、`app/review/page.tsx`：真实到期/全部计划、翻卡、自评、来源与历史、重新加载及真实空态。翻卡前不返回/渲染完整英文答案或错误原答；显式翻卡后才单独获取。元数据使用知识点ID而非英文词义，避免通过来源说明泄漏答案。
- 队列读取全量无答案元信息，再保留到期卡或有本机待确认命令的卡：自评已入库但回执丢失时，刷新仍可找回原操作，即使该卡已被推迟。未知回执沿用原UUID；明确409冲突后可重新读取最新卡，不把拒绝操作计入历史。
- `components/lesson/LessonWorkspace.tsx`：替换测验占位；`lib/state/LessonProvider.tsx`：URL规范化时保留合法的来源 attempt 参数，测验历史可展开并标识对应错误轮次。手动切换学习上下文仍沿用原有恢复点机制。
- `apps/web/src/app/globals.css`：沿用既有颜色、按钮、选项和卡片变量，补充测验题组、反馈、来源轮次与复习卡间距，保留桌面侧栏/助教/固定播放器。
- 新增后端 `SimpleSchedulerTest.java`、`QuizReviewIntegrationTest.java`，新增 `scripts/quiz-review-browser-smoke.{js,sh}`。定向更新 `dictation-browser-smoke.js`、`reading-browser-smoke.js`、`player-recovery-browser-smoke.js`，使回归在翻卡后检查原答、读取独立练习次数，并以真实服务端草稿替代已被既有UI改动移除的状态文案/瞬时响应。
- `scripts/grant-study.py` 追加 V007 最小权限；`HealthController.java` / `scripts/api-smoke.py` 能力阶段更新为07；更新 README、实施计划、OpenAPI、设计偏差及本报告。无新依赖、锁文件或全局运行时改动。

### 时间与草稿边界

提示词默认“浏览器本地时区展示”；遵循用户此前确认的项目偏好，继续使用 `formatBeijingTime`，明确标注北京时间，数据库及接口保存UTC。无偏移的MySQL DATETIME按UTC解释；带Z的时间不重复追加。Clock单测覆盖跨年/午夜与纽约DST，不将UTC间隔冒充本地日历天边界。

测验选项草稿仅存当前浏览器IndexedDB，不提供跨浏览器草稿同步；正式轮次/逐题作答、来源、自评与调度存MySQL。这里不声称浏览、播放、收藏或人工“记住了”等于独立能力测量。测验保留工作台原句/助教入口，属于可回看资料的本课理解练习。

## 3. 实际验证与证据

证据根目录 `docs/evidence/phase-07/`，沿用既有Git忽略规则。实际项目级Node22.23.2、Java21.0.12.1，见 `logs/runtime-versions.log`。隔离测试使用本项目现有 `northstar_phase01_test`，API8086 / Web3101；主实例仍为 API8085 / Web3100 / MySQL3308。未删除/重建数据库、容器或卷。

| 检查 | 实际结果与日志 |
| --- | --- |
| 前端类型/lint | `python3 scripts/local.py exec npm run typecheck`、`npm run lint` 通过；`logs/typecheck-release.log`、`lint-release.log`。生产构建也执行TypeScript检查 |
| 前端单测 | `python3 scripts/local.py exec npm test`：23项通过，0失败/跳过；`logs/web-tests.log` |
| 生产构建 | 在 `.local/phase07-web/` 隔离源码快照执行 `API_PORT=8086 WEB_PORT=3101 npm --prefix .local/phase07-web run build`，Next webpack生产构建通过；`logs/build-workspace-final.log`。隔离构建避免覆盖其他进行中的主Web工作；最终快照包含工作区当时已有听写修改 |
| Java/MySQL | `python3 scripts/local.py exec env NORTHSTAR_DB_TEST=1 DB_NAME=northstar_phase01_test apps/api/mvnw -f apps/api/pom.xml verify`：19项，0失败/错误/跳过，生产打包成功；`logs/api-verify-release.log` |
| 新增后端覆盖 | 3题/选项上下文、原子回滚、并发相同交卷、同event异payload拒绝、三条逐题证据、重做保留、同句不同点独立卡、自评翻卡条件、过期rowVersion拒绝、60秒/1天、历史只追加权限、Flyway重复迁移0、真实应用关闭/重启后轮次/调度保留；Clock单测覆盖DST/午夜/跨年与32天上限 |
| 第七阶段Playwright | 真实错答第6句关联题、知识点卡/来源、草稿刷新、交卷与自评服务端已接受后丢回执、刷新原事件重试、正确重做、跳过不计轮次、翻卡前无英文答案、1分钟调度、未来卡不可提前自评、原句与具体错误轮次跳转、旧卡版本409、1440/375无横向溢出。`logs/browser-workspace-final.log` 为最终结果；空队列/503展示为明确GET故障注入，不冒充数据库故障实测 |
| 听写/阅读回归 | `logs/regression-pass.log` 中两套均 passed=true、pageErrors=[]；含10个真实MP3、速度/seek/AB、草稿刷新、错误原答、跳过/暂停不增计数、丢回执重放、5词定位/收藏/阅读错误来源及盲听保护 |
| 播放器恢复扩展回归 | `logs/player-regression-final.log` passed=true、pageErrors=[]；含恢复暂停、快速换句、快捷键、自然ended循环、离线保留草稿、两页CAS冲突保留双方、存储禁用仍保留原文 |
| 服务重启 | 停止并重启本轮独立API/Web，逐项比较dueAt/rowVersion/reps/来源/自评历史以及8轮测验，完全一致；`logs/restart.log`。重启后的浏览器再次验证到期时间和返回第6句；`logs/restart-browser-final.log` |
| 本地脚本 | `python3 -m unittest discover -s scripts/tests`：8项通过；`logs/script-tests-authorized.log`。临时env仅由单测写入其测试目录，没有替换项目.env |
| API安全/主站只读交付 | `python3 scripts/local.py exec python3 scripts/api-smoke.py` PASS：真实DB/阶段07、缓存头、404/405/403与Host/Origin约束；`logs/api-smoke-main.log`。主站浏览器验证V007、3题/9选项/主库0轮假测验、1440/375布局，pageErrors=[]；`logs/production-browser.log`。所有主站浏览器写请求都设为拦截，实际本轮捕获0次；未播放私人录音或执行主库业务作答 |
| OpenAPI/空白 | Ruby YAML解析34条路径；`git diff --check`通过 |

主Web在本轮收尾时已有晚于相关源码的生产构建（与本轮其他工作并行完成，API转发核对为8085），因此保留其监督PID，不重复覆盖/重启；通过主站只读浏览器核实实际页面确已包含本阶段测验/复习。不会把其他任务的生产构建命令算作本轮重跑结果。

## 4. 主库保护与运行状态

1. 核验主API监督PID/cwd后仅停止该API；本项目MySQL容器身份、回环端口、原卷均核对通过。主Web及其他项目服务保留。
2. 主库迁移前32表原列hash快照：`.local/phase07-main-before.json`；0600 SQL备份 `.local/backups/phase07-main-before.sql.gz`，25,342字节。该备份不是录音二进制备份，未宣称媒体已备份。
3. 主库成功V006→V007；重新授予新表的最小写权限。迁移后即刻32表比较，只有计划中的 exercise/knowledge_point 新增目标、review_item扩展与review_source换卡发生变化；原exercise/knowledge行按原ID投影hash不变，review_source除item_id之外的原始attempt/上下文保持一致。其余原表hash一致。见 `logs/main-before.log`、`main-after.log`。
4. 交付后复核发现 `study_resume` 在持续运行/访问期间另有变化；保留该恢复点，未回退。`logs/main-delivery-initial.log` 保留最初严格快照断言失败；`main-delivery-final.log` 明确区分这一可变恢复点，重新核对不可变历史。不能把交付后的全部32表描述为完全未变。该次主站交付核验时4条exercise_attempt、16条learning_evidence、1条review_source，quiz_run/review_result均0；本轮写E2E只在隔离库。
5. 主API监督PID93425，主Web监督PID92537（为记录时状态，后续用户操作可能改变）。本轮隔离服务和测试浏览器在最终核验后关闭；不停止主MySQL，不执行down -v/rm/prune，不碰其他项目。

## 5. 失败、修正与未测边界

- 初始沙箱拒绝Docker/数据库访问、进程检查、回环端口和Mockito自附加；保留 `migrate-test.log`、`api-tests-initial.log`、`script-tests.log`，获准在本机环境运行后对应测试均通过。不将环境阻塞计为通过。
- 首轮真实MySQL测试暴露DATETIME在queryForMap中返回LocalDateTime，不能直接强转Timestamp；补充明确UTC转换后19项全通过。见 `api-tests-authorized.log` 与最终verify日志。
- 首轮浏览器发现异步IndexedDB保存使受控radio点击短暂回弹；改为即时选择、保存失败回退，仍保留同步锁防止提交越过保存。
- 错误来源attempt参数被工作台既有URL规范化丢弃；定向保留合法参数后，真实链接能展开并标识对应交卷。
- 后续测试脚本失败包括未展开details就点隐藏来源、Next自带alert与业务alert选择器冲突、通用标题与测验标题重复导致严格定位歧义；修正测试操作顺序/范围后重测。原结果保留在 `logs/browser-{second,third,fourth}-result.txt`、`restart-browser-initial-result.txt`。
- 既有听写/播放器脚本依赖旧状态文案、旧计数节点或瞬时PUT响应；定向改为读取独立计数、等待实际持久化草稿和可见错误/保留输入。失败及最终回归日志均保留；没有为通过这些回归而修改无关听写产品实现。
- 未实测Safari/Firefox/真手机、系统时钟被人工修改、硬关机/磁盘损坏恢复；不声称像素级一致、完整无障碍合规或真实语言能力提高。复习自评仍是人工数据，客户端“已翻卡”也不是服务端测得的回忆能力。
- 素材/声音来源授权仍 pending_review，正式发布仍阻塞。没有接入AI/ASR，不增加模型反馈或发音评分。

## 6. 截图与人工审核

`docs/evidence/phase-07/screenshots/`：`quiz-{1440,375}.png`、`review-flipped-1440.png`、`review-scheduled-1440.png`、`review-375.png`、`review-empty-375.png`，以及 `production-quiz-{1440,375}.png`、`production-review-1440.png`。已实际查看桌面测验、调度卡、375px复习、主站1440/375测验截图。

可从主站 `http://127.0.0.1:3100/lesson/demo-01?version=demo-01-v2&tab=quiz&sentence=demo-01-v2-s06` 开始人工审核：完整答三题并故意错第2题 → `/review` 翻卡 → 选还不会 → 查看全部计划的新到期时间/来源/历史 → 返回第6句重做。此步骤会产生用户自己的真实学习数据；本轮未替用户在主库完成这次作答。

本阶段汇报后停止。Phase08需用户审核和单独授权，再做真实首页/报告汇总、设置及导出备份；不把本阶段存在的单项历史当作报告模块已完成。

### 用户追加：保存写作新版本后清空输入（2026-10-24）

用户要求“保存新版本后，清空输入”。原实现成功交卷仅刷新历史，输入与本机/服务端草稿都保留原文。本次仅修改 `apps/web/src/components/exercises/WritingEditor.tsx`：确认正式版本保存后，对仍等于本次提交快照且rowVersion未被其他页面更新的草稿执行乐观锁清空，再清理IndexedDB、输入状态与回载parent关联。刷新后仍为空，已保存版本及其内容不变。正式保存失败不清空；清空步骤失败单独提示“新版本已保存，但草稿未能完整清空”，保留当前输入，不将此错误误当成版本提交被拒绝。其他页面已写入新草稿时跳过清空。离开组件后不继续改写本机输入状态。

新增 `scripts/writing-clear-browser-smoke.js`，验证成功/失败、刷新、本机与服务端草稿清理、不可变历史、回载parent重置、清空失败及其他页面新稿保护。该浏览器测试所有写作接口都明确模拟，另2次浏览位置写请求拦截；模拟5版仅用于UI流程验证，不代表主库真实提交测试，未操作用户作文/学习数据。pageErrors=[]，375px无横向溢出。

类型检查、lint、生产构建（含TypeScript）、专项Playwright及git diff --check通过。证据 `docs/evidence/writing-clear/logs/{typecheck,lint,build,browser}.log`。未新增依赖、修改后端/SQL或重复无关Java测试。仅核对PID/cwd后重启主Web加载构建（监督PID37908），API/MySQL保留，测试浏览器关闭。Safari/Firefox未测；未提交Git、未进入下一阶段。

### 用户追加：复习说明与按钮留出间距（2026-10-24）

按截图红框，仅为 `ReviewQueue.tsx` 的顶部工具栏增加专用 `review-queue-actions` 类，在 `globals.css` 设置 `margin-top:12px`，将调度说明与按钮行分开；其他工具栏、卡片和业务逻辑不变。生产构建（含TypeScript）及git diff --check通过。只读Chromium在1440/375px实测说明底缘至按钮行顶缘均12px，无横向溢出、pageErrors=[]；所有写请求设为拦截，未改学习数据。已查看1440px截图。证据 `docs/evidence/review-spacing/logs/{build,browser,restart}.log`、`review-{1440,375}.png`，临时验证脚本在忽略的 `.local/`。仅重启本项目Web加载构建（监督PID41160），API/MySQL保留，浏览器关闭。未新增依赖或运行无关业务测试；未提交Git，保留工作区其他正在进行的改动。
