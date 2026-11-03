# Phase 10D-2 再次封版验收（R5）

测试日期：2026-11-02；报告归档：2026-11-03（Asia/Shanghai）。执行授权：用户“再进行一次封版验收 / 继续”，沿用附件 R4 的验收标准与新 P0/P1 即停规则。

**结论：FAIL — QA-D02-R5-FINAL-001（P1）。不建议关闭 Phase 10D，不建议进入 10E。**

上一轮卡内83条来源分页修复本轮独立复测通过；本轮新发现的是**概念卡队列自身只取第一页**。没有修改业务实现、迁移、验收标准或旧测试断言。本文是当前结论，R4报告与原始FAIL包均已归档保留。

## 1. 候选身份与测试边界

- Git：`main`，HEAD `a5084cb4442a7b78afad5c920459c22f02f679ce`。未提交/未跟踪 D01/D02 文件均纳入检查，详见 `qa/phase10d-final-r5/evidence/git-status.log`。
- 初始389项清单：`candidate-at-test-start.sha256`，SHA-256 `ac1e29849324b27325962fdd067b41935e3479afafa68753fd71a9f500d42f12`。复制至 `.local/qa-final-r5/source` 独立执行 Node 构建、Java测试和JAR重建。
- 最终完整392项清单：`qa-final-candidate-manifest.sha256`，SHA-256 **`708edab2f1364127ef65949f805378cab535245a4e9be7ac29c55c8212c5a9ad`**。仅补入只读复核的2个脚本及收尾脚本；原389项工作树和实际测试副本逐文件一致，未在测试后改业务候选。逐项证据 `candidate-binding-final.json`。
- 相对R4业务差异仅 `apps/web/src/components/review/ConceptReviewCard.tsx` 的来源分页修复；其他差异为QA打包工具。见 `candidate-identity.json`。
- 实际HTTP运行JAR SHA-256：`771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6`。本轮重建JAR `50931886a5f5c4fda095fdf0a1e48546a0e9d9d6a4d69892a96942bb7624926a` 的124个应用class/resource条目与运行JAR字节完全相同，差异0：`jar-rebuild-comparison.json`。
- 本轮独立Web BUILD_ID：`fxpqzia8rPru49bVZ_KIY`，构建代理8192。Node `22.23.2`、npm `10.9.8`、Java `21.0.12.1`、MySQL `8.4.9`；版本日志均在本轮evidence。
- 最新Flyway `012.11`；`012.08/09/10/11` checksum依次 `614772575 / -1897723092 / 1214340811 / 747985570`，均success。`migration-inputs.json`、`final-flyway-history.log`保留全历史和SQL哈希。没有修改旧迁移、repair或clean。
- 当前源码保留服务端分页游标修复、10C-2-R1 `verifiedRun`/`quizFilter` 和 data-transfer 动态剔除生成列的实现；“实现仍在”不等于“本轮恢复已验证”。

以下证据短路径均相对 `qa/phase10d-final-r5/evidence/`。原 R4测试、CORE自测及其他候选结果不作为R5通过依据。

## 2. 隔离目标

| 项目 | 本轮实际值 |
| --- | --- |
| 容器 | `northstar-qa-final-r5-20261102` |
| 容器ID | `882d9dba76cd22190c7bef8c73e8e91f66091c6a70ff5a2875ddbab1cf9234ea` |
| MySQL端口 / schema | `127.0.0.1:3382` / `northstar_phase01_test` |
| server_uuid | `3c213ff3-d6d4-11f1-9124-068c3e69d404` |
| 卷 | `northstar-qa-final-r5-20261102-data` |
| 账号 | 专属 `northstar_app` / `northstar_migrator`；凭据仅在本地私有目录 |
| 媒体 | `.local/qa-final-r5/content`、`.local/qa-final-r5/recordings` |
| API / Web | `127.0.0.1:8192` / `127.0.0.1:3199` |

证据：`database-identity.json`、`container-mounts.log`、`browser-runtime.json`。只创建新目标，未连接个人3308，也未连接/清理此前3348/3349/3364/3380/3381现场或重启3100/8085。

## 3. 新P1：QA-D02-R5-FINAL-001

**概念卡超过默认20条时，“全部概念卡”和到期队列只展示第一页，没有下一页入口，后续合法概念卡无法从当前列表访问，队列数量也被截断。**

### 实际复现

