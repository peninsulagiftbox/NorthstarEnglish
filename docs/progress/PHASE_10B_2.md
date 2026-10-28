# Phase 10B-2｜通用多课读取与课程目录

2026-10-28（Asia/Shanghai）。**最终结论：PASS（本地隔离工程验收）。个人主站未迁移/部署；真实设备与正式素材授权不在此PASS内。** 原只读规划报告保留为[PLANNING_REPORT](../handoff/evidence/phase10b2/PLANNING_REPORT.md)；本报告区分历史10B-1、此次实现与个人主站状态。

## 1. 授权、10B-1签收与实际范围

用户后续明确要求“你先自行审核10B-1，并获取签收，签收后自行开始10B-2的开发”。已由独立审查代理 `/root/phase10b1_review` 重新核对原始证据并签收 **PASS_WITH_CONTROLLER_NOTE，B01/B03 PASS**；这是独立代理技术审查，不是人工签名，也不是ZIP打包回执。

[独立审查报告](../handoff/evidence/phase10b2/INDEPENDENT_10B1_REVIEW.md)、[机器签收](../handoff/evidence/phase10b2/INDEPENDENT_10B1_SIGNOFF.json)：实际重算32份备份、7367个原始日志hash、44份快照hash、12角色媒体、升级/空库及5组故障恢复/真实续学/重启。原主控汇总退出1仍保留，未改写成0。原STATUS和final-audit历史字节未修改。

签收后按[计划](../handoff/evidence/phase10b2/PLAN.md)实现通用读取、目录、版本/段句关系、独立句音频、启动只读校验及显式空库初始化。没有教材导入、正式发布/current CAS、稳定身份映射、共享音轨、动态题量、跨课知识或教学编排。完成后停止，不开始10B-3。

## 2. Git与完整变更范围

- HEAD：`98bfedc8ac43ab68aea5447f2790cd3777b0a764`，未commit/push。开发前真实190份文件hash见 `before-development-hashes.json`，Git状态见审计命令记录。
- 起点已有 `ExportController.java`、`scripts/data-transfer.py`、`scripts/tests/test_data_transfer.py` 的个人迁移改动，以及V009.01–.04和旧阶段证据未跟踪。ExportController本轮未再改；data-transfer仅在既有008/009.04支持上追加009.05并补测试，不覆盖前一阶段工作。
- 最终tracked/untracked状态、逐文件SHA-256及本阶段清单由 `delivery-audit.json`、`stage-files.json` 和 `DELIVERY_SHA256SUMS.json`记录。不能以tracked diff遗漏新增文件，也不能把已有个人迁移改动全算成本阶段。

本阶段代码与契约清单（相对仓库根）：

| 领域 | 新增/修改文件 |
| --- | --- |
| Java主代码 | 修改 `apps/api/src/main/java/local/northstar/catalog/{ContentPackage,ContentSeeder,CatalogController}.java`；新增同目录 `DemoContentAdapter.java`、`AudioResources.java`、`CatalogReader.java` |
| SQL | 仅新增 `apps/api/src/main/resources/db/migration/V009_05__lesson_catalog_order.sql`；V001–V009.04原字节冻结 |
| Java测试 | 修改 `catalog/ContentPackageTest.java`、`report/ReportExportIntegrationTest.java`；新增 `catalog/MultiCourseIntegrationTest.java`（均在apps/api/src/test/java/local/northstar） |
| TypeScript/React | 修改 `apps/web/src/lib/api/catalog.ts`、`lib/state/context.ts`、`components/CatalogPages.tsx`、`components/lesson/LessonWorkspace.tsx`；新增 `apps/web/tests/catalog.test.ts`。LessonProvider已有同版恢复/空句/异步退出保护继续复用，无不必要修改 |
| 工具/浏览器 | 新增 `scripts/phase10b2.py`、`phase10b2_isolated.py`、`phase10b2_verify.py`、`phase10b2_bootstrap_check.py`、`phase10b2_audio.py`、`phase10b2_browser.py`、`phase10b2-browser-smoke.js`；修改 `full-learning-loop.js`、`data-transfer.py`、`tests/test_data_transfer.py` |
| 文档/证据 | README、docs/openapi.yaml、本报告、docs/handoff/evidence/phase10b2/；截图仅在output/playwright的新10B2路径 |

