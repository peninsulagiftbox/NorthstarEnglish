# Phase 10A-R · 独立设计评审响应

日期：2026-10-26（Asia/Shanghai）。输入结论：**CONDITIONAL PASS**。本轮针对评审修订原九份设计文档，保留技术栈、Demo/V001–V008、不可变版本、显式发布、多课/共享音轨/动态测验/跨课概念与行为证据分层，不全面重写方案。状态为“修订已落文档，待复审”，不自行升级为设计或运行验收PASS。

下列“验收方法”是未来获批实施时的要求；本轮实际执行的文档检查与Git范围记录见[阶段报告](../progress/PHASE_10A.md)。没有改业务代码/迁移SQL，没有连接数据库、备份、迁移或开始10B-2。

## 1. 必须修订项

| 问题 | 修订位置 | 采用的解决方案 | 放弃其他方案的理由 | 对10B–10F的影响 | 验收方法 |
| --- | --- | --- | --- | --- | --- |
| R1：错误要求音频hash与课文hash相等 | [06第3、4.1节](06_CONTENT_IMPORT_PIPELINE.md)、[05第5节](05_AUDIO_ALIGNMENT_DESIGN.md)、[03末尾](03_TARGET_DATA_MODEL.md)、[08 E01](08_TEST_AND_ACCEPTANCE_PLAN.md) | SHA-256分别核验原音频A、全课规范转录T、每音轨覆盖转录Ti；对齐记录分别关联A与Ti。明确transcript-v1、句子覆盖顺序及原文件/PCM区别；补可复算字节夹具和正确/错误矩阵 | 不比较不同内容类型的hash；不以修改声明掩盖篡改；不让独立句对齐误用整课hash；不重写旧Demo字节hash | 10B保护旧hash；10C保存音轨/对齐字段；10E实现静态/语义验证；10F复用验证结果，内容变更新版本 | 正确A≠T仍接受；音频篡改、关联音轨错误、课文变化、对齐转录过期、覆盖遗漏/乱序均拒绝；单句Ti与整课T分别验证。字节夹具不代替合法MP3实播 |
| R2：缺普通原创课程、原创真人录音 | [01第3节](01_CURRENT_ARCHITECTURE_AUDIT.md)、[03第2.1节](03_TARGET_DATA_MODEL.md)、[04第2节](04_MIGRATION_PLAN.md)、[06 Schema/第4.2节](06_CONTENT_IMPORT_PIPELINE.md)、[07](07_API_AND_FRONTEND_IMPACT.md)、[08 B04](08_TEST_AND_ACCEPTANCE_PLAN.md) | 已核对V002真实CHECK；lesson.kind保留original_demo/licensed并新增original；source_kind保留original_tts/licensed_audio并新增original_recording。V009组独立增量迁移替换CHECK，source_type不变；课程/音频独立分类，许可单独验证 | 不修改V002/checksum，不把所有原创伪装Demo，不重命名历史值；不把真人录音伪装TTS，也不从文本授权推断声音授权 | 10B-1演练候选；10B-3实施类型/DTO/发布；10C兼容音频读取；10E按Schema与来源许可校验；10F沿用 | B04三类课程×三类音频合法组合及未知值负例；许可不匹配拒绝；原ID/枚举/许可/hash不变；CHECK替换失败可恢复 |
| R3：10E/10F发布契约冲突 | [02第2.1节](02_LEARNING_BLUEPRINT.md)、[03第2、3节](03_TARGET_DATA_MODEL.md)、[06第2–6节](06_CONTENT_IMPORT_PIPELINE.md)、[07](07_API_AND_FRONTEND_IMPACT.md)、[08 E04/F01](08_TEST_AND_ACCEPTANCE_PLAN.md)、[09 10E/10F](09_PHASE10_IMPLEMENTATION_PLAN.md) | publicationState与contentReadiness独立。core-v1/basic_content只验证课文、音频、基础练习和导入；teaching-v1/teaching_complete才要求目标、步骤、反馈、延迟复习、真实证据规则及闭环实测。历史Demo标legacy_unassessed；补计划新版本 | 不让10E依赖未实现的10F计划；不把有文本音频、published或release_ready当教学闭环；不原地改冻结版本；不追认旧数据为能力证据 | 10B-3预留就绪度与发布门禁；10C/D只验证各自能力；10E只能basic_content；10F验收完整教学计划，用户完成/学习效果仍分列 | E04无计划基础课可发布、冒报完整计划拒绝、无任务无完成率；F01缺目标/训练/反馈/延迟/证据任一必需项拒绝；用真实尝试和合格延迟条件验证闭环 |
| R4：10B迁移前置条件不够硬 | [04第2.1、3–6节](04_MIGRATION_PLAN.md)、[08 B01/B03](08_TEST_AND_ACCEPTANCE_PLAN.md)、[09 10B-1](09_PHASE10_IMPLEMENTATION_PLAN.md) | 仅先在隔离恢复副本与空库执行；六项证据覆盖当前DB/Flyway、备份/媒体hash、V008升级、V001空库初始化、故障恢复和旧列逐值比较。未实际PASS不得迁移个人学习库；迁移集合改变重演 | 不在个人库试错，不以备份存在/SQL评审/空库单一路径替代恢复，不以DDL事务回滚或repair掩盖部分提交 | 10B-1独立先验收；10B-2/3及C–F新增DDL均受同门禁。未来个人库切换另需新鲜备份、固定候选及执行授权 | B01/B03逐项实际日志/退出码、schema/history、前后逐值差异、媒体hash、恢复后旧版读取/续学/重启；缺一BLOCKED/NOT VERIFIED，不能Go |

