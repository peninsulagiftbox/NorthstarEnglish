# Phase 10B-3 实施计划（已获实施批准）

日期：2026-10-28（Asia/Shanghai）。依据用户补全的 Phase 10B-3 任务 A–F、T1–T7。本文件保留实施前计划；用户随后明确“批准！”授权实施。实际执行与结论以 PHASE_10B_3 报告及证据为准，本文件不构成阶段 PASS。

## 1. 已核查基线

- Git HEAD：`e5963bae8766194a32cd00703cd64a7ed2e52d46`。已有未提交修改为 `apps/web/src/app/globals.css`、`apps/web/src/components/CatalogPages.tsx`、`apps/web/src/components/LearningReport.tsx`，另有两组 UI 报告和证据目录；全部保留。
- 已查阅 AGENTS、README、IMPLEMENTATION_PLAN、phase1 适用约定、phase10 的 03/04/06/07/08/09/10A_REVIEW_RESPONSE、10B-1/恢复及10B-2/部署/专项回归报告、最近两份 UI 报告，并检查 Java、SQL、Next 转发/DTO、测试及备份恢复工具。
- 源库经容器标签、回环端口、卷及 project_identity 校验后，以运行账号执行只读事务。实际成功 history 为 V001–V008、V009.01–V009.05，另有既存 BASELINE 0（不是 V000 SQL）；Demo current 为 `demo-01-v2`。API 8085、Web 3100 健康均 UP、schema=009.05。没有运行 Flyway validate/migrate，也没有启动 Spring 来做预检。
- 13 份现有 SQL 与 HEAD 字节一致。10B-1 隔离候选为 V009.01–.04；10B-2 增量为 V009.05，有升级、空库、故障、新目标恢复结果及后续专项回归。旧隔离容器当前均已停止；本轮未启动它们，未在线查询其 history。
- 本轮重算10B-2交付清单中的10份 API 文件和121份证据文件 hash，均匹配；两轮命令记录对应41+28份日志 hash 均匹配。专项回归107份源码中104份一致，差异为上述三份 UI 文件。`phase10b2_isolated.py` 有后续已提交修订，不将旧测试外推为当前脚本已重新验收。
- 10B-1 历史签收为独立代理技术审查 PASS_WITH_CONTROLLER_NOTE，原主控退出1保留。10B-2已有源码、真实隔离结果及部署证据支撑其既定范围；本轮未重跑完整测试，不能宣称重新完成独立验收。

## 2. 复用能力与缺口

复用 `CatalogReader` 多课/显式历史版读取、册内分页、paragraph及同版外键、`AudioResources` 路径与hash验证、Demo冻结适配器、普通启动只读播种校验、显式空库初始化、原学习事件幂等和恢复工具身份门禁。Next通过rewrite转发Java，没有独立API路由实现。

现缺 sentence/paragraph identity、跨版映射、publication_state、content_readiness及发布审计。已有 current 复合FK保证本课归属，但不保证目标发布状态。作答/草稿/恢复点等入口主要核对 lesson.availability，需补版本级门禁。导出虽枚举所有表，CONTENT分类、schema白名单、恢复顺序及权限必须显式同步。

## 3. 实施切片及设计

### 3.1 身份与映射（A，T1/T2）

- 新建 `sentence_identity`、`paragraph_identity`：UUID/opaque PK、lesson_id、registry_key；唯一 `(lesson_id,registry_key)`、`(id,lesson_id)`。实际句/段增加 identity_id 和必要lesson上下文，复合FK保证身份、版本、Lesson一致，唯一 `(version_id,identity_id)` 防止版本内重复。
- 不重建 paragraph/sentence，不修改任何原PK、stable_key或学习引用。历史回填使用冻结的显式物理ID→预分配UUID登记清单，重复执行结果确定；不能通过标题、序号、hash或ID后缀生成长期身份。
- Demo v1/v2逐句核对原文本及音频差异后才允许共享逻辑身份；语义等价不确定时保守分配独立身份。换音频不自动成为 equivalent，不凭 stable_key 生成映射。兼容核对清单及确认来源单独留证。
- `version_sentence_map`保存本课、源/目标版本与物理句、relation、mapping_group、审核来源/审核人、原因及时间；双端复合FK保证本课同版上下文。服务校验不同版本及组基数：equivalent/edited为1:1、split为1:N、merged为N:1，不能靠逐行FK代替组校验。
- 删除以显式 no_target 状态及 NULL 目标表示，和有目标的四类关系用CHECK区分，绝不猜相邻句。段落连续身份复用registry；拆分/新增采用显式登记的新身份，保留旧段投影，不要求本阶段另建通用段落映射系统。
- identity/映射只用于定位与人工 equivalent 参考提示。所有尝试、correct/practiced、复习、自评、草稿、作文及录音仍绑定原课/版/物理句，绝不复制为新版证据。