应用依赖及lockfile未变。为真实MP3测试在 `.local/phase10b2/audio-tools` 装固定 `lameenc==1.8.5`，仅测试工具；未改变全局Python/Node/Java。实际运行Node22.23.2、Java21.0.12.1、项目原Maven和原MySQL固定镜像。

## 3. 课程读取架构与初始化

- `DemoContentAdapter`保留原Demo包的身份、10句/10音频、四册清单、版本、许可标志、文件名、时长及hash完整性检查。`ContentPackage`保留原调用API，冻结包读取委托Demo适配器，通用音频读取交给独立验证器。没有删除冻结JSON/manifest或改其hash。
- `CatalogReader`按真实lesson/version主键和关系表读取；段落按sequence/id，句子按全课sequence/id排序，验证段落同版及顺序。payload仅提供版本元数据/既有词汇练习，正文句子及段落来自关系查询；核对payload身份与DB一致。没有靠标题、文件名、数组索引推导课程身份。
- 新增V009.05为lesson加可空sequence_no/display_number、正序CHECK和册内唯一排序键。旧独立课保持NULL；未知课次不猜测，以NULL最后/id稳定排序。文件SHA-256为 `8b32932f9447faf37a27dd449eb11106130d20637c887ce0bd0b8d2f5bdefa32`。
- 普通ContentSeeder入口只读验证，不补词条/题/任务，不写book或current。缺失/篡改拒绝启动而不静默修复；不再全局要求“只有4册/10句”。Demo自己的数量检查仍存在。
- 一次性初始化需显式 `--northstar.initialize-content=true`，锁项目行，要求内容及学习表为空，事务中先段落后句子，首次设置Demo current。已有/部分初始化库拒绝，不补写。README给出无Web一次性命令，已在全新隔离restore schema实际运行退出0；重复调用退出1，全38表逐值未变，见 `nonweb-bootstrap.json`。
- 最新schema空库直接从V001迁移，再显式初始化；没有沿用10B-1“V008先播种”的结果冒充新路径通过。普通启动仍保留既有Flyway机制，因此本阶段测试均在专用实例，不能把启动个人Spring当只读检查。

## 4. 新旧API契约

| 接口 | 本阶段行为与兼容 |
| --- | --- |
| GET /api/v1/books | 保持books对象和standaloneLessons字段；独立课严格book_id为空。册的actualLessonCount/availableLessonCount按真实行计算，declaredLessonCount只作元信息。四册仍catalog_only，未生成348个假课程 |
| GET /api/v1/lessons | 保持原数组；查询实际可读取的当前版本，不改成分页对象 |
| GET /api/v1/books/{id}/lessons?cursor&limit | 新items/nextCursor对象，limit默认20、1..100；book绑定游标，sequence NULL最后/id做稳定keyset。静态目录不重漏，不承诺并发发布快照；未知册404，坏游标/limit400 |
| GET /api/v1/lessons/{id}?versionId=... | 保留旧字段和去答案规则，追加projectionVersion/paragraphs/paragraphId/实际任务能力。当前和显式历史版本均可读；未知课或不可开放课404，未知版404，已知跨课版422 |
| GET /api/v1/lessons/{id}/versions | 新versions列表，versionId/number/isCurrent/readable；按实际版号/id排序，不虚构未实现的发布生命周期 |
| GET /api/v1/audio/{id} | DB资产关联清单、所属课/版访问边界和来源状态；未知/不可开放404，缺文件/坏hash503；200/206/416保持。新课路径无需Demo命名 |

