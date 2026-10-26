# Phase 10A · 07 API与前端影响

状态：接口草案，未更改 `docs/openapi.yaml` 或业务实现。Java根目录为 `apps/api/src/main/java/local/northstar/`，Web根目录为 `apps/web/src/`。

## 1. 实际依据与兼容原则

已核查 `CatalogController`、`StudyController`、`ExerciseController`、`QuizReviewController`、`WritingController`、`RecordingController`、`ReportController`、`ExportController`；前端 `lib/api/{catalog,reading,practice}.ts`、`lib/state/{context,LessonProvider}.tsx/ts`、`lib/media/*` 与对应课程/练习/复习/报告组件。

沿用 `/api/v1`、同源转发、LocalAccessFilter、Problem JSON、回环访问和既有幂等/CAS。先添加字段与可选参数，不直接把旧数组响应改成分页对象；需要分页的新查询用独立路径或显式新profile。兼容固定Demo旧请求与未确认outbox，在旧版本保留期间仍可重放原回执。新请求不改变已有operation+payload的哈希算法，避免旧event重试冲突。

## 2. API变化矩阵

| 当前端点/代码 | 拟变化 | 兼容与错误边界 | 阶段 |
| --- | --- | --- | --- |
| GET books/lessons，CatalogController | 新book课次列表 `GET /books/{id}/lessons?cursor&limit`，返回items/nextCursor；册/版/来源/可学数与contentReadiness | 旧端点保留数组/standaloneLessons字段；standaloneLessons纠正为book_id为空的课，另增册内列表；不返回348个假可学入口 | B-2读取 / B-3身份发布 |
| GET lessons/{id}?versionId | 新增paragraphs、sentences的stable identity/paragraph/start/end、audioAssets/fullAudioAssetId、可用任务/来源/contentReadiness；版列表 `GET /lessons/{id}/versions` | 固定version查询仍有效；current不改已打开页面；旧每句audio继续返回；缺音频文本可读、媒体状态明确 | B-2/B-3/C |
| GET audio/{id} | 通用清单验证和共享文件 | 200/206/416与坏媒体503保留；不将storageKey公开；撤回不再供新播放 | C |
| GET/PUT study/resume | 旧positionMs句内语义不变，新增可选坐标/完整音轨字段；按版恢复用新 `/study/checkpoints/{versionId}` | 无新字段=旧协议；If-Match及412/428不改；请求同版/范围验证 | C/F |
| GET quiz | 增setId/setHash/totalCount/history每轮total/submitted与sequence | 无参数旧Demo选择默认题集；新版本显式set；历史分母来自run快照 | C |
| POST quiz/attempts | 新请求带setId/setHash/answers；DTO取消恰3限制，按集合1..100验证；结果增totalCount/submittedCount/accuracy | 旧Demo无set仍解析冻结默认3题；后端不信客户端正确数；空集/漏题/外题422、过期题集409；错误无半轮数据 | C |
| POST exercises/{id}/attempts | 从DB解析exercise↔源句，不依赖拼接唯一ID；旧sentence-dictation兼容 | 听写仍audioPlayed且音源可用；旧算法english_token_v1不变；unknown曝光不冒充独立 | C/F |
| GET reading / POST reading/{id}/attempts | sourceSentenceIds/targetOccurrences、反馈explanation从版本题目取；返回source sequence | 去除beside/第6句硬编码；旧primary sentence/knowledgePointId保留；错误来源真实 | D |
| knowledge/{id}/favorite | 旧课内收藏不变；新全局概念浏览 `/knowledge/concepts/{id}/occurrences?cursor` | 不把旧词条ID重命名；跨课联想与权利可见性校验 | D |
| reviews/due/items/answer/results | 原句卡接口保留；新增 `/concept-reviews`列表/来源/自评与客观复测入口 | concept自评不调用旧同句FK写接口；CAS/到期/幂等；回原attempt+version | D/F |
| writing系列 | 原单任务Demo保留；新增 `/writing/tasks/{taskId}`及显式task提交参数 | 不能继续用getFirst选择多任务；原revision/parent/draft不迁移不覆盖 | F |
| recordings系列 | 旧句录音保留；输出任务关联submission | 120秒/8MB不自动扩大；人工评审另端点，不虚构ASR；权限/回放失败可跳过继续 | F |
| reports | 旧计数字段修正为SUM(run.total_count)，增加筛选参数；新 `/reports/evidence`与分页历史 | 有无数据分母都可复算；原6路径仅Demo兼容视图，不再用于所有课完成率；阅读历史旧端点保留受限用途，新UI改分页 | C/F |
| data/export/import-preview | 新表全部有PK；CONTENT分类/签名/恢复顺序更新；大包分块是显式新格式 | 旧snapshot.v1同基线规则保留；旧备份先旧工具恢复再升级，不改schemaVersion绕过；JSON继续不含录音/浏览器缓冲 | B–F |

