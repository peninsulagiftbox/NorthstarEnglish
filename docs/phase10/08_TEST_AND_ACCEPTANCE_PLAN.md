# Phase 10A · 08 测试与验收计划

状态：拟执行清单；下面B–F的测试尚未执行。09-R的25项Node/15项Python/20项Java与MySQL结果仅作历史基线，不能替代Phase10回归。

## 1. 实际依据与回归纪律

现有Java测试在 `apps/api/src/test/java/local/northstar/`，重点为 `catalog/ContentPackageTest`、`CatalogIntegrationTest`、`exercise/ExerciseIntegrationTest`、`ReadingIntegrationTest`、`QuizReviewIntegrationTest`、`practice/PracticeIntegrationTest`、`report/ReportExportIntegrationTest`、`study/StudyIntegrationTest`，以及TokenAligner/SimpleScheduler测试。Web为 `apps/web/tests/*.test.ts`；Python为 `scripts/tests/`；浏览器入口 `scripts/{content-browser-smoke,dictation-browser-smoke,reading-browser-smoke,practice-browser-smoke,quiz-review-browser-smoke,reports-browser-smoke}.sh`、`full-learning-loop.js` 和 `phase09r.py` 的隔离守卫。

不删除或弱化旧断言以迎合新模型：Demo仍10句、3题、2版本；全局计数断言移到“只含Demo的隔离基线”，多课用独立场景按lesson/version断言。旧“缺媒体整课503”按明确批准的新降级契约换成文本可读+媒体503+听写拒绝；错误检测与数据不变断言保留。ReportExportIntegrationTest的008字串改为读取真实当前schema，同时仍测试异schema拒绝，不能让测试变成空替换。

## 2. 隔离测试材料与环境

- 生产学习库不作为测试目标。复用项目级Node22/Java21，不改全局；记录路径/版本、commit、迁移与内容hash、端口、媒体根、命令原始退出码。
- 当前集成源码要求 `northstar_phase01_test`；每轮测试环境用独立DB实例/账号和媒体目录，即使schema同名也核对端口/项目身份，不能让“名字对了”覆盖个人数据。
- 09-R测试脚本含固定V008/表数/冻结签名，实施前精确更新其目标版本与名单，保留防误指主站守卫；不能直接拿旧脚本当通用安全启动器。
- 自有样例A：2段/12句/同一真实音轨/5题；样例B：3段/24句/独立句音频/12题；另有1题、0题和同课v2（换音轨、改一句、拆/合句）负例。与Demo同时存在；两个样例共享一个明确义项，另有同形异义词。新夹具不导入教材，不把合成学习事件写个人库。
- 规模夹具独立授权生成：348个课程“元数据与自有测试内容”只用于隔离性能测试，不标为四册教材；单课1000句、1小时音轨/100题；历史10万attempt/1万review作为提议容量档。真实音频大小按实际测量，不能用空字节证明解码通过。

## 3. 可审计验收矩阵

