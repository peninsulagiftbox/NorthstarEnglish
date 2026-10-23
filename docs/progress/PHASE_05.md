# Phase 05｜精读词汇、阅读理解与证据定位

日期：2026-10-23（Asia/Shanghai）。用户明确授权“现在开始实施第五阶段，先看下这个阶段的提示词，再进行实施”。已核对根 AGENTS、实施计划、`Northstar_English_Codex/prompts/05_PHASE.md`、Phase 04 最新报告及根参考归档的 P05 / AC07–08；开始时 Git 工作区干净。

**结论：本地功能验收 PASS_WITH_NOTES，等待本阶段审核；素材正式发布仍为 BLOCKED。** 未进入 Phase 06–09，未提交、推送 Git 或公开发布。

## 1. 改动文件与设计决定

- `apps/api/src/main/resources/db/migration/V005__knowledge_points_and_exercise_links.sql`：增加版本化知识点、独立收藏、阅读题与选项、不可变答案关联、当前阅读轮状态；扩展原 exercise 类型约束。所有学习对象通过课/版本/源句外键绑定，不删除或改写旧听写数据。
- `apps/api/src/main/java/local/northstar/catalog/ContentSeeder.java`：从已有冻结 v1/v2 内容包读取各 5 个词条和 1 道阅读题，在同一播种事务建立关系并核对数据。语境用法说明存入后端知识点；不改包、音频和 hash，不虚构音标或专业词典数据。
- `apps/api/src/main/java/local/northstar/exercise/ExerciseController.java`：增加 `/reading`、`/knowledge/{id}/favorite`、`/reading/{id}/attempts`、`/reading/{id}/events`。服务端验证题目/选项/课次/版本，按稳定选项 ID 判题；共享 command_receipt 的并发幂等事务和 exercise_attempt / learning_evidence。阅读选项及知识点、证据句、内容版本、规则版本可追溯。
- 阅读答错以 `reading_evidence_mismatch` 追加 review_source；答对同样保留真实 attempt/evidence。与听写共用同版本源句卡，分别保留多次错误来源；阅读不修改听写逐句 study_stage。
- `apps/web/src/lib/api/reading.ts`、`components/exercises/{VocabularyPanel,ReadingQuestion}.tsx`、`components/lesson/EvidenceLink.tsx`：API 词卡、语境义/用法/示例、源句高亮、右栏同步、独立收藏、阅读选项/反馈/历史、开始/暂停/跳过及正式提交。错答自动聚焦第 6 句并展示证据，显式入口可跳完整课文，选中原句且不自动播放。
- `components/lesson/LessonWorkspace.tsx`、`app/globals.css`：替换精读占位、定向文案、词卡和阅读反馈样式、完整课文定位滚动；保留现有桌面布局与底部播放器。隐藏英文时不挂载精读内容，提供显示英文入口。
- `components/exercises/ReviewSources.tsx`：区分阅读选择和听写原文，显示阅读知识点/选项来源，回到对应任务重练。
- 复用既有 IndexedDB outbox：正式阅读提交先持久化 UUID，网络响应丢失后刷新可重试原事件；失败不假报保存。提交期间离开 Tab 时，迟到回执仍可确认既有作答，但不抢回页面上下文。
- `scripts/grant-study.py`：V005 后仅追加 reading_answer INSERT、favorite/progress INSERT/UPDATE；运行账号不能改写已提交答案或内容。
- 新增 `ReadingIntegrationTest.java`、`scripts/reading-browser-smoke.{js,sh}`；更新 README、实施计划、OpenAPI 0.5.0、依赖说明、设计偏差和本报告。无新依赖，无锁文件或全局 Node/Java 变化。

### 学习真实性与数据边界

收藏不等于掌握，浏览/词卡点击/播放均不生成 evidence。首次选择答案记录 in_progress；正式作答回执才产生 practiced，答错也属于真实练习。当前轮暂停/跳过与累计作答历史分开，后续跳过不抹掉历史。首答与重做在历史中分列，不计算能力分或虚构掌握率。

标准答案只在服务端题目快照及已提交反馈中给出；首次答题 UI 不指明正确选项。自学场景允许浏览原句与语境义，不宣称防作弊或独立测量。未正式提交的选项只留当前页面，不伪装为服务端草稿；已持久化的待提交命令可刷新恢复。收藏失败后要求重新读取确认状态，避免不确定响应下反复切换。

## 2. 实际运行与验证

证据目录：`docs/evidence/phase-05/`（沿用 Git 忽略规则，未公开发布机器信息或素材）。

