# Phase 10A · 06 独立课程导入流水线

状态：仅设计，不解析/导入四册教材，不安装OCR或对齐模型，不生成新课/新音频。依据：`catalog/ContentPackage.java`和`ContentSeeder.java`只有固定Demo校验播种；`content/demo-01/{active.json,v1/lesson.json,v1/manifest.json,v2/lesson.json,v2/manifest.json}`；`scripts/validate-content.py`是Demo验证，不是通用导入器；`ExportController`与`scripts/data-transfer.py`负责学习数据快照，不能复用成教材覆盖接口。

## 1. 工具边界与输入

拟在现有API Maven工程内增加独立Java CLI入口（不启动Web、不运行ApplicationRunner、不触发Flyway/reconcile），复用内容校验/事务写服务。解析器可为离线独立脚本，但最终写入只有Java发布服务；不新增消息队列/CMS服务。命令名示意 `content validate/plan/apply/publish/status`，10A没有这些命令可执行。

输入需有来源/授权范围/proofRef/审查人/原文件hash；文本、音频、插图分别记录。pending_review只能进入隔离草稿区，不能变成新教材可学发布；现有Demo本地测试例外保留原边界，不推导新教材也获例外。不抓取整套教材、不绕过文档保护。

## 2. 可审查流程

| 步骤 | 输入→输出 | 人工/机器门禁 |
| --- | --- | --- |
| 取得材料 | 本地授权PDF/文本/音频→source inventory | 范围/许可可追溯；未知权利不发布 |
| 解析 | 文本层提取；扫描件OCR→保留页码/框位置的raw文本 | 先区分文本层与扫描；OCR结果不是正确原文 |
| 校对 | raw→corrected transcript+修改日志 | 人工逐段逐句核对字形、标点、缩写、人物、页眉页脚，标reviewer/time/hash；不能让OCR静默改教材 |
| 结构化 | transcript→中间JSON | 册/课/版/段/句/词义/题目/来源显式；拆句是教学单元，Demo一条可能含多句，不能按句号重切旧ID |
| 编写教学包 | 10E基础题目/答案/解析；10F另加目标与learningPlan | 10E不要求尚未支持的计划字段；10F校验目标、步骤、反馈及延迟复习覆盖 |
| 对齐 | transcript+audio→候选时间轴→审定时间轴 | 见05；所有边界人工听核，工具失败允许手工；未核验不能发布共享音轨 |
| 静态验证 | JSON Schema+语义校验+文件hash→errors/warnings | 引用完整、可学条件、大小/题量上限、答案/授权/对齐状态 |
| Dry run | 只读目标快照+包→操作计划和冲突报告 | 不写DB、不搬目标媒体、不改current、无自动迁移；仅写用户指定报告文件 |
| Apply | 已批准planHash+同hash包→不可变内容行与导入审计 | 重新锁定、检查版本/指针/目标元数据未漂移；全量单课DML事务 |
| Publish | validated版本+对应profile门禁→当前指针 | 显式指定basic_content或teaching_complete；短事务CAS；10E只允许前者；发布失败不替换现行课 |
| 核验 | DB+API+媒体→一致性报告 | 比对全部ID/行hash/数量/引用/音频及去答案API；无学习attempt被制造 |

大包按课独立事务，批次可partial_failed；已成功课若只apply未publish仍不可学，不宣称整册原子发布。默认逐课发布，批量发布清单须明确每课结果；失败续跑按import_entry恢复，不重新执行成功课。

## 3. 课程中间JSON Schema契约