| 编号/阶段 | 场景及方法 | Go标准（全部满足） |
| --- | --- | --- |
| A01 / 10A | 文档引用、Schema代码块解析、相互约束/阶段依赖检查；git范围 | 九文档+10A_REVIEW_RESPONSE+阶段报告齐全；业务/SQL/content/配置/lockfile无修改；没有运行导入或迁移；待人工审查 |
| B01 / 10B-1 | V008备份恢复副本→V009；旧表原列逐值/媒体hash；空库从V001 | 按04第2.1节提交当前DB/Flyway、备份/媒体、两条升级路径、失败恢复和逐值比较证据；仅隔离目标实际PASS，V001–V008文件hash不变；旧ID/正文/hash/event/作文/录音/卡到期全部不变；新段句FK有效 |
| B02 / 10B-2（读取）及10B-3（身份/发布）分别签收 | 10B-2测两课两版查询、旧URL、重复启动；10B-3测身份登记、current CAS、跨版FK负例 | 不覆盖current；旧记录仍指旧版；外课当前指针/外版段句被拒绝；Demo仍独立课；四册仍目录 |
| B03 / 10B-1 | 每条DDL后中断、登记失败模拟，恢复演练 | 部分DDL可识别、停止写入；不repair/改history；新恢复目标可回到旧基线并实测读/续学；原目标保留 |
| B04 / 10B-3 | 三类课程×三类音频（许可各自匹配）隔离正例；未知枚举负例；历史数据对比 | original_demo/original/licensed及original_tts/original_recording/licensed_audio均支持；未知值及许可不匹配拒绝；V002字节与历史行不变；CHECK替换中断可识别并恢复 |
| C01 / 10C | 完整实播/片段、间隙、共享src、loop/rate/A-B、快速换句、恢复 | 按05第6.1节实际输出捕获/标记校准，每速率/音轨/片段10次，最大绝对误差≤150ms、测量不确定度≤30ms且逐句实听无截词；20次切换/10轮循环无串句；偏移例8400+1500=9900正确；Demo旧录音与句音频不变 |
| C02 / 10C | 1/3/5/12/100题；0题/漏题/外题/错选项；同event并发 | N题成功恰1 run/N answer/N attempt/N evidence，汇总correct一致；重复零新增；异payload409；任何失败零半轮残留；0题不能交卷 |
| C03 / 10C | 历史3题+5题+12题报告、改当前题集后读旧轮 | 分母Σrun.total不再runs×3；每轮历史不随新版漂移；例1/3+4/5整体5/8而非均值；skip/pause/草稿不增run |
| C04 / 10C | Range、坏hash、丢文件、越界、重叠、软链接、>10min恢复 | 正常200/206/416；坏媒体503；文本可读；听写不制造证据；非法区间/路径拒绝；>10min位置按内容范围合法 |
| D01 / 10D | 空格/撇号/连字符canonicalKey合法、空白规范化及空词条拒绝；两课同概念、同形异义、多个来源；直接写非法关联 | 正确跨课联结且每attempt原课版句题可溯；错版/错exercise/错occurrence FK或服务拒绝；不依赖客户端conceptId |
| D02 / 10D | 旧句卡+新概念卡；多错题来源、自评CAS/重试/重启 | 来源不覆盖；旧due/reps/row_version不重置；新卡计次准确；翻卡不生成客观掌握分 |
| E01 / 10E | 06第4.1节正确/错误hash矩阵、音轨覆盖与transcript-v1；OCR待校对、Schema非法/额外字段、未知引用、错答案、权利/对齐未审 | error含JSON Pointer与code；未审不得发布；原稿/校对/hash链可追；无伪造置信度 |
| E02 / 10E | dry run、重复/并发apply、同ID异hash、stale plan、失败续跑 | dry run目标DB/媒体无变；相同包no_op且校验投影；冲突不覆盖；跨课失败明确partial_failed；当前发布版本不变 |
| E03 / 10E | 磁盘满/rename失败/文件后DB失败/DB后响应前退出 | 无已发布缺文件版本；孤儿保留并可查；重试恰一内容版本，旧学习摘要/媒体不变 |
| E04 / 10E | core-v1基础内容发布、缺learningPlan、冒报teaching_complete | 文本/音频/基础练习可验证；允许无计划的basic_content；冒报teaching_complete或未验证计划字段拒绝；无任务无完成率；Demo标legacy_unassessed |
| F01 / 10F | teaching-v1发布门禁与真实闭环；不同册型计划、不选/选做/跳过/暂停/错误作答 | 完整目标/步骤/反馈/延迟复习/证据关联俱全才可teaching_complete；缺一拒绝；真实尝试及延迟条件实测。七环节可组合，非每课全做；必需分母冻结；选做单列；无证据不practiced，错误可以practiced但不算掌握 |
| F02 / 10F | 23h/24h/72h/7d窗口、曝光/未知、重复题/换情境/自评 | 时间来自服务端；23h不计延迟；合格/排除数量可钻取；自评不进客观分母；context未变不算迁移；未知显示未验证 |
| F03 / 10F | 作文多版本+录音关联+人工评审 | 原文/parent完整；rater/rubric/时间可追；无评审只输出证据，无ASR/模型能力分 |
| F04 / 10F | 升级后SQL+媒体备份→新目标→恢复→真实UI续学→重启 | 所有表原列/新关联逐值相同、媒体hash相同；真实新增event幂等；重启再核对；V008旧快照须旧恢复后升级 |
| F05 / 10F | 隔离容量档、Explain、30次暖请求、浏览器性能 | 本地目标机器记录配置；课程首屏≤2s、列表/分页报告p95≤500ms（不含首次构建/导入）；历史查询分页≤100条；JS无长任务>200ms为提议预算，超预算先分页/分段，不先加缓存基础设施 |
| F06 / 10F | 来源防护、私密文件与导出、麦克风拒绝/真实设备 | 回环/Host/Origin/专用头/坏JSON守卫保留；无secret进入JS/报告；权限拒绝可继续；实体设备未执行必须NOT VERIFIED |

性能数字是待审核的工程预算，不是已测结果或对所有Mac的承诺。若单课payload/DOM超预算再做按段加载；不以盲目增加依赖代替测量。1000句/100题为首个有界契约，不能静默截断超限材料，需明确错误或另审上限。

## 4. 执行命令与阶段范围

沿用README的项目环境入口，以下是实施后验证命令模板，不表示10A已运行：

```sh
python3 scripts/local.py exec npm run typecheck
python3 scripts/local.py exec npm run lint
python3 scripts/local.py exec npm test
python3 scripts/local.py exec npm run build
python3 scripts/local.py exec apps/api/mvnw -f apps/api/pom.xml verify
python3 -m unittest discover -s scripts/tests -v
```

真实MySQL使用经检查的隔离环境配置运行 `python3 scripts/local.py db-test`；不是在未核对.env情况下直接执行。普通verify需报告integration skipped与原因；目标阶段新增集成测试必须实际运行。浏览器使用固定Playwright CLI、独立profile/构建/媒体/服务，先更新隔离守卫再跑相关smoke；阶段最终跑完整学习闭环与恢复演练。不要为取证覆盖正在运行的主站构建。

10A只文档，不重复编译整套未修改应用、运行DB或浏览器；执行文档检查并明确“不构成应用回归通过”。B–F按改动先定向单元/契约，再真实DB/媒体/必要E2E；阶段交付需要类型/lint/build与相应集成通过。环境权限失败保留原始日志、退出码与BLOCKED，不模拟通过。

## 5. 手工与证据交付

每阶段 `docs/progress/PHASE_10X.md`（10B拆为PHASE_10B_1/2/3.md） 记录文件、决定、命令/cwd/环境/原始退出码、验收ID、PASS/FAIL/BLOCKED/NOT VERIFIED、截图/trace位置、剩余问题与下一阶段依赖。截图使用合成测试记录，私人学习原文/录音只在本地受限目录；报告不嵌secret或版权正文。

实体Chrome/Safari麦克风：记录浏览器/系统→允许录制→停止→实际回放→刷新再播→人工自评→拒绝权限→提示/跳过→继续写作；再检查播放与录音互斥。音频边界需耳听，截图不证明声音正确。另机安装/恢复与外部浏览器未跑均单列，不能借09-R的Chrome虚拟麦克风PASS覆盖。

任何原记录丢失、回执不幂等、误计跳过、虚构能力或授权未满足的新教材发布均No-Go。阶段结束停止等待用户审核，不自动推进下一阶段。
