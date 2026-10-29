> 后续部署（2026-10-29）：用户确认审核通过并授权提交GitHub及本地部署，个人库现已升级009.15，见[部署报告](PHASE_10B_3_DEPLOYMENT.md)。下文未迁移/未部署为开发验收阶段的历史范围。

# Phase 10B-3｜稳定身份、版本映射与显式发布

日期：2026-10-28–29（Asia/Shanghai）。结论：**建议 PASS（已测本地隔离工程范围），提交人工独立审核；不代表个人库部署或正式教材授权通过**。用户先批准计划再实施，额度中断后按原授权继续；没有扩大到个人库迁移、部署或10C。

## 1. 基线、范围与原有修改

- HEAD：`e5963bae8766194a32cd00703cd64a7ed2e52d46`。未自动commit/push。
- 起点已有 `globals.css`、`CatalogPages.tsx`、`LearningReport.tsx` 及两组UI报告/证据；三份源码与实施前保存hash逐字节一致，全部保留，不将其算作10B-3开发。
- 已复核10B-1历史签收、10B-2实际源码/SQL、部署与专项回归证据。起始个人健康与只读history为009.05、Demo current=demo-01-v2；10B-1原主控退出1仍保留。本阶段没有将旧演练PASS当新DDL的通行证。
- 完成A–F：句/段身份registry、跨版映射、独立生命周期/就绪度、显式校验发布/撤回/CAS/审计、类型扩展、读取/前端最小适配、新表备份恢复和隔离验收。未实现PDF/OCR、共享音轨、动态题量、跨课知识或完整教学计划。

## 2. 文件范围与关键设计

| 范围 | 文件及变化 |
| --- | --- |
| 核心业务 | 新增 `apps/api/src/main/java/local/northstar/catalog/{ContentIdentities,ContentPublication,ContentPublicationCli,VersionAccess}.java`；修改同目录CatalogReader/CatalogController/ContentSeeder |
| 学习访问 | 修改StudyController、ExerciseController、QuizReviewController、PracticeCommands、WritingController、RecordingController和ApiProblems；事务内版本门禁、历史读取和原事件回执重放分别处理 |
| SQL/资源 | 新增V009.06–.15及 `apps/api/src/main/resources/catalog/demo-identities.json`，已有paragraph不重建 |
| 前端 | 修改 `apps/web/src/lib/api/catalog.ts`、`lib/state/context.ts`、`components/lesson/LessonWorkspace.tsx`；增补catalog/context测试。无新的依赖、视觉系统或Tab/播放器重构 |
| 测试与工具 | 新增ContentPublicationIntegrationTest/IsolatedMigration；适配MultiCourseIntegrationTest显式身份/发布夹具；新增scripts/phase10b3*.py/js；修改data-transfer.py及其测试 |
| 契约/文档 | docs/openapi.yaml、README、已批准计划、本报告、phase10b3证据入口及.gitignore私有证据规则 |

依赖及锁文件未改；沿用项目级Java21/Node22/MySQL8.4与既有Flyway，不更改全局运行时。

## 3. 身份、映射与学习证据

`sentence_identity`和`paragraph_identity`以UUID/opaque ID登记，每条身份只属于一个Lesson。实际句/段保留物理PK，新增identity引用；唯一 `(version,identity)` 与复合FK拒绝跨课及版本内重复。paragraph同时绑定同课的version和identity，原句→同版paragraph外键保留。

Demo采用显式物理ID→UUID清单确定性回填，原20句、2段、全部练习/历史引用不重建。v1/v2的配音不同；本阶段保守独立登记，不依据stable_key/序号/后缀推导equivalent。新课夹具验证同逻辑身份可跨版复用，排序和物理ID独立。

version_sentence_map保存双端课/版/句、关系、组、reviewer、confirmation_source、reason及确认时间；同课复合FK和组服务共同约束。真实夹具含equivalent 1条、edited 1条、split 2条、merged 2条、no_target 1条；删除使用NULL目标且显式no_target。组确认事务化、追加不可覆写；非法基数/跨课、确认关系NULL及无目标重复均被拒绝。人工角色是明确的合成审核夹具，不伪造真人签名。

原版真实听写correct/practiced和复习自评留在原物理句/版；映射之后新版本的attempt/stage/review均为空。另以真实旧作答验证equivalent参考提示，UI显示“仅作参考，不代表新版已掌握”，新版仍not_started。无确定映射、拆合及无目标均回新版本首句，不猜ID前缀、不复制草稿或成绩。

## 4. 生命周期与显式发布