采用[JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)。以下是10C–10E首个机器契约的核心完整profile设计，嵌入文档供审查；不是仓库已实现的验证器。core-v1仅对应 `basic_content`（基础内容可用），允许课文、音频及已支持的基础练习；无练习时明确提示。教学计划/人工输出扩展在10F增加独立 `teaching-v1` profile，对应 `teaching_complete`（完整教学计划可用），不能以任意未校验JSON进入发布库。完整计划必须具备02约定的目标、训练步骤、反馈、延迟复习与真实证据关联规则；“计划可用”也不等于学生已完成或效果已证实。所有跨引用、数组按ID唯一、跨字段数值关系在第4节语义校验完成，Schema本身不保证这些。

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Northstar content package core-v1 (proposed)",
  "type": "object", "additionalProperties": false,
  "required": ["schemaVersion", "packageId", "book", "lesson", "version", "sources", "paragraphs", "sentences", "audioAssets", "knowledge", "exercises", "exerciseSets"],
  "properties": {
    "schemaVersion": {"const": "northstar.content.core.v1"},
    "packageId": {"$ref": "#/$defs/id"},
    "book": {"anyOf": [{"type": "null"}, {"$ref": "#/$defs/book"}]},
    "lesson": {"$ref": "#/$defs/lesson"},
    "version": {"$ref": "#/$defs/version"},
    "sources": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/source"}},
    "paragraphs": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/paragraph"}},
    "sentences": {"type": "array", "minItems": 1, "maxItems": 1000, "items": {"$ref": "#/$defs/sentence"}},
    "audioAssets": {"type": "array", "items": {"$ref": "#/$defs/audio"}},
    "fullAudioAssetId": {"$ref": "#/$defs/id"},
    "knowledge": {"type": "array", "items": {"$ref": "#/$defs/knowledge"}},
    "exercises": {"type": "array", "items": {"$ref": "#/$defs/exercise"}},
    "exerciseSets": {"type": "array", "items": {"$ref": "#/$defs/set"}}
  },
  "$defs": {
    "id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"},
    "hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    "text": {"type": "string", "minLength": 1, "maxLength": 20000},
    "ids": {"type": "array", "uniqueItems": true, "items": {"$ref": "#/$defs/id"}},
    "book": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "catalogKey", "editionLabel", "title"],
      "properties": {"id": {"$ref": "#/$defs/id"}, "catalogKey": {"$ref": "#/$defs/id"}, "editionLabel": {"$ref": "#/$defs/text"}, "title": {"$ref": "#/$defs/text"}}
    },
    "lesson": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "title", "slug", "sequence", "kind"],
      "properties": {"id": {"$ref": "#/$defs/id"}, "title": {"$ref": "#/$defs/text"}, "slug": {"$ref": "#/$defs/id"}, "sequence": {"type": "integer", "minimum": 1}, "kind": {"enum": ["original_demo", "original", "licensed"]}}
    },
    "version": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "number", "licenseId", "transcriptSha256", "transcriptNormalization", "contentReadiness"],
      "properties": {"id": {"$ref": "#/$defs/id"}, "number": {"type": "integer", "minimum": 1}, "licenseId": {"$ref": "#/$defs/id"}, "transcriptSha256": {"$ref": "#/$defs/hash"}, "transcriptNormalization": {"const": "transcript-v1"}, "contentReadiness": {"const": "basic_content"}}
    },
    "source": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "medium", "sourceType", "sourceRef", "sha256", "rightsScope", "reviewStatus", "proofRef", "reviewer"],
      "properties": {
        "id": {"$ref": "#/$defs/id"}, "medium": {"enum": ["text", "audio", "annotation"]}, "sourceType": {"enum": ["original", "licensed"]},
        "sourceRef": {"$ref": "#/$defs/text"}, "sha256": {"$ref": "#/$defs/hash"}, "rightsScope": {"$ref": "#/$defs/text"},
        "reviewStatus": {"enum": ["pending_review", "confirmed", "rejected", "expired"]}, "proofRef": {"type": ["string", "null"]}, "reviewer": {"type": ["string", "null"]}
      }
    },
    "paragraph": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "stableKey", "sequence", "sourceRef"],
      "properties": {"id": {"$ref": "#/$defs/id"}, "stableKey": {"$ref": "#/$defs/id"}, "sequence": {"type": "integer", "minimum": 1}, "sourceRef": {"$ref": "#/$defs/text"}}
    },
    "sentence": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "stableKey", "paragraphId", "sequence", "speaker", "text", "translation", "explanation", "focus", "audioAssetId", "startMs", "endMs"],
      "properties": {
        "id": {"$ref": "#/$defs/id"}, "stableKey": {"$ref": "#/$defs/id"}, "paragraphId": {"$ref": "#/$defs/id"}, "sequence": {"type": "integer", "minimum": 1},
        "speaker": {"type": "string", "maxLength": 64}, "text": {"$ref": "#/$defs/text"}, "translation": {"type": "string", "maxLength": 20000},
        "explanation": {"type": "string", "maxLength": 20000}, "focus": {"type": "string", "maxLength": 255},
        "audioAssetId": {"$ref": "#/$defs/id"}, "startMs": {"type": "integer", "minimum": 0}, "endMs": {"type": "integer", "minimum": 1}
      }
    },
    "audio": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "licenseId", "sourceKind", "storageKey", "mimeType", "byteSize", "durationMs", "sha256", "alignment"],
      "properties": {
        "id": {"$ref": "#/$defs/id"}, "licenseId": {"$ref": "#/$defs/id"}, "sourceKind": {"enum": ["original_tts", "original_recording", "licensed_audio"]}, "storageKey": {"type": "string", "minLength": 1, "maxLength": 128},
        "mimeType": {"const": "audio/mpeg"}, "byteSize": {"type": "integer", "minimum": 1, "maximum": 2147483647}, "durationMs": {"type": "integer", "minimum": 1, "maximum": 2147483647}, "sha256": {"$ref": "#/$defs/hash"},
        "alignment": {"type": "object", "additionalProperties": false, "required": ["status", "method", "audioSha256", "transcriptSha256", "transcriptNormalization", "sentenceIds", "reviewer", "reviewedAt"], "properties": {
          "status": {"enum": ["auto_draft", "needs_review", "verified", "rejected"]}, "method": {"$ref": "#/$defs/text"}, "audioSha256": {"$ref": "#/$defs/hash"}, "transcriptSha256": {"$ref": "#/$defs/hash"}, "transcriptNormalization": {"const": "transcript-v1"}, "sentenceIds": {"$ref": "#/$defs/ids", "minItems": 1}, "reviewer": {"type": ["string", "null"]}, "reviewedAt": {"type": ["string", "null"], "format": "date-time"}
        }}
      }
    },
    "knowledge": {
      "type": "object", "additionalProperties": false,
      "required": ["conceptId", "occurrenceId", "kind", "canonicalKey", "senseKey", "term", "meaning", "sentenceId"],
      "properties": {
        "conceptId": {"$ref": "#/$defs/id"}, "occurrenceId": {"$ref": "#/$defs/id"}, "kind": {"enum": ["vocabulary", "grammar", "collocation", "pattern"]},
        "canonicalKey": {"type": "string", "minLength": 1, "maxLength": 255}, "senseKey": {"$ref": "#/$defs/id"}, "term": {"type": "string", "minLength": 1, "maxLength": 100}, "meaning": {"type": "string", "minLength": 1, "maxLength": 255}, "sentenceId": {"$ref": "#/$defs/id"}
      }
    },
    "exercise": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "kind", "sentenceIds", "occurrenceIds", "prompt", "options", "answerKey", "explanation"],
      "properties": {
        "id": {"$ref": "#/$defs/id"}, "kind": {"enum": ["dictation", "reading_choice", "quiz_choice"]}, "sentenceIds": {"$ref": "#/$defs/ids", "minItems": 1}, "occurrenceIds": {"$ref": "#/$defs/ids"},
        "prompt": {"$ref": "#/$defs/text"}, "options": {"type": "array", "items": {"type": "object", "additionalProperties": false, "required": ["id", "text"], "properties": {"id": {"$ref": "#/$defs/id"}, "text": {"$ref": "#/$defs/text"}}}},
        "answerKey": {"type": ["string", "null"]}, "explanation": {"type": "string", "maxLength": 20000}
      }
    },
    "set": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "purpose", "protocolVersion", "contextGroupId", "exerciseIds"],
      "properties": {"id": {"$ref": "#/$defs/id"}, "purpose": {"enum": ["practice", "diagnostic", "immediate", "delayed", "transfer"]}, "protocolVersion": {"$ref": "#/$defs/id"}, "contextGroupId": {"$ref": "#/$defs/id"}, "exerciseIds": {"$ref": "#/$defs/ids", "minItems": 1, "maxItems": 100}}
    }
  }
}
```

profile说明：首版每句有音频是与V002 NOT NULL兼容的约束；纯文本草稿可留在解析区，不能以空asset绕过发布。knowledge每项表示一个全局概念在一个句子的出现：occurrenceId在包内唯一，同conceptId可在多项重复但其kind/canonicalKey/senseKey必须完全一致，term/meaning为语境释义；每项只绑定一个sentenceId。多句出现显式列多项，禁止用同occurrence PK表示多句。后续profile再增加lesson/paragraph scope。首版选择题用真实首证据句作为旧主锚点，所有证据句另入关联表；需保留与该锚点同句的旧knowledge_point兼容投影。dictation要求恰一源句、options=[]、answerKey=null，规则标准来自原句；选择题2–8选项、唯一有效answerKey、至少一个目标occurrence。这些均须语义验证。

整包hash放在外部manifest（不自包含循环hash）；源文件sha、校对文本sha、规范化内容sha、原JSON字节sha分别保存。规范化算法带版本，JSON字段排序、UTF-8/LF规则固定；旧Demo继续用原字节hash，不改为新算法。

## 4. Schema之外的语义验证

ID/slug/存储键长度符合实际列限制；按对象身份验证数组内ID唯一（knowledge以occurrenceId判重，conceptId按上述共享规则）与引用归属，lesson↔book↔edition不可漂移；同版本只出现同课段/句/asset，段句序唯一连续；stableKey匹配身份registry；同ID不同hash冲突。题目选项归属、answerKey存在、请求profile是否受支持；teaching-v1另验写作/计划及教学目标覆盖；所有新字段映射到DB列或版本payload，不能校验后丢字段。

校对状态、许可范围及到期、对齐状态verified且审校人/时间非空、下述同类型哈希关联校验、所有start/end边界及时长有效。core-v1只校验基础练习可运行；完整教学目标覆盖等10F条件只在teaching-v1验证，缺失时不得宣称完整教学闭环。日期format需开启assertion或Java显式Instant解析，不能以Schema的format注解当校验成功。路径拒绝绝对路径、..、编码绕过与越界软链接；PDF/OCR输入限定文件大小/页数/超时、不执行嵌入脚本，不把任意路径暴露给Web。


### 4.1 SHA-256分别计算与关联（R1）

设 `H=SHA-256`。`transcript-v1`：句子按全课sequence排序；每句text先将CRLF/CR统一为LF，再Unicode NFC，仅去除整个text两端的ASCII空格/Tab/LF，保留内部空白、大小写、标点与说话内容；用单个LF连接，末尾加一个LF，UTF-8无BOM编码。说话者标签、译文、讲解不进入转录哈希。此算法也用于对齐的句子子集，不能以JSON字段排序算法代替。旧Demo字节校验保持原规则，由兼容适配器提供派生检查，不回写旧包。

- `A = H(实际原音频文件字节)`：必须等于 `audioAssets[i].sha256`，且等于该音轨 `alignment.audioSha256`。临时PCM不是原音频，若保留其hash必须另记，不能覆盖A。
- `T = H(本课全部句子的规范化转录字节)`：必须等于 `version.transcriptSha256`。
- `Ti = H(该音轨alignment.sentenceIds对应的规范化转录字节)`：必须等于该音轨 `alignment.transcriptSha256`。sentenceIds必须按全课sequence排列，且恰好覆盖所有引用该asset的句子；不得遗漏、重复、外课或乱序。独立句音频只覆盖本句；完整共享音轨覆盖全课时Ti=T，否则不要求相等。首版不允许夹带未转录的其他语音，静音可保留。
- 不要求 `A=T` 或 `A=Ti`；比较的是每个声明与其实际对象及关联记录。即使偶然相等也不能取代上述校验。音频字节变化、文本变化或句子覆盖关系变化均使原对齐审校失效，重新核验并创建新版本。

可复算哈希单元样例（字节夹具只验证规则，**不是可解码MP3或实播测试**；正式10E还需合法可解码音频）：

```python
from hashlib import sha256
import unicodedata