| 检查 | 实际结果 / 日志 |
| --- | --- |
| 环境与项目身份 | Node22.23.2、npm10.9.8、Java21.0.12.1、专属 MySQL8.4；3100/8085 开始为空闲，3308 为本项目既有实例；`logs/doctor.log` |
| 类型检查、lint、生产构建 | PASS；`python3 scripts/local.py exec npm run typecheck` / `lint` / `build`；最终 `typecheck-delivery.log`、`lint-delivery.log`、`build-delivery.log` |
| 前端既有单测 | `python3 scripts/local.py exec npm test`，19 项全部通过、0 失败/跳过；`logs/web-tests.log` |
| Java21 + 真实 MySQL 集成 | `python3 scripts/local.py db-test`，16 项全部通过、0 失败/错误/跳过；`logs/api-db-release.log`。含新增阅读并发重复事件、改 payload 409、跨课/跨版本/选项 422、事务回滚、正误作答证据、收藏不产生作答、暂停/跳过保留历史、只追加权限、重复播种/迁移 |
| 阅读 Playwright | `python3 scripts/local.py exec sh scripts/reading-browser-smoke.sh`，passed=true、pageErrors=[]；`logs/browser-delivery.log`。覆盖 5 词原句/高亮/助教、收藏刷新、真实错答→第6句→复习来源、正确重做、回执丢失后刷新原事件重放、离开 Tab 的迟到回执保护、暂停/跳过、历史、隐藏英文、错误重试/空状态、1440/1280/979/375 无横向溢出与底栏位置。错误/空状态使用明确 API 故障注入；其他作答连接真实隔离库 |
| 既有听写与恢复回归 | `python3 scripts/local.py exec sh scripts/dictation-browser-smoke.sh`，核心/恢复两个套件均 passed=true、pageErrors=[]；`logs/dictation-regression.log`。真实十音频、倍速/A–B、差异、草稿、幂等与多页恢复保留 |
| 脚本单测 | `python3 -m unittest discover -s scripts/tests`，8 项通过；`logs/script-tests.log` |
| API 健康与安全 | `python3 scripts/local.py exec python3 scripts/api-smoke.py` PASS；健康/实际数据库、no-store、404/405、Host/Origin403、无通配 CORS；`logs/api-smoke.log` |
| 主库升级与历史保护 | 迁移前 `.local/backups/phase05-main-before.sql.gz`；V004→V005。19 张旧表逐表哈希不变（exercise 比较原 dictation 行，Flyway 比较旧迁移行）；`logs/main-before.log`、`main-after.log`。两版本共10知识点/2阅读题/6选项；主库 reading_answer/favorite/progress/attempt/evidence/review_source 均0，隔离 E2E 未混入主库 |
| 主库 E2E 防护与最终实例 | `logs/main-guard.log` 显示脚本在打开浏览器前拒绝主库；`logs/production.log` 确认最终页面为主库、5词/题目可见、pageErrors=[]。最终 API/Web 监督进程 PID 为67446/67496；19张旧表再核验通过，主库无新增学习记录 |
| OpenAPI 与空白检查 | Ruby YAML 解析19个路径；`logs/openapi.log`；`git diff --check` PASS |

## 3. 过程失败与修正

1. 普通沙箱的 Docker socket 不可访问、Mockito 自附加失败：初次 `api-unit.log` 有6项环境错误、4项DB测试跳过，不能算通过。获准环境后实际连接隔离 MySQL 的16项全部通过。
2. 脚本测试在普通沙箱首次因 ps/回环端口权限出现2项环境错误，保留 `script-tests-initial.log`；获准环境8项全部通过。
3. 新增集成测试发现 MySQL `COALESCE` 返回数字，收藏 API 未满足 boolean 类型；已在服务端规范为布尔并复验。失败保留 `api-db-final.log`，通过为 `api-db-release.log`。
4. 浏览器初次文本定位 bench 同时命中 beside 示例，改为词条精确匹配；随后补 React 更新等待和高亮文本的 textContent 比较，避免把 DOM 时序误报为产品失败。`browser-initial.log` / `browser-second.log` 保留；最终完整用例通过。
5. 主库快照初次遇到二进制列解码失败，改用明确 utf8mb4 与 binary-as-hex 读取后完成备份/哈希；没有执行删除或改写数据。
6. 收尾补上阅读提交期间离开 Tab 的迟到回执保护，并用服务端真实接受后延迟回包的场景定向验收；最终构建已含该保护。

## 4. 验收、截图与限制

