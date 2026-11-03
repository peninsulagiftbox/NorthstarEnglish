# Phase 10D-2 QA-EXEC R4 最终封版验收

> 2026-11-02 R5再次封版验收已完成：本报告的卡内来源分页P1已独立复测关闭，但发现新P1“概念卡队列超过20条无翻页入口”。当前仍FAIL，详见 [R5最终报告](10D_D02_QA_R5_FINAL.md)。以下保留R4历史，原R4证据包已归档为 `northstar-phase10d-r4-archived-evidence.zip`。

日期：2026-11-02（Asia/Shanghai）。角色：独立QA。结论：**FAIL — 新P1 QA-D02-R4-FINAL-001，停止封版，不建议关闭10D或进入10E。**
补记（同日晚）：经用户授权实施前端修复后，第6节的定向复测PASS；冻结候选的FAIL结论与未验证门槛不变。

## 1. 同一候选身份与范围

- 实际 HEAD/分支：`a5084cb4442a7b78afad5c920459c22f02f679ce` / `main`。工作树原有大量未提交/未跟踪D01/D02输入均保留。Git状态：`qa/phase10d-final-r4/evidence/git-status.log`。
- 最终完整清单：`qa/phase10d-final-r4/evidence/qa-final-candidate-manifest.sha256`，**385项**，SHA-256 `ae4fb16befec1dcb25699f084d7582f49ab118cacdd7bf70bf0c65af34fd3784`。覆盖Java/TS、迁移、测试、fixture、OpenAPI、data-transfer、脚本和构建配置/锁文件，以及本轮实际使用的原创音频与Demo输入哈希。未把未跟踪文件漏出候选。
- 原P1 336项输入清单 `31131ea6b5a92b87ff12d32e61ad6fef9896e2028d16ecba5b7e9368f60b1a6c` 的每项当前字节、测试副本字节均一致：`p1-336-input-binding.json`。最终385项也与构建副本逐项一致：`candidate-binding-final.json`。中途仅修订QA工具/扩大运行fixture清单，未改业务输入，历史工具版清单身份保留在命令日志；不将不同业务候选混作同一候选。
- 真实HTTP JAR：`output/review/northstar-phase10d2-p1-candidate.jar`，SHA-256 `771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6`。
- 独立重建JAR：`92e707473265e6cee3b151ada104f41e7754b39966cc6484d853130c5d79d6ac`；124个应用class/resource条目与运行JAR字节完全一致，差异0：`core/jar-rebuild-comparison.json`。
- 独立Web BUILD_ID：`-npvkMs_s7of_JgI9yxq7`，代理8191；Node `v22.23.2`，npm版本见 `npm-version.log`；Java `21.0.12.1`，MySQL `8.4.9`。未修改全局Node/Java。
- 最新合法Flyway `012.11`；`012.08/09/10/11` 校验和分别为 `614772575/-1897723092/1214340811/747985570`，均success。全历史见 `flyway-history.log`、`core/flyway-history.log`；SQL与SHA见 `migration-inputs.json` 和源码清单。未repair/clean、未改旧迁移。
- 核对真实 `ConceptReviewController.sources()`：受限字段裁剪前保存nextCursor；合法occurrence游标允许1–36位id。API修复仍在候选。10C-2-R1源码与报告回归仍在；data-transfer动态剔除GENERATED列的实现仍在，但本轮真实恢复未执行。

下文证据短路径均相对 `qa/phase10d-final-r4/evidence/`，源码/截图另注明。历史状态分类见 `history-status.md`，不把历史通过算作当前通过。

## 2. 新阻断缺陷：QA-D02-R4-FINAL-001（P1）

**混合权限来源超过20条时，前端只展示第一页且无继续加载入口，后续合法来源无法回溯。**

真实环境：容器 `northstar-qa-final-r4-20261102`，ID `5cf01895ef81d5056cbff6f96e2ad656d87f216ac5182027fa9ce572e93a6212`，端口3380，UUID `7da41d23-d6ab-11f1-b67f-f6c0385d516f`，schema `northstar_phase01_test`；独立账号app/migrator、卷与挂载见 `database-identity.json`、`container-mounts.log`。API8191/Web3198仅回环，隔离媒体 `.local/qa-final-r4/content` 与 recordings。

准备：复用冻结套件的原创A/B课程和合法登记，**通过真实API完成83次错误Attempt**，形成一张金融bank卡、83条完整来源（A82/B1，不直接INSERT Attempt）。在本轮合成库将课A撤回。事件与关系见 `83-source-fixture.json`、`http.jsonl`、`failure-db-key-values.json`。

最小复现：

1. 在上述保存的目标启动冻结JAR与已构建Web；打开 `/review`，选择“全部概念卡”。
2. 展开金融bank卡 `d3d3c982-4bd9-4780-a3ac-1c024a1f9a21` 的“学习来源”。
3. 默认API每页20条，沿nextCursor连续5页返回 `20+20+20+20+3=83`，全部200，83个唯一来源，82受限/1可见；受限字段均符合白名单。
4. **DOM实际仅20条受限来源，0条可见链接；缺63条。** 唯一可见课B来源在后续页，页面显示“学习来源（0 条可见）”，无法访问该合法练习。卡片内无加载下一页按钮。
5. 刷新队列、切换全部卡片后重新展开，仍是20条/0可见，未恢复完整来源。