### 3.2 生命周期、快照与类型（B/D，T3/T5）

- 增量增加 draft/validated/published/withdrawn、独立 readiness、schema/profile及必要发布时间与校验快照。Demo两版明确回填 published + legacy_unassessed，保留 release_ready=false、pending_review、local_test_only及原hash/字节；例外仅限核验过的冻结版本。
- 新版本默认draft；通过当前基础规则得到validated，再显式发布。teaching_complete保留类型但本阶段不开放授予；共享音轨、未支持的教学profile不能借基础校验发布。
- 原 content/manifest hash 保持原算法。新增带算法版本的关系内容快照摘要，覆盖正文、句界、段句顺序、音频元数据/区间、实际题目答案及已支持任务；校验原始包/文件、DB投影和媒体，不能对MySQL重新序列化JSON求hash冒充原字节校验。摘要不含可变发布状态或独立追加的审核映射。
- 版本内容没有原地更新入口；变正文、音频、区间、答案或任务创建新版本。发布前复核冻结快照，发布事务中复核关联内容、许可和验证凭据；内容写入权限收敛，不给普通应用内容修改权。
- 已核查实际CHECK：`lesson_chk_1`及`audio_asset_chk_1`；执行前仍按表达式复核。独立增量ALTER分别保留旧值、加入original/original_recording，不改V002或content_license来源分类，不UPDATE旧枚举。
- 课程kind与音频来源独立校验。B04使用自编文本、自有测试音及明确标记的许可元数据夹具；第三方授权组合只验证规则，不宣称夹具拥有真实第三方授权。

### 3.3 显式发布、CAS及审计（C，T4）

- 提供独立本地Java入口及可测服务，不启动Web/ApplicationRunner/Flyway/reconcile。发布进程不得执行DDL；使用范围受限的内容操作权限，不扩普通app权限，不提供公网发布接口。
- 请求包含operationId、lessonId、targetVersionId、expectedCurrent（允许显式NULL）、期望冻结hash及操作者。校验归属、validated状态、内容/媒体完整性、支持的基础规则、readiness与文本/每项音频许可门禁；未知权利拒绝发布。
- 短事务锁定Lesson及必要版本/许可行，重新核对条件；以NULL安全比较执行current CAS。状态变更、current及成功审计同事务提交；零行更新返回明确CURRENT_VERSION_CONFLICT，失败不得留下published半成功。
- operationId唯一并绑定请求hash；同请求重放原结果、异payload冲突，数据库提交后响应丢失重试不重复审计。业务拒绝在不修改状态/current的事务内保存确定失败结果；意外SQL异常先回滚，再单独记录可记录的失败。数据库不可用时只保留本地命令失败日志，不能假称DB审计已写入。
- 审计保留请求标识、课、目标、预期旧值、实际指针、时间、结果/code及hash；非法目标请求也能记录请求值，不让审计FK失败掩盖原错误。审计只追加，恢复时按原值保留。
- 撤回同样显式、幂等、事务化。撤回current必须同时CAS切到经校验的已发布版本或显式清空current，禁止current继续指向withdrawn，不自动挑相邻版，不删除历史。

### 3.4 API、前端与旧客户端（E，T3/T6）

- 版本/课程响应追加 publicationState、contentReadiness、current标识及身份/映射信息；保留旧响应结构、深链和六Tab布局。目录只给符合门禁的当前版本，显式历史链接仍可读未撤回旧版。
- 前端按服务端审核映射定位；只有确定1:1关系才可定位，拆合/无映射/未确认明确提示并回新版首句，不猜ID前缀，不复制旧草稿。人工equivalent可显示“存在旧版本学习记录”，不显示新版掌握。
- 新增统一版本访问门禁并覆盖正文/媒体、新作答、复习结果、草稿写入、作文、录音及恢复点相关入口；历史读取与新写入分开，撤回返回明确 VERSION_WITHDRAWN（拟HTTP410）。服务端写事务内复核并协调撤回并发，避免仅请求开始时检查的竞态。
- 撤回前已提交成功的同event同payload仍重放原回执；未提交的新event拒绝。旧outbox不清空、不换eventId；终止性撤回错误保留本地内容并提示，避免无限重试。个人录音/旧作文/历史结果仍可追溯，课程媒体分发停止，权利限制时显示原ID与不可用原因。