def transcript_v1(texts):
    parts = [unicodedata.normalize("NFC", t.replace("\r\n", "\n").replace("\r", "\n")).strip(" \t\n") for t in texts]
    return ("\n".join(parts) + "\n").encode("utf-8")

def digest(data):
    return sha256(data).hexdigest()

raw_audio = b"audio-fixture-v1"
texts = ["Good morning.", "Please sit beside me."]
A, T = digest(raw_audio), digest(transcript_v1(texts))
asset = {"sha256": A}
alignment = {"audioSha256": A, "transcriptSha256": T}
assert A != T  # 正确数据也可不同，不能要求两类哈希相等
assert digest(raw_audio) == asset["sha256"] == alignment["audioSha256"]
assert digest(transcript_v1(texts)) == alignment["transcriptSha256"]
assert digest(raw_audio + b"changed") != asset["sha256"]
assert digest(transcript_v1(["Good evening.", texts[1]])) != alignment["transcriptSha256"]
assert digest(transcript_v1(texts[:1])) != T  # 单句覆盖不能套整课哈希
```

| 测试输入 | 预期 |
| --- | --- |
| 正确文件A、全课T、完整共享音轨关联(A,T)，A与T不同 | PASS；独立句资产另用本句Ti也PASS |
| 改音频字节但保留asset.sha256 | 拒绝audio_hash_mismatch |
| asset.sha256正确但alignment.audioSha256指向旧文件 | 拒绝alignment_audio_mismatch |
| 改句子文本却沿用version.transcriptSha256 | 拒绝transcript_hash_mismatch |
| 课文哈希已更新，但alignment.transcriptSha256仍旧值 | 拒绝alignment_transcript_mismatch，重新人工审校 |
| 单句对齐填整课T，或sentenceIds遗漏/乱序/串asset | 拒绝alignment_transcript_mismatch或alignment_scope_mismatch |
| 仅CRLF/LF或Unicode组合形式不同 | 规范化哈希一致；原文件字节hash仍各自校验 |

### 4.2 类型与规范词条（R2、补充1）

课程 `original_demo/original/licensed` 分别是历史Demo、新增原创、获授权第三方；音频 `original_tts/original_recording/licensed_audio` 分别是原创合成、原创真人、授权第三方。课程与音频独立分类，禁止从课程kind推断音频来源。来源许可仍 `original/licensed`，每个version和asset的licenseId必须引用包内sources.id；校验medium与sourceType匹配、proofRef/审校记录及使用范围。原创TTS需要引擎/声音许可依据，真人录音需要录制者与声音使用许可，第三方录音需要授权范围；未知一律不发布。source.sha256校验其sourceRef对应原始文件，不能用它冒充音频/转录哈希。历史Demo例外不扩散给新增原创课。

conceptId是稳定opaque ID；canonicalKey是规范词汇/搭配/语法表达的Unicode文本，可含空格、撇号、连字符，如 `community garden`、`look after`、`someone's turn`。用NFC、去两端空白、连续空白折叠为单个空格进行词条规范化，不删标点、不自动转小写；导入值应已规范化且非空。它不是ID、URL或sentence.stableKey，不能引用$defs/id。senseKey仍是人工登记的义项标识；规范文本相同不意味着义项可合并，见03第5节。