1. 在上述新隔离库运行现有回归，再登记原创A/B课程及21句原创花园测试课程。使用 `KnowledgeRegistrationCli.register()` 合法登记21个独立概念和Occurrence，不直接INSERT卡片或Attempt。
2. 通过真实HTTP完成83次A/B错误阅读Attempt（形成1张跨课金融bank卡），再完成21次花园课程错误听写Attempt（每题1个概念），生成共22张卡、104条来源。错误听写经过真实音频完整性/时长检查。音频为既有原创合成测试音，明确不是发音示范。
3. 撤回课A以复测83条混合权限来源；bank卡仍有课B的1条可见来源。全部22张卡均合法、到期且 `rowVersion=1/reps=0`。
4. `/concept-reviews/due?all=true` 返回20条及非空 `nextCursor`；沿游标第二页返回2条，22个ID唯一。
5. 独立Chromium profile打开 `/review`，在**包含“全部概念卡”按钮的唯一section**内统计 `.review-card h2`。首次全部、刷新全部、重新打开全部、切换到期四种状态均只显示20张，按钮只有到期/全部/刷新及已显示卡的操作，没有下一页或加载更多。
6. 缺少两张：

| 概念 | cardId | API直接读取 |
| --- | --- | --- |
| `qa-r5-c20` / QA garden apple | `8b42234a-775c-4c28-8b42-7180e6589322` | 卡详情200，来源200，1条可见来源 |
| `qa-r5-c21` / QA garden pear | `3b41d4f6-28a1-49c3-a4d7-a0e619f4e430` | 卡详情200，来源200，1条可见来源 |

这些记录没有丢失；缺陷是UI不能在当前“全部”列表中选择它们、查看其来源或发起自评。没有通过评价前20张来改变排序绕过缺陷，也不声称它们在排期变化后永远不可见。

### 证据与可信度

- `queue-recheck-result.json`：两页完整响应、四次UI概念卡标题/数量、缺失ID、按钮文本、直接详情/来源响应、pageErrors和网络记录。
- `queue-recheck.log`：真实进程 **exit1**，每次 API22 / 概念DOM20。
- `recheck-read-only-comparison.json`：卡、来源、结果、Attempt、知识关联、回执、旧句卡、旧评价、学习证据9表复核前后逐值相同，均true；前后原始行在 `recheck-before-*` / `recheck-after-*`。
- 截图 `output/playwright/phase10d-final-r5/concept-queue-only.png`、`queue-header.png`；精确section文本 `concept-queue-only.txt`；真实交互轨迹 `queue-recheck-trace.zip`。
- 保留首轮 `browser-result.json` / `browser.log`：首轮全页`.review-card`定位误含24张旧句子卡，得到总DOM44，不作为“概念卡数量”的证据。其缺失标题提示随后经独立只读复核确认；未删除或改写原始失败记录。
- 两轮均无未捕获pageerror；networkErrors中保留导航/预取中止记录，不将其统一删除或宣称网络错误为0。分页和缺失卡直接读取均200。

根因：`apps/web/src/components/review/ConceptReviewQueue.tsx:13` 固定调用 `getConceptReviews(true)`；第15行只消费 `page.items`，整个组件忽略 `nextCursor`，第19行仅从已加载项计算到期数量。后端和前端API函数支持游标，队列没有消费。

等级依据：沿用原QA缺陷定义“P1=功能断裂”。问题影响整个概念卡列表的合法任务与来源入口，超过20卡即可重现；不是仅计数文案错误，不是上轮卡内83条来源缺陷复发。

给CORE的最小建议：消费队列 `nextCursor`，提供稳定的继续加载/翻页并按卡ID去重；明确当前显示数量与到期数量的含义；保持待确认命令可见性。以超过20张真实卡验证全部/到期、刷新、翻页终点和页外卡自评/重试。**本轮QA不改业务，按停止规则交回CORE。**

## 4. 本轮实际通过及失败

| 项目 | 本轮执行结果 | 证据 |
| --- | --- | --- |
| Node test | PASS，36/36，0失败，exit0 | `node-test.log` |
| typecheck / lint / build | 全部exit0；lint仅原有KnowledgeConcepts busy未使用warning | `node-typecheck.log`、`node-lint.log`、`node-build.log` |
| Java核心回归 | PASS，11/11，0失败/错误/跳过，exit0 | `java-regression-correct-origin.log` |
| 核心覆盖 | ConceptReview集成1、KnowledgeSources集成1、KnowledgeConcepts单元4、QuizScale集成3、QuizReportR1集成2 | 同上；不冒称规范化CLI集成另跑 |
| Maven package / JAR应用条目对照 | PASS，exit0，124条目0差异 | `java-package.log`、`jar-rebuild-comparison.json` |
| 新空库初始化 | PASS，012.11；仅初始化路径，未执行恢复 | `initialize.log`、`flyway-history.log` |
| QA原创fixture登记 | PASS，两项执行exit0 | `seed-fixtures.log` |
| 83混合来源修复独立复测 | PASS；4次加载更多，5页20+20+20+20+3；83唯一、82受限/1可见、字段白名单正确；DOM83，显示1/1，按钮消失 | `browser-result.json`、`source-trace-responses.json`、`source-page-audit.json` |
| 超20张概念卡队列 | **FAIL**；22/20，四种界面状态均遗漏2张 | `queue-recheck-result.json` |

