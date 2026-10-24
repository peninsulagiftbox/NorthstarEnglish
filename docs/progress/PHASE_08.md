# Phase 08｜真实首页/报告、设置与导出备份

日期：2026-10-24（Asia/Shanghai）。用户明确授权“现在开始实施第八阶段，先看下这个阶段的提示词，再进行实施”。已完成实现与本阶段验收，主站只读交付核验通过；不进入Phase09，不提交或推送Git。

## 输入与范围

已读根AGENTS、实施计划、`Northstar_English_Codex/prompts/08_PHASE.md`、最近PHASE_07报告及 `references/phase1/` 详细规范P01/P10/P11。保留起始工作区已有Phase07与听写/录音UI等未提交修改，不把它们归为本阶段成果。仅增加真实首页/报告、偏好、JSON导出预检与新隔离库恢复。

AI按计划为独立可选项；未授权供应商/预算/数据外发，不检查或输出密钥，不发起外部模型请求。现有预置讲解按课版本与句ID定位，明确“本地预置讲解 · 未接入AI”。无ASR、发音分或能力曲线。

## 改动文件与关键决定

- `report/ReportController.java`：REPEATABLE_READ汇总真实提交、正确数、独立听写、录音、作文、完整测验与复习。六步状态按课版本呈现；浏览独立于五训练证据，当前暂停/跳过不覆盖累计练习。阅读保留真实逐题历史。
- `exportimport/ExportController.java`：事务一致全表逻辑快照，无数据库凭据；字符串SQL单元避免跨语言数值损失。`northstar.snapshot.v1` 包含原始payloadJson及SHA-256；媒体二进制/浏览器缓冲明确排除。只读预检检查项目、归属、数据版本、列结构、冻结内容与迁移基线；不宣称仅预检就已证明全部业务约束。
- V008仅增加user_setting.recording_enabled；GET设置新增字段，PUT按rowVersion保存倍速、译文、键盘提示/快捷键和录音开关。`HealthController`能力阶段08；`RecordingController`开关仅拦截新上传，已接受的幂等重试保留原回执。`DatabaseGuard`仅在显式恢复开关+时间戳隔离库名+项目身份匹配时允许恢复副本启动。
- Web：`LearningReport.tsx`、`DataTransferPanel.tsx`、`SettingsPanel.tsx`与报告/设置路由；`CatalogPages.tsx`首页使用服务端恢复点（包括旧内容版本），真实统计替换占位。`api/settings.ts`、LessonProvider/context、MediaProvider、LessonWorkspace、RecorderPanel接入偏好，默认译文只用于新上下文，不抹掉旧恢复点；`globals.css`补表单与报告间距，保留既有布局。
- `scripts/data-transfer.py`、backup.sh/restore.sh：完整私人录音备份逐文件核对SHA与大小；恢复只创建全新隔离库，不接受主库/测试库作目标。用当前已验证DDL，数据值十六进制编码，外键开启、单事务入库；处理课版本循环引用和作文自引用。既有目标拒绝，失败目标保留，不删除/重建库卷。录音文件不可与SQL事务原子提交，失败范围明确。
- `ReportExportIntegrationTest`、原DatabaseIntegrationTest权限断言、Python导出格式/SQL值转义测试、reports-browser-smoke.{js,sh}；grant-study增加设置最小更新权限，api-smoke对齐阶段与设置字段。
- README、OpenAPI、实施计划、DESIGN_DEVIATIONS、BACKUP_RESTORE及本报告。未引入新依赖、锁文件变更或全局运行时修改。

## 实际验证与证据

证据 `docs/evidence/phase-08/`（本地忽略，不提交私人数据）。项目级Node22.23.2 / Java21.0.12.1。既有隔离测试库northstar_phase01_test、API8086/Web3101；恢复副本使用额外空闲端口与新库；未删除现库/卷。