旧Demo的pending_review/releaseReady=false本地例外只保留给Demo；其他未确认来源、draft/withdrawn不能通过新读取器/音频端点访问。册内不可学行仅给目录元信息，不给正文/媒体或可学版本入口。未引入10B-3发布写入接口。

**兼容选择**：本阶段保留“音频缺失导致整课503”，前端明确资源失败与重试。文本/媒体分离降级留10C；未单纯删除旧503负例。原ReportExportIntegrationTest将schema负例从写死008改为实际当前版本，保留真实异schema拒绝。

## 5. 前端与音频

真实册卡可展开实际课程、下一页、空态和失败重试；独立Demo与独立原创课另列。已有可读课程的测试册不误标“暂不可学习”，四册零内容仍明确仅目录。继续入口按真实resume课/版验证，不从独立课数组猜测册内恢复点。

工作台标题、来源和版本入口来自实际课程。段落有序显示，保留六Tab、224px侧栏、原主学习区/助教布局、76px播放器。通用切版回目标版首句并提示，不伪造跨版句身份或迁移成绩；仅原冻结Demo保留已核对的v1/v2后缀兼容规则。无听写/写作/测验定义时显示明确空态，不制造完成记录。

音频路径拒绝绝对路径、空路径段、`.`/`..`、编码/反斜杠和越界软链接；realpath必须位于允许root；验证实际大小及流式SHA-256。Demo原独立音频不改。所有应用和媒体测试使用独立目录，不写个人录音。

## 6. 真实隔离样例

| 内容 | 版本 | 每版段落 | 每版句子/独立音频 | 归属 |
| --- | --- | --- | --- | --- |
| 原Demo01 | v1、v2 | 1 | 10 / 10 | 独立，原包不变 |
| 原创样例A | fixture-a-v1、v2 | 2 | 12 / 12 | 原创测试集合，显式课序7，展示号A |
| 原创样例B | fixture-b-v1、v2 | 3 | 24 / 24 | 独立原创测试课 |

新增共4版、10段、72句及72独立音频资产；连同Demo共6版/12段/92句。另有4个真实draft元数据行（课序1/2/3及未知NULL）验证分页和不可学状态；不是教材占位课。四册各实际0课/可学0课；测试集合是第五个独立测试book，不将A/B或Demo塞入四册。

文本为本阶段自编；测试音频是自编440Hz数学波形，经LAME编码成真实MP3并由afconvert解码为PCM；浏览器实际播放。72资产使用独立路径引用同一自编测试波形字节，**不是72段朗读或教材音频**，不证明语音、对齐或发音质量。界面明确“原创合成测试音·非朗读/非发音示范”。受限于当前枚举使用original_demo/original_tts测试分类，不作为正式发布类型或内容导入流程。音频记录见 `audio-fixture.json`。

## 7. 实际命令、退出码和结果

精确argv/cwd/UTC时间/Git SHA/日志SHA见 `execution-commands.jsonl`；隔离SQL/Flyway/PID/UUID及退出码见 `migration-execution-20261028b/commands.jsonl`、各分项及后续命令文件。共用源码HEAD不代表工作区已提交，源码字节另见交付清单。私人旧行值和凭据只在.local受控快照/原始日志，不进公开证据。