`source-trace-responses.json`来自本轮浏览器原始trace的响应内容；`source-page-audit.json`对相同URL重读去重后核对5页83个唯一来源及受限字段白名单。原 `QA-D02-R4-FINAL-001` 卡内来源分页缺陷本轮定向复测关闭；旧服务端500/合法游标422缺陷未重新打开。

最初sandbox执行create时，本地端口绑定被禁止，空闲端口探测耗尽并退出1；经批准在sandbox外重跑，创建3382目标成功。证据 `launch-failures.json`，不将环境失败冒充业务缺陷或抹掉。所有主要命令、实际退出码和日志SHA见 `commands.jsonl`。

## 5. 最终门槛逐项回答

| 问题 | R5结论 | 对应证据 / 未测边界 |
| --- | --- | --- |
| D01是否仍PASS | 核心定向回归PASS；完整发布门禁NOT VERIFIED | 本候选KnowledgeSources、KnowledgeConcepts测试通过；生成列真实恢复及规范化CLI集成未另跑 |
| D02是否完整PASS | **FAIL** | 新P1概念卡队列截断 |
| B08是否通过 | **NOT VERIFIED** | 本轮集成套件含部分CAS/幂等/回滚验证，不替代来源追加×自评A–H真实并发及逐值时间线 |
| B09是否通过 | **NOT VERIFIED** | 只读复核有API重启，但没有多次真实自评、事件重放、新CAS推进的完整两次重启矩阵 |
| M03–M08是否通过 | **NOT VERIFIED** | 未运行真实备份恢复/逐DDL-DML-history中断/恢复后续学/导出分类完整门槛；私有dump不是恢复测试 |
| Playwright是否独立通过 | **独立执行，整体FAIL** | 来源分页PASS；概念卡队列FAIL。自评、双Tab、断网、丢响应、空队列/API错误未执行 |
| Node测试是否独立通过 | **PASS** | 36测试及typecheck/lint/build，绑定初始389项与最终392项逐字节无业务变化 |
| 有无未解决P0/P1 | **1个新P1** | QA-D02-R5-FINAL-001；未观察新P0，不据未执行项推断无风险 |
| 个人数据是否保持原样 | 本轮未连接3308，未重启或替换3100/8085 | UUID守卫及新容器记录；没有连接个人库获取前后哈希，不虚构个人数据全量对账 |
| 是否建议关闭10D | **否** | P1阻断且关键并发/恢复门槛未验证 |
| 是否建议进入10E | **否** | 等CORE修复、新冻结候选与QA复测 |

原Demo完整学习闭环、旧Review完整保护和10C-1音频兼容全流程未补齐；只计入本轮实际集成覆盖和9表只读复核。既有归档报告是历史导航，不转为本轮PASS。旧测试计划中来源追加重置排期的描述按现行 `concept_review_v1` 实施协议解释：追加来源不改变排期，只有自评CAS推进。

## 6. 保留现场与交付

- 停止时22张概念卡、104条来源/104个唯一来源Attempt、0条概念评价、111条command_receipt、24条非空location_guard：`final-counts.log`。回执包含核心回归留下的合成记录，不能误称只有104条。
- 本轮3382容器/卷、媒体、数据库、失败日志全部保留。私有逻辑dump在 `.local/qa-final-r5/failure-db-logical-dump.log`，仅导出身份SHA，不包含在交付包。
- API/Web两轮子进程均退出143（主动停止）；browser context关闭。`stop-state.json`、`recheck-stop-state.json`、`qa-ports-after-stop.log`；后者lsof exit1表示8192/3199无监听。
- R4原420文件包归档为 `output/review/northstar-phase10d-r4-archived-evidence.zip`，原/归档SHA完全相同：`727f3996fea44c3ebaa5b6766414e072c00eac6fb470b14f13415d9f1d0d2121`。R4报告原文保存在本轮evidence/history。
- 当前交付路径为 `output/review/northstar-phase10d-final-qa-sanitized-evidence.zip`，附`.sha256`。仅包含冻结源码文本、QA日志/合成数据、报告、截图/轨迹和SHA校验器；排除 `.local`私有内容、数据库dump、密钥、Cookie、个人.env、音频和录音。解压运行 `python3 verify.py`。
- 未提交、合并、推送、部署或开始10E。新P1确认后仅做只读证据保全和报告收尾。
- 交付校验已实际执行：独立解压运行 `verify.py`，exit0；最终392项候选字节复核及R4原包归档哈希复核PASS，`git diff --check` exit0。交付ZIP最终哈希以同名`.sha256`为准，独立校验日志在 `bundle-independent-verification.log`，不在报告内写包自身哈希。

**PHASE 10D FINAL FAIL — STOP FOR CORE FIX.**
