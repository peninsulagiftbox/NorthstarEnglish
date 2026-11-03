# Phase 10D-2 R5 P1 定向修复

日期：2026-11-03（Asia/Shanghai）。结论：**CORE 定向修复及本轮验证通过，可再次提交独立 QA；不代表 10D 整体 PASS，不进入 10E。**

## 修改与边界

修复 QA-D02-R5-FINAL-001：`apps/web/src/components/review/ConceptReviewQueue.tsx` 消费 `nextCursor`，提供有界的“加载更多概念卡”。每次请求仍为后端默认 20 张；不会为了计数自动无界遍历。到期模式继续对每一已读取分页检查 pending outbox，即使卡片已不再到期，未确认的原事件仍可恢复。到期按钮明确写“已加载”，未读完分页不显示全局总量或最终空状态。

`apps/web/src/lib/review/conceptQueue.ts` 封装同一队列的分页状态：卡 ID 去重、保留后端返回顺序、保留更高 rowVersion；刷新和模式切换同步重置列表及游标，并推进请求代次；旧网络响应、旧 outbox 异步读取、卸载后响应均不能提交状态。分页加载期间同步锁住重复请求；错误保留已加载卡片及原游标，重试继续同一页。该实现直接用于 UI 和 Node 测试。

新增 `apps/web/tests/conceptQueue.test.ts`（7 项）和 `qa/phase10d2-r5-fix/` 独立验收工具。未增加业务功能或依赖；未改卡内来源组件、自评协议、后端代码或任何 Flyway 迁移。

## 环境与候选身份

- Git HEAD：`a5084cb`，main；保留此前全部未提交与未跟踪候选。完整输入范围以冻结清单为准。
- 新隔离容器：`northstar-qa-final-r5fix-20261103`，MySQL 8.4.9，127.0.0.1:3380，UUID `160a0a24-d741-11f1-825b-2e0319a9d1eb`。本轮创建新卷，未采用或部署个人数据库。
- 修复版 API/Web：127.0.0.1:8194 / 3201。旧版复现另启本轮子进程 8192/3199，同样只连接本轮新隔离库；使用旧构建的复制件，未重写 R5 原失败构建。
- Web BUILD_ID：`SuZ-zEmOT_iOi5QX-oa9O`，Node v22.23.2；JDK 为项目内 Java 21。
- 运行 JAR：`output/review/northstar-phase10d2-r5-fix-candidate.jar`，SHA-256 `771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6`，与 R5 相同。隔离副本重建 JAR SHA `aa149048778aa7cd799979333c1b5a855e6cbf9205867f3cf0ec1f2d15038887`；124 个应用 class/resource 条目逐字节一致（ZIP 元数据不作为代码变化证据）。
- R5 原失败证据 ZIP SHA `8705e518524c1eac3db6c58bdae2c213ea161a90911cce3f83a7ff244d00e954` 与既有 sidecar 相符。49 个迁移文件与 R5 冻结记录逐一一致。

## 实际运行与结果

命令均在项目根目录执行，命令日志、退出码、时间及哈希位于 `qa/phase10d2-r5-fix/evidence/commands.jsonl`；凭据仅存 `.local/qa-final-r5fix/credentials.json`，不进入交付。