证据：`browser-result.json` 逐项记录API页、DOM、按钮、请求/状态；`browser-tool-result.log`；截图 `output/playwright/phase10d-final-r4/sources-truncated.png`；轨迹同目录 `sources-truncated-trace.zip`。全新Playwright browser context，1440×900，结束已关闭。没有未捕获pageerror；记录4条导航/预取 `net::ERR_ABORTED`，原样保留，不宣称networkErrors=0。MCP没有进程退出码：工具正常返回 **assertion FAIL**，没有虚构exit=0。

根因：`apps/web/src/components/review/ConceptReviewCard.tsx:31` 只将首次返回的 `page.items` 放入state，忽略 `nextCursor`；`apps/web/src/lib/api/conceptReviews.ts` 的函数虽支持cursor，界面没有继续请求。summary从已载入第一页过滤计数，进一步误显示总可见来源。

严重性依据：既有QA缺陷定义P1=功能断裂。本例让83来源中的63条不可达，并完全遮掉唯一合法可见来源，直接违反本轮场景A/C的“列表完整、合法回溯”。**不是服务端原分页500/422复发，也未将受限来源身份/数量显示本身当作泄露。** 已关闭的旧缺陷保持关闭。

给CORE的最小建议：消费nextCursor，提供可继续加载/逐页浏览并稳定合并去重；使可见计数含义明确，与服务端visibleSourceCount一致；保留现有受限字段白名单与授权规则。加真实浏览器回归：83混合来源、合法可见项在第一页外、加载至终点无重复遗漏；CORE修复后新冻结候选，QA重测受影响范围。**QA本轮未修业务。**

## 3. 实际执行与失败记录

| 项目 | 本轮实际结果 | 原始证据 |
| --- | --- | --- |
| Node `npm run test` | exit0，36/36，0skip | node-test.log |
| Node `typecheck` | exit0 | node-typecheck.log |
| Node `lint` | exit0；原有busy未使用warning1，无error | node-lint.log |
| Node `build` | exit0，独立构建标识如上 | node-build.log / web-identity.json |
| Java D02/D01/10C-2-R1 + KnowledgeConcepts | 新3381库11/11，0失败/错误/跳过，exit0 | core/java-regression-correct-origin.log |
| 规范化集成 | 首轮3380真实执行1/1通过；该轮整体仍失败，未掩盖 | java-regression.log |
| Maven package | exit0，隔离target，无覆盖个人运行构件 | core/java-package.log |
| 新库迁移 | 3380/3381从空schema经真实候选初始化至012.11成功 | initialize.log / core/initialize.log |
| 本轮83来源API连续分页 | 5页全部200、83唯一、82/1权限字段正确 | browser-result.json |
| 本轮83来源浏览器列表 | **FAIL，20/83，缺63** | browser-result.json / screenshot / trace |

独立QA历史所称“Node四项”经原执行记录确认即typecheck/lint/test/build，不是四个另命名脚本；本轮逐项按真实package入口执行。

保留失败：首轮Origin环境3198与套件固定3196不符，D02/D01请求403，整体12项中2fail（exit1）。修正仅QA运行环境后，D02等通过；规范化套件首轮留下norm-*记录，第二轮导致自身DuplicateKey及D01全量集合断言受污染，整体exit1，仍保留3380现场。另建3381，避免改断言或删除既有现场，最终核心11项全过；规范化未再宣称复跑通过。详情 `java-regression.log`、`java-regression-correct-origin.log`；工具启动失败见 `tool-launch-failures.json`。无修复业务或改迁移强行通过。

最终数据库读取：本复现金融卡rowVersion=1/reps=0、83个不同attempt来源/1卡、概念评价0；总command_receipt=95（包括本轮套件其他合成事件，不误称只83）、location_guard非空4行。全部关键字段已保存；仅做保存现场的私有逻辑dump，**不是M03/M04恢复试验**，不算恢复通过。

## 4. 最终门槛逐项回答