publication_state=draft/validated/published/withdrawn；content_readiness=legacy_unassessed/basic_content/teaching_complete，与许可release_ready分开。原Demo两版为published+legacy_unassessed，原release_ready=false、pending_review、local_test_only及原payload/content/manifest/media字节不改；这不是新的正式素材授权。

新版本默认draft，独立validate检查支持的本地基础profile、原包/manifest字节hash、正文投影、段句顺序、独立音频清单/文件/区间、既有答案合法性及文本/每项音频来源证据，冻结带算法标识的关系快照；成功才validated。内容变动必须新版本；published不能原地重校验覆盖。teaching_complete及未支持教学/共享音轨字段拒绝。`northstar.local.basic.v1`只是当前门禁，不冒称10E完整core-v1或10F验证器。

publish请求显式携带operationId/课/目标版/expectedCurrent/hash/actor；锁Lesson→版本→许可并复验，NULL安全CAS更新current，状态/current/成功审计同事务提交。旧版仍published可继续学习。相同operation+payload重放原结果，异payload冲突；业务拒绝保存失败结果，不动current；SQL意外失败先回滚，再独立记录PUBLICATION_ROLLED_BACK。数据库不可用时不假称审计已写入。

withdraw是显式、幂等事务：撤回current同时清空current，撤回历史版不影响其他current，不自动选择替代版，不删除历史。新学习命令及课程媒体返回VERSION_WITHDRAWN/410；原成功event同payload仍重放，历史作文/草稿/录音/结果保留。旧课程撤下或来源不可用的音频404保留，不与具体版本撤回混淆。

独立CLI不启动Spring、Flyway、播种或录音reconcile。隔离专用发布账号只有内容SELECT、必要生命周期/current列UPDATE和验证/审计INSERT；真实负例证明不能更新正文、学习数据或CREATE TABLE。普通应用没有新增内容写权限，无公网发布接口。

## 5. 新增迁移、对象与恢复边界

所有V001–V009.05与HEAD字节一致；V009.06–.14首次执行后冻结。复查发现MySQL CHECK接受UNKNOWN及UNIQUE中NULL不判重，故**另追加V009.15**，没有修改已执行V009.10。

| 文件 | SHA-256 |
| --- | --- |
| `V009_06__content_identity_registries.sql` | `6a849bc0fbcf51f74f3e3e26affe1030b260c0ffd17020f2d8a217b63e947b7c` |
| `V009_07__identity_context_columns.sql` | `4c6e6ea186b7802a8bd372b9b70dc726aea6776a820ea3353053d6f7006e9979` |
| `V009_08__legacy_identity_registration.sql` | `2f6fcba0e46bed07341e486ed05456460e87ba88a331991c65c504aa08840fc0` |
| `V009_09__identity_context_constraints.sql` | `e48f4a5a81faa21b6ba124799688e63f21d343a402b1b253c4bbd66914583c35` |
| `V009_10__version_sentence_mapping.sql` | `1b3f522c824b219da270f140d587b4440392bdbf22df590fa019ec55a45aad6f` |
| `V009_11__version_publication_lifecycle.sql` | `17276f3044bf36e7d7e61615ab1a3fb68a884dc59274b5cdbd9eec12dacd3e4b` |
| `V009_12__publication_validation_and_audit.sql` | `cf1fd67964cad5b9e4f590fe83550d5d55838105cde40060b0ca43e3f426fed7` |
| `V009_13__original_lesson_kind.sql` | `45d6e47a7a4e52f8804eb0ddd3252578d8e8cb48c33696480b4bdcb29e0c27da` |
| `V009_14__original_recording_source.sql` | `da9fb5b91c4319599e2bb822940cb52ba9689aa135660776443566541e2c900f` |
| `V009_15__mapping_null_safety.sql` | `73495895722f471dcb82e91d5b11348ac4e5a41d1cf0d2d69d89a747b5c9defd` |

共新增5表：sentence_identity、paragraph_identity、version_sentence_map、content_validation、publication_audit；最终共43表。真实DDL/列/主键及FK见本地证据schema.sql/schema-summary.json，全部保留原上下文FK，无级联删除。审计请求ID不设到目标版本的FK，以便记录未知/跨课请求的拒绝结果；合法current仍受原复合FK保护。