- 前端23项单测、typecheck、lint、第一次隔离webpack生产构建通过。
- Java/MySQL第一次授权verify：20项中新增统计/偏好/快照预检通过；旧Phase01“设置不可UPDATE”断言与Phase08需求冲突。改为禁止DELETE后，20项全部通过，0失败/错误/跳过；最终录音幂等开关修改后再跑verify也20项全通过，生产打包成功（api-verify-release.log）。后续导入兼容性定向测试1项通过：版本/类型/脚本/校验和/成功标志必须一致，安装时间可以不同（portable-snapshot-test.log）；最终包单独构建，不把package的skipTests当作重跑测试。
- Python10项通过；含损坏校验和、归属/版本与恶意SQL字符十六进制编码。初始沙箱拒绝ps/回环绑定，授权本机运行后通过，原失败日志保留。
- Playwright首页六步、真实报告/样本、偏好保存刷新/倍速实际应用、关闭快捷键/提示、无AI状态、JSON实际下载与预检、损坏包拒绝、1440/375布局无横向溢出、pageErrors=[]；503与零数据明确为GET响应注入。截图已查看reports-1440和settings-375。
- 备份预检首次因测试Web端口不匹配被Origin保护拒绝；新增--web-port后成功。首次恢复列名规则误拒sha256，空失败目标保留；修正后换新目标通过行数核对。脚本后来批量合并计数/授权查询，避免逐表启动Docker客户端。
- 生成正弦波录音只有空容器、不能解码，未把它当成播放成功；改用浏览器虚拟麦克风真实MediaRecorder，21660字节WebM实际解码播放约0.713秒。不是物理麦克风验收。完整备份恢复到northstar_restore_20261024153500后，37表全部导出列值与原快照逐值相同，两份ready文件大小/哈希一致；其中一份是前面110字节的不可解码测试空容器，保留如实标记，不把它算播放成功。有效21660字节WebM已在源隔离浏览器实际解码，恢复副本核对其二进制完全一致；未声称两份文件都能播放。restore-compare.log还验证非空听写新提交及相同event重放只新增一次；API重启后所有导出值和新作答保持一致（restart-restore.log）。
- 原恢复副本启动曾出现MySQL握手超时，日志保留；重试后副本启动并完成继续作答/重启核验；不把最初仅恢复行数通过当作已能继续学习。
- 主库迁移前37表原列hash与28692字节0600SQL备份完成；迁移后37表全部原列/行hash一致（main-after-final.log）。该SQL备份不包含私人录音二进制。主库没有本阶段伪造的测验/听写提交。

## 截图与未测边界

截图 `screenshots/dashboard-1440.png`、`reports-1440.png`、`settings-1440.png`、三个375宽度页面及`reports-empty-375.png`。首页/报告/设置遵循既有侧栏和卡片视觉，未声称像素级一致。

Safari/Firefox、真实麦克风、硬关机/磁盘损坏、全新机器发布恢复与教材素材合法正式发布未验收。素材/声音授权仍pending_review。纯JSON不含未同步浏览器缓冲和ready录音文件；恢复有ready录音时缺文件会拒绝。源数据库和本项目其他服务保留，所有恢复测试库/失败库不自动清理。Phase09完整集成与发布验收须用户后续单独授权。


## 补充恢复、安全与运行交付

- 零记录恢复到全新 `northstar_restore_20261024154000`，实际API8088所有指标/阅读历史为零，每个版本六步均not_started/证据0；`zero-report.log`。没有通过删除现有学习记录制造空库。原GET空态注入测试与真实零记录API核验明确区分。
- `import-rejections.log`：冻结内容篡改后即使重算checksum仍422；同包对已存在目标的再次恢复拒绝，没有重复合并；ready录音缺失在建库前拒绝。第一次失败目标20261024152000、后续验证副本/零记录副本均保留，未删除库/卷。媒体在项目`.local/restore-media/`。
- 主库V008的ALTER已经提交，但3秒数据库socket超时使Flyway未写完成登记。先核对完整SHOW CREATE TABLE与已成功的隔离测试库完全一致、默认值和旧数据不变，再仅复制该已验证V008的version/type/script/checksum登记，execution_time=0明确为人工核对登记；没有重复ALTER、删除字段或修改旧迁移。`main-migration-reconcile.log`保留依据，原main-migrate.log/api.log失败不抹去。后续启动Flyway校验全部9条迁移通过、无待执行迁移；原37表列值hash一致。
- 交付初次API只读冒烟曾因settings查询超时返回503，原`api-smoke-main.log`保留；本机启动/构建变慢期间只关闭本轮源/恢复/零数据服务释放资源，不重启MySQL或其他项目，不把环境失败写成通过。
- 本轮API8086/Web3101、恢复API8087和零记录API8088均核验自身PID/cwd后关闭，数据库和媒体保留。主站API8085/Web3100按本项目自有监督记录更新启动。
- OpenAPI YAML解析37条路径，git diff --check通过。所有导出/备份和E2E私有输出沿用.gitignore，没有新增依赖或提交操作。