## 5. 幂等、冲突与发布事务

- `import_batch`：id、packageId、packageHash、schemaVersion、toolVersion、targetFingerprint、planHash、status、started/finished；`import_entry`：batch/version/action/expectedHash/result。UQ(packageId,packageHash,targetIdentity)，另对version ID唯一锁定。
- 同版本同hash：验证已存所有投影行及媒体后no_op，不能跳过一致性校验；同版本不同hash：immutable_version_conflict，要求新版本；same book/lesson ID但edition/book归属不同：identity_conflict；同文件键不同hash：media_conflict；当前发布指针与dry run不同：stale_plan。
- 冲突报告含JSON Pointer、对象ID、预期/实际hash、code、severity、建议；不将完整版权文本/私人记录/凭据写公开日志。warnings必须可逐项接受，error零个才apply。
- Apply先复制媒体到项目专用staging目录，验证后原子rename到不可变版本路径；fsync及空间检查。文件先可用，DB后提交；崩溃允许遗留孤儿文件，但不能制造已发布缺文件版本。
- 单课DML事务内锁项目身份/lesson行，复验planHash与所有冲突条件，写许可/版本/段句/题目/关联并标validated；不含DDL/ALTER/GRANT。审核确认发布时再锁lesson，核验许可、媒体、profile/contentReadiness和expectedCurrent，原子更新状态/current与发布审计。10E只允许basic_content；10F补计划必须创建新版本并以teaching-v1重新验证，不原地升级已冻结包。
- 进程在DB提交后响应前退出：重试查询同hash批次/版本，返回原结果，不新增内容/事件。媒体已落盘DB失败：保留孤儿清单、下次验证复用；不自动删旧文件。并发同包一个成功一个no_op，异包相同版本一个成功一个冲突。
- CLI使用内容写入专用账号，无学习表UPDATE/DELETE权限、无DDL权限；普通app账号仍只按原权限学习写入。DDL仅迁移账号离线阶段执行。运行账号不自动拥有导入权限。

## 6. 导入后校验与验收

比对计划中每张表ID/数量/hash、所有FK/跨课负例、题集题量、音频大小/hash/区间/许可；读取API不得泄漏标准答案和私有存储路径；完整实播与逐句定位；新课无attempt/learning_evidence；Demo原列/旧学习/媒体不变；新版本前后旧URL可读。

10E先只使用自有样例（非四册正文）：一课一音轨多段、一课独立句音频，1/5/12题、跨课同概念、版本修改/拆合句/缺文件/错误OCR；dry run前后目标DB摘要和目标媒体清单完全相同。故障注入覆盖解析、校对缺失、hash错、路径越界、磁盘满、文件落地后DB失败、DB提交后进程中断、publish CAS冲突、并发重导。所有结果与重试可核对才Go；源码完成不等于批量教材可上线。

10E验收必须证明“basic_content可学、完整教学计划未验收”，不能输出完整闭环标志；10F另验收teaching-v1及真实学习证据。仅文本与音频的版本即使发布也只为basic_content，无任务时不显示计划完成率。