| 本阶段条目 | 结果 |
| --- | --- |
| 5 个原型词条含实际源句、语境义、用法说明、示例；收藏独立 | PASS |
| 点词卡高亮原句并更新右侧上下文，数据来自 API | PASS |
| 固定阅读问题/正确选项，第6句证据；对错均保存真实记录 | PASS |
| 题目/选项/证据/知识点/课与版本关联；错答追加复习来源 | PASS |
| 浏览/收藏/跳过不产生练习完成；刷新收藏和历史、幂等重试 | PASS |
| 跨课/版本明确拒绝；实际 MySQL、编译、浏览器闭环 | PASS |

截图在 `docs/evidence/phase-05/screenshots/`：`vocabulary-1440.png`、`beside-source-1440.png`、`wrong-evidence-1440.png`、`history-1440.png`、`review-source-1440.png`、`vocabulary-{1280,979,375}.png`、`reading-375.png`、`reading-error-375.png`。已实际查看桌面词卡、beside 原句高亮、错答反馈和375px阅读布局；不声称像素级一致、真实触控或完整无障碍合规。最终本地主库只读浏览器为 Chromium 155.0.8059.85，确认5词/真实题目、pageErrors=[]；预设拦截所有写请求，本次实际触发0次，随后19张旧表哈希仍一致。

未测真实 Safari/Firefox、屏幕阅读器、真实触控设备；本阶段无 AI/ASR/发音评测。收藏不自动进入错误来源列表，不提供“已掌握”能力判定；复习翻卡/调度留 Phase07。原始素材/声音正式发布授权仍待审查，只限已授权本地功能测试。

## 5. 本地交付与下一阶段

本项目 Web/API/MySQL 以回环地址保留运行，精读入口 `http://127.0.0.1:3100/lesson/demo-01?tab=vocabulary&english=1`。测试浏览器与本轮测试 API/Web 已停止，正式实例连接主学习库；PID/cwd与最终复核见 `logs/runtime-delivery.log`、`logs/production.log`、`logs/main-delivery.log`。可使用既有 `sh scripts/dev-down.sh` 停止本项目，不删除数据或卷。

下一步须用户审核 Phase05 后才可授权 Phase06（录音持久化与写作版本）。本阶段汇报后停止，不自动进入后续阶段或提交 Git。

### 用户追加：听写播放行与草稿标题间距（2026-10-23）

截图红框中播放/状态行紧贴“本句听写草稿”标题，原 `.dictation-playback` 没有底部外边距。本次仅在 `apps/web/src/app/globals.css` 给该局部类添加 `margin-bottom:16px`，不改变状态标签居中或其他 toolbar。

lint、生产构建、git diff --check 通过。真实 Chromium 在1440/375px实测播放行底部到草稿标题顶部均为16px、无横向溢出、pageErrors=[]；已查看桌面截图。证据在 `docs/evidence/dictation-spacing/`：`spacing-{1440,375}.png` 与 `logs/{lint,build,browser}.log`。验证拦截所有写请求，未提交练习；纯间距修改未重复业务测试。

已仅更新本项目主 Web（监督进程PID68881），API/MySQL保持运行；未改学习数据、提交Git或进入下一阶段。Safari/Firefox本次未测。

### 用户追加：听写跳过后进入下一句（2026-10-23）

根因：`DictationEditor.tsx` 收到 skip 回执后只刷新本句状态，没有更新工作台目标句。本次在确认 skipped 回执后暂停旧音频、加载下一句（不自动播放），更新选句并进入下一句听写；保留原句草稿、累计练习与历史。最后一句不回绕，明确提示补练或切换精读。失败或不确定回执不跳转，重试原事件成功后才前进；离开原句后的迟到回执沿用已有 active 防护，不抢回手动选择。无需后端、数据库迁移或依赖修改。

修改 `apps/web/src/components/exercises/DictationEditor.tsx`；新增 `scripts/dictation-skip-browser-smoke.js`；既有 `scripts/dictation-browser-smoke.js` 的跳过断言调整为先验证选中下一句，再回原句核对 skipped 与累计次数。README 补充行为说明。

验证：typecheck、lint、生产构建、19项前端单测和 git diff --check通过；日志在 `docs/evidence/dictation-skip/logs/`。新增真实Chromium专项passed=true、pageErrors=[]，覆盖原句skip入库→下一句、旧音频暂停/新句不自动播、原句草稿保留、503不跳、服务端接受后丢回执/刷新/原eventId重试、迟到回执不改手动目标、暂停不跳、最后一句不回绕；所有句子练习次数和错误复习来源数均未增加。后端沿用既有实现，本轮未重复Java测试或整套听写/恢复回归。