## 阶段验收边界

| 条目 | 结果 |
| --- | --- |
| 服务端恢复入口、六步状态与真实报告 | 已实现并浏览器验证；状态与历史证据分列 |
| 偏好持久化、实际倍速/提示/快捷键生效 | 已在隔离浏览器验证 |
| JSON导出、严格预检、媒体另备份、新库恢复 | 已完成，逐值/哈希与继续学习、重启验证通过 |
| 重复/冲突/损坏/缺媒体拒绝 | 已验证，不覆盖现库 |
| 零记录无虚构百分比 | 真实新隔离库API核验通过，UI零响应也单独验证 |
| 无AI仍可学、上下文预置讲解 | 已验证；外部AI适配器明确未实施，可选项延期 |
| Safari/真实麦克风/完整机器灾难恢复/素材正式发布 | 未验收，留Phase09或独立授权；不签完整发布通过 |

本阶段总体按PASS_WITH_NOTES交付；新增功能和本地数据恢复已验收，版权与声音授权仍阻塞正式发布。汇报后停止，等待用户审核，不自动实施Phase09。


## 最终交付核验

- 最终主站生产构建通过：`logs/main-web-final.log`。构建包含零样本录音/复习的“暂无数据”文案；主站实际加载的页面另行验证，不以源码或编译结果代替运行验收。
- 最终API包：`logs/api-package-release.log`；完整20项后端验证见`api-verify-release.log`，后续可移植快照修正的1项定向测试见`portable-snapshot-test.log`。前端23项、类型/lint和Python10项通过；后端package中的skipTests不计为测试通过。
- `logs/api-smoke-main-final.log`通过：真实健康/阶段08/新设置字段、no-store、Host/Origin拒绝及404/405/403契约。
- `logs/production-browser.log`结果passed=true、pageErrors=[]、mainWrites=0：首页服务端恢复点包含版本/Tab/句子，报告/设置真实加载，1440/375无横向溢出。真实零数据API8088响应已先独立核验，再将该原始响应回放到UI渲染并截图；这是响应回放，不冒充浏览器当时直连仍在运行的零数据副本。
- 主站截图：`production-dashboard-1440.png`、`production-reports-1440.png`、`production-settings-1440.png`、`reports-real-zero-375.png`；本轮没有替用户提交主库学习作答、修改主库偏好或下载私人录音。
- 所有本轮测试浏览器已关闭。主站保持Web3100/API8085/MySQL3308；其他项目服务与既有卷保留。未自动提交、推送或开始Phase09。

### 用户中断后继续收尾

继续时重新核验发现原API/Web进程已退出，本项目MySQL容器也处于exited（ExitCode255，未显示OOMKilled）；退出根因未另行确诊。只启动已核验的原MySQL容器，原项目身份/卷保留，不重建数据库、容器或卷；随后启动已构建API/Web。`resume-api-smoke.log`重新通过；`resume-live-final.log`实际确认首页/报告/设置HTTP200、API健康、schema008/phase08以及AI关闭。主站恢复后可访问，本轮没有借此清理或回退任何用户数据。

### 审核调整：默认倍速点击循环

按用户截图要求，将SettingsPanel默认倍速下拉框改为按钮，沿用播放器顺序1x→1.25x→1.5x→0.75x→1x；仍需“保存偏好”才写入服务端。更新reports-browser-smoke.js对新控件的操作。typecheck、lint及主站生产构建通过，已只更新本项目Web3100。实际Playwright验证完整循环、Enter/Space、375宽度无溢出，pageErrors=[]、写请求0且已保存偏好不变；日志settings-cycle-{typecheck,lint,deploy,browser}.log，截图settings-speed-cycle-1440.png。

### 审核调整：导出按钮位置

按用户截图要求，将“导出学习JSON”移到DataTransferPanel卡片标题行右侧，与服务状态卡片的标题/操作布局保持一致；640px及以下移到标题下方，间距12px。只调整DataTransferPanel.tsx及globals.css布局，导出/预检逻辑保持原样。typecheck、lint、生产构建通过并更新Web3100；Playwright验证1440标题行右对齐、375标题下方排布、无横向溢出、pageErrors=[]/写请求0。已查看两张卡片截图export-position-{1440,375}.png，日志export-position-{typecheck,lint,deploy,browser}.log。