## 2. 补充优化

| 问题 | 修订位置 | 采用的解决方案 | 放弃其他方案的理由 | 对10B–10F的影响 | 验收方法 |
| --- | --- | --- | --- | --- | --- |
| S1：canonicalKey错误使用ID格式 | [03第5节](03_TARGET_DATA_MODEL.md)、[06 Schema/第4.2节](06_CONTENT_IMPORT_PIPELINE.md)、[07](07_API_AND_FRONTEND_IMPACT.md)、[08 D01](08_TEST_AND_ACCEPTANCE_PLAN.md) | conceptId为稳定标识；canonicalKey为至多255字符、区分大小写的Unicode规范文本，允许空格/撇号/连字符，NFC与空白规则明确；senseKey独立义项 | 不把自然表达slug化，不自动按词面合并或删标点/小写化，避免语义损失及旧ID漂移 | 10B/C不改旧知识点；10D建概念及唯一键；10E校验规范文本；10F按义项目标聚合 | community garden/look after/someone's turn及连字符正例；纯空白拒绝、空白规范化可复算；同词异义不合并 |
| S2：10B范围过大 | [04第2.1节](04_MIGRATION_PLAN.md)、[07](07_API_AND_FRONTEND_IMPACT.md)、[08 B01–B04](08_TEST_AND_ACCEPTANCE_PLAN.md)、[09第3节](09_PHASE10_IMPLEMENTATION_PLAN.md) | 拆10B-1数据安全、10B-2多课读取、10B-3身份与发布；分别输入/交付/Go/报告/停止点；已准备10B-1候选执行顺序，未执行 | 不把安全演练与多课/发布打包为一次默认授权，不将旧演练PASS延伸到新DDL | 10C依赖三个子阶段分别通过；D–F原顺序不变；报告拆PHASE_10B_1/2/3.md | B01/B03归B-1，B02拆读取/发布签收，B04归B-3；任一未通过不自动推进 |
| S3：音频边界≤150ms缺测法 | [05第6.1节](05_AUDIO_ALIGNMENT_DESIGN.md)、[08 C01](08_TEST_AND_ACCEPTANCE_PLAN.md)、[09 10C](09_PHASE10_IMPLEMENTATION_PLAN.md) | 分离人工对齐与播放器执行误差；已知音标记+实际输出捕获校准，各速率/音轨/片段10次，记录起止/循环偏差、最大值/p95、不确定度；前台≤150ms且不确定度≤30ms、逐句实听 | 不用currentTime或截图证明可听精度，不把浏览器称采样级裁剪器，不以平均值掩盖超限 | 10B无音频引擎重构；10C实际测量，失败调整/另审；10E检查对齐质量；10F回归 | 保存源音轨hash、标记/采样率、输出捕获/日志/校准与误差表；无捕获条件NOT VERIFIED，后台仅测暂停策略 |
| S4：学习效果保持核心，避免过度建设 | [02第2.1节及末尾](02_LEARNING_BLUEPRINT.md)、[03第6节](03_TARGET_DATA_MODEL.md)、[09 10F](09_PHASE10_IMPLEMENTATION_PLAN.md) | 保持内容配置+现有任务证据的最小关联，优先验证目标→训练→反馈→延迟复测；教学计划可用/学生完成/学习效果三层分开 | 无当前必要性建设通用流程平台，无合格样本或外部评测不能产生综合能力分 | B–E围绕承载能力；F检验真实闭环与五层证据，不扩BPM/AI/评分基础设施 | F01–F03：跳过不练习、自评不算客观保持、缺样本未验证；真实输出与修订可溯，效果结论不超证据 |
| S5：10A阶段报告及Git范围证据 | [PHASE_10A](../progress/PHASE_10A.md)、[01第7节](01_CURRENT_ARCHITECTURE_AUDIT.md) | 保留原报告历史，追加10A-R实际起止状态、HEAD、跟踪/未跟踪范围、11份文档清单、原九份局部diff统计及V001–V008逐字节检查 | 空git diff不覆盖未跟踪文件，不能据此称新增文档已验证；也不能以本轮状态补造原10A运行证据 | B–F尚未实施；本轮不编译未改应用、不执行DB/服务操作 | 本轮文档完整性/JSON语法与引用/样例执行/链接/空白/范围检查，实际结果见阶段报告；业务及迁移与HEAD无差异 |

## 3. 复审与停止点

本轮交付共11份Markdown：原九份局部修订、新增本响应、更新PHASE_10A报告。Git工作区起点已有未跟踪设计文件，本轮未暂存/commit/push；“提交审查结果”指交付复审材料。未自行执行10B-1计划、未修改数据库或业务代码，10B-2未开始。

请按R1–R4与S1–S5复审；全部运行验收保持未执行状态。复审通过及明确授权10B-1之后，才按09列出的数据安全候选计划推进，阶段报告后再次停止。