| 实际命令（从项目根执行） | 结果 |
| --- | --- |
| python3 scripts/phase10b2.py sync | 0；只同步独立构建副本，主站target/.next不动 |
| phase10b2.py run ... npm test | 0；最终27条Node测试通过 |
| ... npm run typecheck / lint / build | 各0；最终生产构建通过，使用隔离API端口 |
| ... apps/api/mvnw -f apps/api/pom.xml package（无DB变量） | 沙箱内1（Mockito自附加限制），沙箱外0；早期8个DB门控跳过不算通过 |
| python3 scripts/phase10b2_isolated.py migrations | 新b批次实际0；V008备份→009.04→009.05、最新空库链/初始化、DDL后故障和新目标恢复四路径PASS |
| python3 scripts/phase10b2_verify.py integration | 0；实际隔离MySQL基础回归21条（含新增资源负例）、MultiCourse1条均通过，零跳过/失败/错误；Maven verify包含编译、测试及打包 |
| ... python3 -m unittest discover -s scripts/tests -v | 沙箱内1（ps/TCP权限）；沙箱外0，15条通过 |
| .local/phase10b2/audio-tools/bin/python scripts/phase10b2_audio.py | 沙箱内CoreAudio失败1；沙箱外0，真实MP3解码通过 |
| python3 scripts/phase10b2_browser.py phase10b2-browser-smoke.js | 浏览器多课、目录/版本、实播、空态/失败重试、1280响应式；结果见最终CLI日志，passed=true |
| python3 scripts/phase10b2_browser.py full-learning-loop.js | 0，passed=true；Demo实际听写/阅读、幂等重试、两版作文、错题测验/复习、草稿刷新、键盘和跳过不计完成 |
| python3 scripts/phase10b2_verify.py final-protection | 0；最终JAR两次普通重启前后38表逐值、全部测试媒体一致；旧备份升级/恢复目标最终JAR复验一致 |
| python3 scripts/phase10b2_bootstrap_check.py | 0；无Web空库初始化0、重复初始化1（预期拒绝），全表未变 |
| git diff --check、文档/工具语法及证据完整性检查 | 0；交付审计核对4,888份原始日志hash、冻结迁移/内容/依赖、秘密扫描、端口和6个隔离容器实际停止状态；不当作应用功能测试 |

真实失败和修正逐项保存在 `failure-events.json`；旧失败日志不删、不改退出码。首轮工具就绪竞态、Next入口路径错误、浏览器B路由等待错误均已修正并实际重验；没有通过删负例迎合实现。全闭环中册卡从“无任何控件”改为“可看真实空目录但无假学习链接”，是目录契约变化；保留四册身份、空册无学习链接断言并新增独立多课负例。截图路径改为10B2新目录，不覆盖09-R历史。

## 8. 数据与运行保护

- 新资源仅在本阶段命名空间，DB端口3350–3353，测试API/Web8131/3151；创建前拒绝已有资源，核对完整容器ID/标签/绑定/卷/UUID，明确拒绝源UUID及3308/8085/3100。
- 以旧受控V008备份在新目标恢复验证；不从当前个人库写入测试事件。新增DDL只应用隔离目标，未改V001–V009.04或repair/history/关闭FK/清卷。
- 旧列逐PK逐值、媒体hash、Demo v1指针保留及重复启动见四路径报告；含新样例和真实学习测试记录的38表再经最终JAR两次重启全值一致，见 `final-data-protection.json`。既有录音登记/媒体、作文父链、听写/阅读/测验/复习数据无普通启动改写。
- 个人主站仍使用旧已运行构建及009.04，本阶段没有迁移、停服务或部署替换。当前个人库全量逐值未重取，不声称运行期间用户没有自行写入；保护结论依据隔离身份门禁、实际命令和最终运行核验。
- 新建容器/卷和失败副本保留；只停止本阶段服务，最终实际状态见 `delivery-audit.json`。没有删除个人库、卷或媒体。

## 9. UI与截图

使用Playwright及ui-audit技能：1440×900工作台测得侧栏224px、播放器76px、六Tab；1280×800无横向溢出。已查看真实截图，沿用原色彩、组件、字体和主区/助教布局，没有视觉重构。长内容仍用原主区滚动；截图不证明声音质量。

- `output/playwright/phase10b2-workspace-top-1440.png`
- `output/playwright/phase10b2-catalog-1440.png`
- `output/playwright/phase10b2-lesson-a-1440.png`
- `output/playwright/phase10b2-lesson-b-1280.png`
- `output/playwright/phase10b2-demo/`：原Demo闭环各阶段截图。