| 单元 | 前置/后置及中断识别 |
| --- | --- |
| .06 registry | 核对旧基线与对象不存在；后置两表PK/UQ/Lesson FK；创建残留以实际table/constraint识别 |
| .07 context列 | registry存在、原列未加；句/段可空上下文列；实际演练第一条ALTER提交后第二条未执行，history仍.06 |
| .08 回填 | 固定Demo物理清单、可空列；后置22条登记与全部旧值不变；事务中注错后行值完全回滚、DDL保留 |
| .09 上下文约束 | 登记完整且无NULL/跨课/重复；NOT NULL/UQ/复合FK；不认识的历史内容不猜身份，须先登记而非强行回填 |
| .10 map | 句上下文键存在；双端复合FK与组服务；跨课/错误基数和无映射负例 |
| .11 lifecycle | 冻结旧版及无同名字段；旧Demo明确投影published/legacy，其他新内容draft；不改原hash/许可 |
| .12 validation/audit | 版本表已扩展；两张有PK的新增表、验证算法CHECK及审计唯一operation；业务回滚与DDL故障分开 |
| .13/.14 CHECK | information_schema实际名称/表达式核对；新旧合法值均保留；CHECK提交后中断、history INSERT权限失败均实际识别并保留目标 |
| .15 NULL安全 | .14完整且无非法映射；显式非NULL关系、生成唯一键；最新空库与恢复副本通过；DDL已提交而history未登记故障亦实测 |

DDL不能整体事务回滚。升级、空库、故障、恢复使用新命名容器/卷/账号/媒体，核对标签/回环端口/卷/UUID并拒绝个人UUID/3308。固定V008备份32文件大小/hash重算通过；V008恢复→009.05→新增单元及最新V001→009.15→显式初始化均实测。每步history/迁移hash留证；没有clean、repair、改history或覆盖旧目标。

已有个人数据保护结论针对受控旧备份隔离副本，按旧表/旧列逐PK比较；不声称覆盖备份之后个人新增记录或当前全局零用户写入。个人库未停写/迁移，未重新采集个人备份。

## 6. CAS、类型与验收证据

真实两个连接同步争抢v1→v2/v3，结果为PUBLISHED→pub-v2及CURRENT_VERSION_CONFLICT→pub-v2；两操作各恰1审计，重放一致。还测同请求并发只有一条审计、异payload、过期current、跨课、未知目标、坏hash、正文/关系快照/媒体变化、许可失效、未validated及状态写入后的注错。注错后current仍NULL、目标仍validated、失败审计1条；新operation可正常发布。原始结果见java-publication-real-db日志的CAS_RESULTS及实际审计表。

B04三类课程×三类音频的9种独立分类均验证通过；未知枚举、来源/许可不匹配及未授权/不完整条件拒绝。content_license.source_type不另造体系。测试材料为自编句子及既有自编MP3测试波形，licensed/recording类别是明确的合成规则元数据，不是第三方教材/真人录音授权证明；真实第三方权利仍NOT VERIFIED。

## 7. 实际验证与退出码

命令从项目根经 `scripts/phase10b3.py` 的独立副本记录；真实DB由 `phase10b3_isolated.py` 身份门禁注入。逐命令的argv/cwd/时间、实际退出码和log hash在证据目录；最终业务源码hash及与构建的逐文件比较在delivery-audit.json。相同HEAD不代表中间未提交工作区字节相同，不把历史工具日志当成最终全部工具源码已重跑。

| 命令/范围 | 实际结果 |
| --- | --- |
| Maven package / verify | 编译/打包通过；无DB开关时的门控跳过不算DB PASS |
| 真实MySQL旧回归 / MultiCourse / ContentPublication | 21 / 1 / 3条通过，0失败/错误/跳过 |
| equivalent参考/审计快照保护及音频状态重叠定向test | 各1条通过，0失败/错误/跳过；合计27条Java实际执行 |
| npm test / typecheck / lint / build | Node28条通过，其余各退出0；独立8149/3169构建 |
| Python unittest discover | 15条通过，退出0；schema .14/.15及原旧备份支持保留 |
| migrations / append-migration / supplemental | 升级、V009.15、最新空库/重复初始化拒绝、DDL/DML/history故障及新目标恢复分别通过 |
| 独立发布CLI | validate、publish、replay各退出0；正文/学习/DDL权限负例各预期退出1 |
| 实际data-transfer backup / restore | 各退出0，43表逐值一致；新identity/map/validation/audit、生成列和ready录音均完整 |
| Playwright多课 / Demo闭环 / 10B3边界 | 各退出0、passed=true；后者补验真实equivalent提示及新版零练习；pageErrors为空 |
| 最终候选重启/恢复 | 最新JAR在测试源与恢复schema各两次重启，43表/媒体完全一致，实际撤回音频410；恢复后真实续学/幂等/再重启通过 |
| OpenAPI / whitespace | Ruby内置YAML解析通过，git diff --check通过；Python/Node无yaml模块的尝试不当应用故障 |