### 3.5 迁移、备份恢复与隔离（F，T6/T7）

- 迁移从未占用的V009.06起，建议依次拆为：身份registry、可空上下文列、确定性回填、NOT NULL/UQ/FK、映射、生命周期列、生命周期回填/约束、审计/校验凭据、课程CHECK、音频CHECK；每个必要DDL再按可恢复边界拆号。最终编号/hash在首次执行前冻结；不得修改已执行SQL。V010等旧文档编号是分组提案。
- 每个单元有前置断言、目标schema/旧值检查、回填及后置断言、中断状态表和新目标恢复策略。DDL与DML及业务发布分别记账，不宣称跨DDL整体回滚。
- 复用受控旧备份，至少执行V008恢复→现有迁移→新迁移，以及全新隔离库V001→目标→显式初始化；另从当前固定009.05的已有备份副本升级。核对备份hash/候选依赖，不为测试停写或重新备份个人库，不把历史备份称为当前全量快照。
- 全新命名容器/卷/账号/端口/构建/媒体，拒绝个人源UUID和端口、既有目标；旧测试资源不复用覆盖。失败目标和卷保留，只停止本轮核验归属的服务。
- 新表显式归入内容registry/映射、验证凭据或操作审计分类；更新ExportController分类、data-transfer版本与一致性规则、FK恢复顺序、必要权限和测试。审计不能误当可由学习快照覆盖的学习数据。
- 同schema备份恢复必须逐值完整；V008/009.05快照先按原版本工具恢复再升级，禁止改JSON schemaVersion绕门禁。个人数据对账在受控备份的隔离副本按旧表/旧列逐PK完成，不向个人库写测试事件，也不声称覆盖备份之后的个人新增记录。

## 4. 验证与交付

实施审核通过后，先定向Java/Node/Python测试，再隔离真实MySQL及必要Playwright，最终执行项目级Java21 Maven verify、Node22 test/typecheck/lint/build；DB门控跳过不算PASS。所有构建在独立副本，避免覆盖运行中的target/.next。

| 验收 | 必须取得的证据 |
| --- | --- |
| T1/T2 | 人工确认1:1、编辑、拆分、合并、删除无目标；跨课FK/版本内重复拒绝；新增身份及无映射；旧成绩/草稿/复习零迁移 |
| T3 | draft拒绝、validated发布、撤回拒绝新命令/保留历史/旧回执重放、旧未撤回版继续作答；普通启动两次指针及表值不变 |
| T4 | 两个独立DB连接同步争抢v1→v2/v3恰一成功；过期预期、重复operation、异payload、跨课/无效目标、坏hash/许可/缺媒体及事务内故障；提交后响应丢失重试与审计对账 |
| T5/B04 | 3×3来源组合及许可匹配、未知值/不匹配拒绝；CHECK替换中断识别及新目标恢复；原枚举/行值不变 |
| T6 | Demo两版PK/正文/hash/媒体及原段句关系；event/receipt、作答、草稿、作文父链、录音状态/文件、复习到期及旧URL逐项核对 |
| T7/B01/B03 | 升级与空库两路径、DDL边界/history登记/DML回填故障、新目标恢复后真实续学和重启；新表/审计/映射同schema完整恢复；旧Demo浏览器闭环与新发布/撤回提示回归 |

保留失败原始命令、cwd、实际退出码、源码/迁移hash、SQL状态、trace及截图；隐私数据、录音、SQL原件和凭据仅存受限.local，不上传公共证据。人工实听、真实麦克风和另机未执行时明确NOT VERIFIED。

最终交付 `docs/progress/PHASE_10B_3.md`、`docs/handoff/evidence/phase10b3/`、实际变更/迁移清单及T1–T7/B01–B04逐项结论。全部满足才建议PASS；缺项按CONDITIONAL PASS/FAIL/NOT VERIFIED如实列出。报告后停止，交人工独立审核，不自动提交Git、迁移个人库、部署新schema应用或进入10C。

## 5. 审核停止点

待用户审核上述实施方案后才开始代码与隔离实验。若现场约束、历史数据或许可模型与设计发生严重冲突，停止并报告，不自行扩大范围。本阶段禁止项按完整任务执行；当前个人站点及其Flyway自动迁移路径不用于10B-3验证。