### 审核调整：测验结果底部操作栏

按用户截图要求，给QuizPanel结果增加独立操作栏：桌面端重做提示左对齐、复习入口右对齐并垂直居中；提示使用次要文字，统一分隔线和上下间距，交卷历史留24px间距；手机端上下排列、间距12px。只修改QuizPanel.tsx及globals.css布局，不改交卷、复习或历史逻辑。typecheck/lint/主站生产构建通过。Playwright重放已有交卷结果（不是真实新增交卷），验证1440/375对齐、间距、链接和无溢出，历史前后相同，pageErrors=[]、真实写入0。截图quiz-footer-{1440,375}.png已查看；其中同步错误提示来自测试主动拦截恢复点PUT以保护主库，不代表实际主站接口故障。日志quiz-footer-{typecheck,lint,deploy,browser-final}.log；测试浏览器已关闭。

### 审核调整：所有选择题选项随机排列

核实冻结内容包的3道课时测验及1道阅读题，正确选项确实都是原数组第一项。新增lib/shuffle.ts，以不修改原数组/选项ID的Fisher–Yates随机排列，共用于QuizPanel与ReadingQuestion。进入练习和成功交卷后的新一轮重新随机，作答、开始/暂停/恢复及状态刷新保持本轮顺序；再次进入/刷新可产生新顺序，但测验草稿仍按ID恢复。阅读新一轮清空上次选择，历史与反馈继续按ID匹配。随机排列允许偶然重复或正确项偶然位于第一位，未强制排除某个位置或改写冻结答案。

新增shuffle.test.ts穷举3选项全部6种排列，验证正确项三个位置各出现2次、ID/文案引用不变、原数组不变、边界和新随机抽取。25项前端单测通过，typecheck/lint/生产构建通过并更新Web3100。最初测试代码的Object.freeze回调类型推断错误已修正并重跑类型检查，原失败日志保留。

Playwright使用受控随机数确保正确项显示第三位，并将测验/阅读请求实际转发到已核验隔离API8086（Origin3101）；其他主库写请求全部阻断。验证作答/暂停不重排、刷新重排后仍恢复原选项ID、每轮重新随机、反馈选项对应正确。隔离库实际3轮成绩3/3、3/3、0/3，阅读正确/错误各1次；均由真实后端按选项ID判定。主库测验和阅读历史前后完全一致，pageErrors=[]、主库学习写入0。日志shuffle-{tests-final,typecheck-final,lint,deploy,browser,stop-test}.log。无后端/数据库迁移改动；隔离测试服务验收后关闭，保留测试数据和原卷。

### 审核调整：倍速改为无边框文字控件

按用户截图要求，SettingsPanel默认倍速去掉边框、底色和阴影，与标签同一行垂直居中、间距16px；保留原点击循环及键盘焦点提示，不改保存方式。仅修改SettingsPanel.tsx/globals.css。typecheck、lint、生产构建和Playwright通过；实际计算样式border=0/background透明，同行间距正确，四档循环及Enter/Space均通过，375无溢出，主库写入0/偏好不变/pageErrors=[]。主站Web3100已更新，截图speed-text-{1440,375}.png，已查看桌面控件；日志speed-text-{typecheck,lint,deploy,browser}.log。

### 审核调整：设置卡片操作统一放底部

按用户最新截图要求，替代此前标题右侧布局：HealthPanel“重新检查”移到状态列表底部，与检查时间同行，时间在左、按钮在右；DataTransferPanel导出按钮移到底部，与文件选择区并列，文件选择标签/输入分行，按钮右对齐。两卡统一settings-card-footer间距和边距，手机端空间不足自动换行且操作保持右对齐。仅修改两个组件和globals.css，保留加载/失败重试、导出与预检逻辑。

typecheck、lint、主站生产构建通过；Playwright验证1440/375位置/对齐/无溢出、真实健康GET重查，以及明确注入503后重试恢复。pageErrors=[]、写请求0，没有导出私人文件或修改偏好。已查看四张card-actions-{health,export}-{1440,375}.png截图；日志card-actions-{typecheck,lint,deploy,browser}.log，Web3100已更新。