多课浏览器检查中的503是路由注入来验UI提示/重试；后端真实坏hash、越界、缺文件及不可访问资产另有Java真实DB/文件测试，不将注入当真实媒体损坏测试。浏览器pageErrors均空；预期的网络/503失败在console可见，不能称console零错误。

## 10. 未执行、限制与人工审查

- 真实麦克风、扬声器人工实听、其他浏览器/另机安装：NOT VERIFIED。本轮Demo浏览器口语只验证显式skip，不计practiced；旧录音API/存储/回放证据由Java集成及媒体保护覆盖，不冒称实体设备通过。
- 新样例只有读取/播放测试内容，无完整教学计划/正式课程发布；合成测试音非朗读，不证明学习效果。Demo原素材正式发布授权仍待原流程，未解锁公开分发。
- 同时发布导致目录变化的分页快照不在此阶段；静态目录keyset已测。内容发布/current CAS、跨版本身份与学习迁移留10B-3。
- 缺音频继续整课503是保留契约；更细的文本降级需10C另验。普通运行没有新增AI/ASR或评分。
- **现有个人库尚未应用V009.05，主站未加载本阶段代码。** 应另行批准个人库升级/部署后再停写、备份和验证，不直接在主站重启新JAR触发迁移。

需人工审核：此次代理技术签收边界；可空排序/展示课号及稳定分页；显式空库初始化与缺失拒绝而非修复；跨课版本422；保留缺音频整课503；测试音仅作功能夹具。批准本阶段不意味着批准这些后续个人库操作。

## 11. 10B-3准备与停止点

已具备真实多课/多版/段句读取、目录入口、安全独立音频和普通启动零current覆盖基线。10B-3仍需独立设计/迁移演练，实施身份登记/映射、枚举扩展、发布生命周期和current CAS；不得沿用V009.05演练PASS默认放行新DDL。

本阶段完成后停止，不自动开始10B-3，不自动提交Git或部署主站。

## 12. 最终验收矩阵

| 条目 | 结论 | 直接证据 |
| --- | --- | --- |
| 10B-1前置签收 | PASS_WITH_CONTROLLER_NOTE | INDEPENDENT_10B1_SIGNOFF.json，原主控1保留 |
| 两课不同句数/段落、各两版及同版关联 | PASS | MultiCourseIntegrationTest真实DB、浏览器多课passed=true |
| 四册真实0内容与独立课/册内课、稳定分页和访问负例 | PASS | Java真实DB负例、最终多课浏览器日志 |
| Demo01与学习记录兼容、跳过不等于practiced | PASS | 基础Java21条及Demo浏览器完整闭环；旧缺媒体负例保留 |
| 普通启动零current覆盖/零内容补写、显式空库初始化 | PASS | 四路径演练、nonweb-bootstrap.json、final-data-protection.json |
| 通用独立句音频、安全路径/完整性、Range及实播 | PASS | Java资源/范围测试、真实解码audio-fixture、浏览器播放器 |
| 编译/类型/lint/build、Node/Python/Java集成 | PASS | 实际Node27、Python15、Java22条；全部集成零跳过；对应命令日志 |
| 原始证据与隔离资源保护 | PASS | delivery-audit.json：4,888份raw hash通过、6目标exited/卷保留、测试端口无监听、主站009.04/原JAR不变 |
| 实体麦克风/人工实听/其他浏览器/另机 | NOT VERIFIED | 明确未执行，不并入工程PASS |
| 正式教材/语音素材授权及个人库新版本部署 | NOT VERIFIED / 未执行 | 本阶段未导入/发布/迁移个人库；须另行批准 |

人工审核本报告及所列技术决策后再确定后续阶段。此次已完成授权范围，停止于10B-2交付。