浏览器从about:blank#8086起步，先验证8086实际连接隔离测试库，再将全部 `/api/v1/**` 请求转发到该实例，未向主API写入测试数据。已实际查看 `next-sentence-1440.png`，另存 `last-sentence-1440.png`。本轮未测Safari/Firefox或窄屏交互。

主Web已更新（监督进程PID70339）；主API/MySQL保持运行，专项测试API PID70004及测试浏览器已关闭。未提交Git或进入后续阶段。

### 用户追加：词卡内容与收藏按钮间距（2026-10-23）

原 `.vocabulary-select` 用内部12px padding充当间距，hover背景延伸到按钮旁，内容区边界与收藏按钮贴在一起。仅修改 `apps/web/src/app/globals.css`：词卡使用纵向flex与16px gap，内容按钮移除底部伪间距；收藏按钮保持内容宽度，不被拉满。

lint、生产构建、git diff --check通过；真实Chromium在1440/375px的默认/hover状态，实测全部5张卡的内容区到收藏按钮间隔均16px，无横向溢出、pageErrors=[]。已查看桌面hover截图。证据 `docs/evidence/vocabulary-spacing/card-{default,hover}-{1440,375}.png`、`logs/{lint,build,browser}.log`。浏览器拦截所有写请求，未操作收藏或练习提交；纯样式改动不重复业务测试。

本项目主Web已更新（监督进程PID71931），主API/MySQL保持运行；未提交Git。Safari/Firefox本次未测。

### 用户追加：收藏移至词卡右上角（2026-10-23）

用户要求节省卡片纵向空间。本次修改 `VocabularyPanel.tsx` 与 `globals.css`：收藏按钮改为右上角32px星标，与词语同排；空心/实心星和背景区分收藏状态，保留 `aria-label`、`aria-pressed`、title与键盘操作。词语预留44px右侧空间，长词组可换行；释义、示例等仍使用完整卡片宽度。两个按钮保持兄弟关系，避免嵌套按钮或收藏误触选句。此布局取代上一节底部16px间隔方案。

typecheck、lint、生产构建、git diff --check通过；真实Chromium验证1440/375/320px的全部5张卡：星标与词语顶部对齐、文字至少保留10px间隙、无横向溢出，实测卡高166px；Enter切换收藏状态且不改变选句，pageErrors=[]。收藏响应明确由浏览器模拟，所有其他写请求拦截，未修改主库，不将此项描述为本轮真实持久化验证。纯布局/图标变化未重复业务单测。

证据 `docs/evidence/vocabulary-compact/`：`card-{1440,375,320}.png`、`workspace-1440.png`、`logs/{typecheck,lint,build,browser-final}.log`。已查看桌面和320px卡片截图；留图时将词卡滚至视口中央，避免固定播放器遮挡元素截图。主Web已更新（监督进程PID72978）；主API/MySQL保持运行，未提交Git。Safari/Firefox与真实触控设备本次未测。

### 用户追加：修正词卡内层背景色（2026-10-23）

截图中的不协调浅绿色块来自全局 button:hover 规则作用于 `.vocabulary-select`，形成卡片内部的第二层底色。仅修改 `apps/web/src/app/globals.css`：内容按钮在默认/hover/active均透明；整张卡默认白色、未选中hover浅灰#f3f5f7、选中整卡淡绿#e0f1eb，hover不覆盖选中状态。收藏按钮保持独立状态，已收藏hover维持本色。

lint、生产构建、git diff --check通过。真实Chromium在1440/375px验证default/hover/pressed/selected/selected-hover/favorite-hover：内层始终透明，外卡颜色符合上述规则，无横向溢出、pageErrors=[]。已查看桌面hover截图，整卡统一灰底，不再出现内嵌色块。证据 `docs/evidence/vocabulary-background/`，包括各状态截图及 `logs/{lint,build,browser}.log`；拦截全部写请求，未改主库学习记录。纯样式变化未重复业务测试。

主Web已更新（监督进程PID74455），API/MySQL保持运行，测试浏览器已关闭。未提交Git；Safari/Firefox本次未测。

### 用户追加：明确单句语境与全文入口文案（2026-10-23）

用户确认修改设计说明中建议的文案。`components/lesson/EvidenceLink.tsx` 将“查看课文第X句”改为“在全文中查看上下文 →”；`components/exercises/VocabularyPanel.tsx` 将区块标题改为“当前句语境 · 第X句”，与下方阅读题的固定证据句区分。共享入口在阅读反馈/历史中同步更新；跳转仍保持课/版本/句子并切到课文，不自动播放。`scripts/reading-browser-smoke.js` 同步更新按钮定位文案。