Playwright（沿用playwright技能和固定CLI0.1.22）实际验证：目录、两课12/24句及2/3段、历史版本、Range/实播、空态/失败重试、Demo真实听写/阅读/两版作文/错题测验/复习、幂等重试/草稿刷新/键盘/skip不计practiced，以及无映射回首句、稳定身份返回、撤回410与原证据可追。1440侧栏224px/播放器76px与1280无横溢出保留。失败注入UI与真实后端损坏负例分别标记，不把注入当真实故障。

截图在 `output/playwright/phase10b3-*.png`、`phase10b3-demo/`；已查看版本/等价参考1440截图。没有更改六Tab或播放器设计；截图不证明语音质量。

## 8. 失败保留、环境及限制

- 沙箱Mockito附加、Python ps/回环端口限制导致失败；相同范围在允许环境实际通过。原退出码/日志保留。
- 首轮多课音频负例预期404得到409：恢复既有课程撤下/许可不可用404，仅具体版本撤回410。旧失败库保留，新regression-final目标重跑通过，没有删断言或覆盖失败记录。
- 最新空库首轮健康早于ApplicationRunner提交，读取HTTP404/退出1（原工具session 87279的完整异常已取回）；工具改为等待Demo实际可读，保留fresh-final现场，另建fresh-resume后通过。
- 最终辅助SQL恢复首次启动因遗漏目标schema账号授权被身份门禁拒绝/退出1；仅补齐该隔离目标的既有授权清单后，43表未变、真实续学及重启通过。实际data-transfer恢复路径原已包含此授权并通过；未放宽guard或改history。
- 自动审批因额度耗尽未能完成一次Java重建审查；该命令未执行，属于审批服务可用性失败，不是动作不安全裁决。用户续跑后在同范围成功执行，未绕过审批。
- 真麦克风/人工实听、Safari/另机、真实教材/第三方声音授权未验证。MP3测试波形不作朗读、ASR或发音评测。
- 新版本校验只是当前本地基础profile。10E输入校对/完整Schema/导入批次与媒体提交机制、10F计划和效果验证均未实现。普通Spring仍沿用Flyway自动迁移，新JAR不可擅自在个人配置启动。

## 9. 最终停止点

最终候选JAR SHA-256：`c4243bca0b7062e2c94bbe6e78fe7e5603791173c615959a4819a5f6ecdfc310`。最终二次重启覆盖测试源与含全部新增表的恢复schema，43表及媒体字节一致；恢复副本真实续学只新增允许的作文/证据/回执及对应投影，幂等重放与再次重启一致。

`delivery-audit.json`核实本轮11个容器均exited、卷保留、测试端口无监听；重算9,340份原始日志hash，13份历史迁移和10份新迁移字节保持，179份共享证据未匹配源/隔离凭据。已有三份UI源码与起点hash一致。最新个人Web/API只读健康仍UP/009.05，原部署JAR SHA-256仍为`b148e046ff3a9b62b4abed11969af285733ea6018b94f3e84fdee4f0a645e8f5`；本阶段没有个人库SQL写入、停写、迁移或部署。

| 验收 | 结论与边界 |
| --- | --- |
| T1稳定身份 / T2拆合句 | PASS；同课登记/跨课及重复负例、五类映射、无目标与无映射、旧真实成绩不转移 |
| T3生命周期 / T4发布并发 | PASS；草稿/校验/发布/撤回、旧回执、CAS一胜一冲突、同请求并发及失败回滚/审计 |
| T5 / B04 | PASS（隔离分类与许可规则）；真实第三方授权NOT VERIFIED |
| T6历史兼容 | PASS（受控旧备份及隔离回归）；不声称当前个人新增记录已全量重取 |
| T7 / B01 / B03 | PASS；固定旧基线升级、最新V001空库、故障残留/新目标恢复、实际工具43表/录音恢复、最终候选重启/续学 |
| API/前端及旧学习回归 | PASS；Java27/Node28/Python15及三组Playwright；不将门控跳过算通过 |
| 个人库保护及阶段边界 | PASS（本阶段执行范围）；未迁移/部署个人库，未开始10C |
| 真设备、实听、另机与正式内容权利 | NOT VERIFIED；不并入本地工程PASS |

本阶段已停止开发，交付报告、证据及变更清单等待人工独立审核；未commit/push，未部署个人站点，不自动进入10C。

10C可以复用已验证的稳定身份、不可变版/状态/current CAS、明确的媒体访问边界和新表恢复基础；共享音轨约束/坐标、动态题集/run分母仍须新迁移、独立演练和单独批准。