本阶段不为CLI导入加Web管理写端点。API权限仍是本地单用户来源防护，不能称支持公网无登录导入。未知版404、关联不匹配422、同event异内容409、资源撤回返回明确业务code；精确HTTP/Problem契约在对应实现阶段更新OpenAPI并做契约测试。

新增 `contentReadiness` 返回basic_content/teaching_complete/legacy_unassessed；与publicationState和releaseReady分别传递。10E课程仅标“基础内容可用，完整教学计划未验收”；10F通过教学profile才显示“完整教学计划可用”，完成状态仍来自个人真实证据。无计划不展示完成百分比，不能由published、available或有音频推断闭环。kind/sourceKind类型同步03/06的保留旧值与新增值，canonicalKey作为Unicode规范文本展示，不作ID或路由键。

10B-2只落多课读取与旧Demo适配；身份登记、类型CHECK扩展和显式发布/current CAS在10B-3验收。涉及的候选schema均先经10B-1安全门禁或同等增量重演，不因拆阶段跳过恢复检查。

## 3. 示例契约（设计）

```json
{
  "runId": "opaque-uuid",
  "setId": "set-opaque-id",
  "totalCount": 5,
  "submittedCount": 5,
  "correctCount": 4,
  "accuracy": 0.8
}
```

这里只展示汇总字段，正式成功响应还必须包含恰好5条answers。accuracy传0..1，UI再格式化；整体正确率为Σcorrect/Σtotal，不对各轮百分比取平均。无测验时返回空题集提示，不能返回0题100%。旧回执可能没有新增字段，客户端用该run的已存answers长度兼容显示，不借用当前题集长度；若无法确认则显示“分母待核对”。

## 4. 前端最小修改清单

| 文件（相对Web根） | 变化与测试重点 |
| --- | --- |
| lib/api/catalog.ts | Book availability联合类型、Lesson/Paragraph/Segment/AudioAsset/任务与版本DTO；运行校验边界，不只TS断言 |
| components/CatalogPages.tsx | 册内真实课列表与分页、独立原创课分区；撤回/无内容/来源待审明确；继续入口按真实resume解析 |
| components/lesson/LessonWorkspace.tsx | 元数据驱动标题/音色/版本入口、段落显示、任务可用性；保留1440×900、224px侧栏、2:1、76px播放器 |
| lib/state/context.ts + LessonProvider.tsx | 版本映射按API/stable identity，不替换ID前缀；映射缺失提示并选择新版首句，不迁移历史；空/坏课程不访问sentences[0] |
| lib/media/AudioController.ts / MediaProvider.tsx / timeline.ts | 片段边界状态机/同源复用/坐标变换/词点hash匹配；保存恢复与异步token；细节见05 |
| components/player/PlayerBar.tsx | 文件时间/片段时间/句序拼接时间标签分明；整课静音区无假句子；倍速/循环/A-B保持 |
| components/exercises/QuizPanel.tsx | 动态题数文案/按钮/当前与历史分母；sequence来自DTO，移除slice(-2)；set版本键入草稿/命令，旧key兼容读取不自动覆盖 |
| DictationEditor.tsx | 新题ID来自服务端；旧听写键与曝光记录保留；切课/切版pending请求不串写 |
| ReadingQuestion.tsx / VocabularyPanel.tsx / EvidenceLink.tsx | 不硬写第6句；多源证据/多目标概念可定位；term不同义项分列 |
| WritingEditor.tsx / RecorderPanel.tsx | 明确taskId、输出关联、人工量规状态；旧草稿回载与录音失败重试保留 |
| components/review/ReviewQueue.tsx | 句卡/概念卡分组、全部来源与原版跳转；空态返回当前可学入口，不固定Demo；自评与复测结果分别标注 |
| components/LearningReport.tsx | 动态计划分母、即时/延迟/迁移样本与排除原因；无样本/来源未知显示未验证，不能补零装成评分 |
| lib/persistence/db.ts / outbox.ts | 新记录键显式version/set/task，升级IndexedDB只加store/index并保留旧数据；不清空旧outbox、不替换eventId |

每项保留loading/success/error/empty、失败重试、缺媒体可继续阅读、网络错误不丢草稿。教学环节可配置但不改现有六Tab名称和已存tab CHECK。AI失效不影响学习的原则在此阶段表现为完全不依赖AI。

## 5. 风险与验收

混用新旧字段会导致错误分母、位置加两次或outbox重复。对应实现需API契约+纯状态机单元+真实浏览器实播验证，不凭类型检查证明交互正常。跨两课切换/刷新/旧版深链/返回错误来源、并发提交/412冲突、麦克风拒绝/缺媒体、5题和12题历史混排均必须实测。详见[08](08_TEST_AND_ACCEPTANCE_PLAN.md)。