typecheck、生产构建、git diff --check通过；真实Chromium在1440/375px核对标题和按钮文案，并点击验证仍进入课文选中第10句、audio.paused=true，无横向溢出、pageErrors=[]。证据 `docs/evidence/context-copy/context-{1440,375}.png`、`logs/{typecheck,build,browser}.log`。所有写接口拦截，未改学习记录；文案修改未重复业务单测/整套阅读提交回归。

主Web已更新（监督进程PID76053），主API/MySQL保持运行，测试浏览器已关闭。未提交Git；Safari/Firefox本次未测。

### 用户追加：收藏时全部按钮闪烁（2026-10-23）

根因：`VocabularyPanel.tsx` 的全局saving布尔值绑定全部收藏按钮disabled，每次请求让5个按钮同时触发disabled透明度，再一起恢复。改为按知识点ID保存pending集合和同步请求锁，只有正在请求的词条disabled/aria-busy；其他词条保持原状态并可独立并发。服务端回执按ID局部合并，后发请求先返回也不会覆盖另一词条。失败也按ID保留不确定状态，仅阻止对应词条，其他收藏仍可操作；明确重新读取后才解除失败词条限制。

修改 `apps/web/src/components/exercises/VocabularyPanel.tsx`；新增 `scripts/favorite-feedback-browser-smoke.js`；无需CSS、后端、迁移或依赖改动。

typecheck、lint、生产构建、19项既有前端单测、git diff --check通过。新增Chromium专项passed=true、pageErrors=[]：模拟延迟检查单项/双项pending，其余按钮opacity始终1且未改DOM属性；同一词条重复点击只有1次请求，不同词可并发，逆序回执各自正确更新；模拟503仅锁定失败词条，其他收藏可继续，明确重新读取恢复状态。MutationObserver确认未操作词条没有属性变化、全部节点复用。证据 `docs/evidence/favorite-feedback/logs/{typecheck,lint,unit,build,browser}.log` 与 `concurrent-pending.png`，已查看截图。

该专项模拟收藏回执并拦截其他写接口，未写主库，不声称本轮重测真实MySQL持久化；后端沿用既有已验收逻辑。主Web已更新（监督进程PID76855），API/MySQL保持运行，测试浏览器已关闭。未提交Git；本次未测Safari/Firefox或窄屏并发交互。

### 用户追加：跳过本轮时阅读区域闪烁（2026-10-23）

根因：`ReadingQuestion.tsx` 在请求期间整组fieldset/操作按钮切换disabled，触发原生选项禁用外观和全局按钮透明度；busy提示还按条件插入/删除，推动历史区域。改为初始化/空答案仍使用真实disabled；暂时提交锁用aria-disabled、aria-busy和同步请求锁表达，保留原有外观。鼠标/键盘修改选项及重复提交均显式拦截，待确认命令只能通过“重试原提交”重发。保存提示使用固定20px高状态位，避免历史区域位移。跳过仍仅改本轮状态，不计练习，不改变阅读题目标。

修改 `apps/web/src/components/exercises/ReadingQuestion.tsx`、`apps/web/src/app/globals.css`；新增 `scripts/reading-feedback-browser-smoke.js`，既有 `reading-browser-smoke.js` 的等待条件同步检查aria-disabled，避免将视觉可用误当请求已结束。

typecheck、lint、生产构建、19项既有前端单测及git diff --check通过。新增真实Chromium专项passed=true、pageErrors=[]：1440/375px下延迟跳过回执，验证fieldset/选项/按钮透明度与disabled外观保持不变、历史相对位置/整块高度不变、原DOM节点保留；重复动作及鼠标/键盘选项修改均被拦截。模拟503后其他动作不会隐式重试，明确重试沿用同一eventId，成功解除pending。日志 `docs/evidence/reading-feedback/logs/{typecheck,lint,unit,build,browser-initial}.log`，截图 `pending-{1440,375}.png`，已查看桌面图。

专项仅模拟阅读轮事件回执和对应GET投影，所有其他写接口拦截，未修改主库学习记录；未重复Java/真实MySQL或完整作答提交套件。主Web已更新（监督进程PID78995），API/MySQL保持运行，测试浏览器已关闭。未提交Git；Safari/Firefox本次未测。

### 按阶段归档提交（2026-10-24）

用户授权分阶段提交当前代码。Phase05快照从Phase04基线分离，包含阅读/词汇及其听写相邻修复；录音、写作、V006及共享弹窗/滚动修复放入后续Phase06提交。旧文中的未提交/未进入后续阶段描述为当时记录，本节更新归档状态。独立快照检查见Phase06报告的本轮Git归档记录。