| 问题 | 结论 | 证据/限制 |
| --- | --- | --- |
| D01是否仍PASS | 本轮D01来源、不可变快照、V012_08负例和规范化定向回归PASS；完整D01发布门禁未重跑，不能扩称整组最终PASS | 上述独立Java日志；生成列恢复等未跑 |
| D02是否完整PASS | **FAIL** | 新P1前端来源不可达 |
| B08是否通过 | **NOT VERIFIED** | D02既有套件部分CAS用例通过，不替代本轮A–H真实来源追加×自评并发时间线 |
| B09是否通过 | **NOT VERIFIED** | 未执行两次重启/全字段重放与新CAS推进矩阵 |
| M03–M08是否通过 | **NOT VERIFIED** | 真实有数据恢复、逐DDL/DML/history/备份恢复中断与恢复后续学均未执行；停止门禁 |
| Playwright是否独立通过 | **独立实际执行，FAIL** | 新context真实请求/DOM/trace；仅完成来源场景便触发P1停止，自评/双Tab/断网/丢响应/错误/空队列等不冒称通过 |
| Node是否独立通过 | **PASS，四项** | 36测试+typecheck/lint/build实际exit0 |
| 有无未解决P0/P1 | **1个新P1，未解决** | QA-D02-R4-FINAL-001；未观察到新P0，但未执行项不能据此排除全部风险 |
| 个人数据是否保持原样 | **本轮没有访问/写入个人3308，也未重启3100/8085** | 所有DB运行器仅新3380/3381并绑定UUID；未连接个人库做前后值比较，不伪称有个人全库哈希证据 |
| 是否关闭Phase10D | **否** | P1阻断，且B08/B09/M组未验证 |
| 是否进入Phase10E | **否** | 等CORE修复、新冻结候选和QA受影响复测 |

原Demo完整闭环、旧句卡完整保护、10C-1音频基本回归未在本轮独立补全；集成套件已有的局部旧卡/quiz检查仅按其实际范围计入。未执行240次声学采集。旧候选的通过不迁移为本轮通过。

## 5. 保留物、交付与停止

保留新3380失败目标、新3381核心回归目标及卷/媒体；此前3348/3349、3364及CORE目标均未连接/清理。专属API/Web子进程已停止，浏览器新context已关闭：`owned-processes-after-stop.log`/`qa-ports-after-stop.log` 中exit1表示无对应PID/监听，非业务测试失败。未自动提交/合并/推送/部署，未开始10E。

证据包：`output/review/northstar-phase10d-final-qa-sanitized-evidence.zip`，附`.sha256`。白名单含冻结源码文本/迁移、当前实测日志、明确未测矩阵、最小复现/DOM/截图/trace、独立校验脚本；排除`.local`内容、数据库dump、env、凭据、Cookie和所有音频/录音。清单仍记录实际音频输入哈希，未把私有媒体复制入包。解压执行 `python3 verify.py` 校验交付内全部文件；省略的运行输入不会伪称已随包提供。

**PHASE 10D FINAL FAIL — STOP FOR CORE FIX.** 本报告按新P1即停规则结束本轮，无开发或部署授权扩展。

交付校验：白名单420个文件已实际独立解压并运行verify.py通过（exit0）；git diff --check通过（exit0）。证据包最终SHA-256以同名.zip.sha256为准，避免包内报告自引用哈希。

## 6. 修复复测补记（同日晚，用户授权"解决新缺陷"）

修复内容（仅工作树 `apps/web/src/components/review/ConceptReviewCard.tsx`，API/JAR/迁移未动）：消费`nextCursor`逐页加载；按`attemptId:occurrenceId`用Map去重合并并保持顺序；summary改为"已显示 X/Y 条可见"（X为已载入可见数，Y为服务端`visibleSourceCount`）；提供"加载更多来源"按钮与读取中/失败重试状态。

复测环境：同一冻结JAR（SHA-256 `771a72e8…`）与同一3380库（UUID `7da41d23…`）不变；Web由修复后工作树以`API_PORT=8191`重建，BUILD_ID `dfgGpBMsE_A5ulue2ALhf`。复测首次启动失败的原因是既有`.next/routes-manifest.json`在构建时固化8085代理，`next start`不重读环境；`fix_stack.py`增加重建步骤后纠正，`fix-web-build` exit0已入册，`fix-runtime.json`记录栈身份。上一会话遗留的8191 API进程经lsof确认cwd为`.local/qa-final-r4/source`（QA隔离副本）后由本会话接管终止，两处`stop-owned-child`见`commands.jsonl`。

复测结果（`fix-browser-result.json`，截图 `output/playwright/phase10d-final-r4/sources-fixed.png`）：**PASS**。全新browser context展开同一金融bank卡，点击"加载更多来源"4次共读取5页（20×4+3=83），DOM渲染83/83（82受限+1可见），summary显示"已显示 1/1 条可见"，加载按钮消失；5次sources请求全部200且游标推进。5条`net::ERR_ABORTED`为导航/预取中止，原样记录，不计为页面错误。修复后静态检查`fix-node-test`/`fix-node-typecheck`/`fix-node-lint`均exit0（build即`fix-web-build` exit0）。

边界与不变结论：修复代码尚未构成新冻结候选（385清单与P1 336绑定仍对应修复前字节）；B08/B09、M03–M08、双Tab/断网/自评矩阵仍未验证。QA-D02-R4-FINAL-001在复现环境中的缺陷表现已消除，但正式关闭仍需冻结新候选、复测受影响范围并补齐剩余门槛。修复验证证据单独打包为 `output/review/northstar-phase10d-fix-verification-evidence.zip`（附`.sha256`，解压运行`python3 verify.py`校验）；原420文件FAIL包保持不变。