| 检查 | 命令/证据 | 结果 |
| --- | --- | --- |
| 隔离初始化 | `python3 qa/phase10d2-r5-fix/run.py create` | 新库、49 项迁移初始化通过 |
| 前端 | `python3 qa/phase10d2-r5-fix/run.py nodes` | Node 43/43、typecheck、lint、生产 build exit0；lint 仅既有 KnowledgeConcepts.tsx 未用 busy 警告 |
| 后端 | `python3 qa/phase10d2-r5-fix/run.py regressions` | 核心 Java 11/11，package exit0，124 应用条目无差异 |
| 合法内容登记 | `python3 qa/phase10d2-r5-fix/run.py seed` | 2 fixture 测试通过；原创100概念经正式知识登记入口登记；卡片只由真实错误作答生成 |
| 旧问题复现 | `baseline-21.json` | 旧 R5 BUILD_ID fxpqzia8rPru49bVZ_KIY，API21/UI20，无加载入口 |
| 数量矩阵 | `python3 qa/phase10d2-r5-fix/browser_stack.py`，`matrix-{0,1,20,21,22,100}.json` | 六组真实卡数量全部通过；首次到期/全部/刷新/切换/重开均逐卡对齐 API 顺序，无重漏 |
| 异步与重试 | `matrix-100.json` | 页外末卡来源与自评通过；成功响应故意丢失，刷新页面后原事件保留，重放后消失；快速连点只发1页请求；刷新及模式切换后的迟到分页被丢弃；503保留20卡并原游标重试成功 |
| 自评与CAS | `rating-cas-check.json` | 重放 eventId 仅1结果、rowVersion只推进1次；新eventId携带旧版本返回409且结果数不增；本测试课程真实attempt仍为100 |
| 混合权限来源 | `matrix-101.json` | 100卡外增加bank，共101张；bank API/UI完整83条，82受限/1可见，无重复；受限响应逐字段检查白名单，撤回来源不含标题、句文、练习内容 |
| API分页 | `pagination-api-results.json` | 到期0/1/20/21/22/100全遍历，ID唯一、全局排序；20满页后空尾页正确终止；all模式101卡分别以limit1/20/100完整遍历；limit101返回422 |
| 到期数量UI | `due-check-{0,1,20,21,22,100}.json` | 隔离夹具分别设置到期数量；UI逐页完成后数量正确，无自动无界读取；来源/结果/回执表前后逐值不变 |

Node 新测试直接调用生产分页实现，覆盖同一数据规模、重复ID、高版本、pending过滤、旧模式响应、分页锁、错误原游标重试、卸载及迟到outbox读取；不是复制一份业务逻辑作为断言。

## 失败日志与验证限制

初次 freeze 缺 fixture 路径、一次中断、测试断言的 TypeScript 收窄错误，以及首轮100卡 Playwright路由清理错误均未当作通过。浏览器首轮日志保留为 `browser-100-first-failure.log`；续跑同到期时间按UUID重排导致固定词卡不再位于页外，日志保留为 `browser-100-second-failure.log`，最终改为实际API末卡。作答计数曾误把此前Java回归的4条其他课程记录算入，本轮改为明确限定测试课程，未删除其他记录或放宽业务断言。

部分早期 freeze/类型错误只存在会话输出；最终证据包不声称包含被中断会话的完整原始终端日志。100卡验收从显式检查点续跑，隔离夹具将到期时间重置后再次验证；本轮有多条不同eventId的合法自评，但每个丢响应事件分别验证仅计数一次。测试用 due_at 更新只发生在新隔离库，未更改调度协议或迁移。

本轮不补称 B08/B09 全矩阵、M03–M08 恢复演练、真设备麦克风、完整Demo/音频闭环通过。旧 R5 仍维持其原FAIL结论，由后续独立QA决定新的阶段门禁。

## 冻结与交付

`qa/phase10d2-r5-fix/evidence/qa-final-candidate-manifest.sha256` 冻结全部未提交/未跟踪业务、文档、QA输入（排除本轮持续生成的evidence目录，防清单自引用）；测试副本与当前源文件逐字节核对。补充的全工作区清单 `output/review/northstar-phase10d2-r5-fix-all-worktree.sha256` 在打包前冻结 **git status --untracked-files=all列出的全部现存文件，包含本轮evidence JSON/JSONL和旧QA证据**，并放入ZIP的 `freeze/all-worktree.sha256`；忽略的运行产物通过BUILD_ID/JAR身份及包内SHA256SUMS单列。

交付 `output/review/northstar-phase10d2-r5-fix-sanitized-evidence.zip` 和同名 `.sha256`。包采用显式目录白名单，扫描本轮真实凭据并检查嵌套trace，排除私有SQL dump、环境文件和音频。解压执行 `verify.py` 核对每个成员；全工作区清单在打包后再次对当前文件验证。私有最终dump留在 `.local/qa-final-r5fix/`，仅身份摘要进入包，未声称恢复验证。

截图/trace：`output/playwright/phase10d2-r5-fix/`（baseline、matrix、六组due-check）；结果原文在 evidence JSON。验收脚本退出时停止自有API/Web子进程，隔离MySQL及卷保留用于复核。未提交、推送GitHub，未部署个人数据库，未进入10E。下一步仅为独立QA接收新候选并补齐其余阶段门槛，报告后停止。
