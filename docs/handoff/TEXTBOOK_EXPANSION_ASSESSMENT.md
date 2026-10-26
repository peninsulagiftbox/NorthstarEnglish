# 四册教材扩展能力只读评估

2026-10-26。结论：**存在版本化和关联完整性的基础，但当前实现不足以直接承载四册真实课程。** 不提供工期承诺，不实施扩展，不导入版权教材；以下能力均未经过大数据量实测。

| 需求 | 当前基础 | 明确约束/风险 | 结论 |
|---|---|---|---|
| 四册及大量课次 | book/lesson/lesson_version、4册目录144/96/60/48声明课数 | V002 book availability只允许catalog_only；ContentPackage 固定demo-01/10句；ContentSeeder固定源句/知识点/题量；列表/报告/导出无规模验证 | **现状不支持直接扩展** |
| 不同教材版本 | book.catalog_key/edition_label复合唯一；lesson_version版本号/哈希/许可/当前指针 | 教材edition与内容修订是两个层次；暂无教材版本导入/选择/课程对齐流程；当前API/UI主要演示单课双版本 | **模型部分具备，流程NOT VERIFIED** |
| 长课文与稳定句ID | sentence TEXT、独立ID、stable_key/sequence，历史引用带version | ContentPackage固定10句；ID路径正则仅01–10；无拆句/合句映射契约；整课payload/DOM/列表无长文性能数据 | **需要实现和迁移，性能NOT VERIFIED** |
| 整课音频与逐句时间戳 | audio_asset duration/hash，sentence start/end字段，v2词边界 | V002 start_ms必须0；sentence.audio_asset_id唯一；一文件一句；AudioController使用独立句文件，当前AB句内；词点不是整课对齐 | **现状不支持共享整课音频** |
| 词汇/语法/练习跨课关联 | knowledge_point/exercise带课/版本/句，复合FK保证来源正确；写作多源句 | knowledge_point绑定单课单版本，reading/quiz FK绑定同一句；缺独立跨课概念层、关系表和多源知识点模型；语法是预置说明 | **课内具备，跨课不具备** |
| 大批量导入与失败回滚 | manifest/哈希/来源校验；ContentSeeder先校验包再事务写；全局身份行锁 | 只处理固定Demo已发布版本；无通用批次/预检/进度/逐条错误/断点/内容回滚接口；MySQL DDL和媒体操作不能整体回滚 | **不具备通用批量导入** |
| 学习记录长期兼容 | 事件幂等、历史版本保留、复合FK、不可变尝试/作文、调度版本字段 | 不保证旧素材永远可取得；内容撤回/授权过期/拆句对齐未形成策略；备份预检拒绝不同内容/迁移基线；V008人工登记历史需复核 | **当前同基线兼容有历史证据，长期升级NOT VERIFIED** |

## 关键依据

- `apps/api/src/main/java/local/northstar/catalog/ContentPackage.java`：load/publishedVersions/checkedAudio 固定demo路径、10句、4个catalog_only；版本号限制小于100。
- `catalog/ContentSeeder.java`：demo当前版本更新、固定第6句/词项、写作3源句、quiz要求3题；导入事务只保证这个已知包的DML。
- `apps/api/src/main/resources/db/migration/V002__catalog_content_versions.sql`：book、sentence的CHECK/UNIQUE/FK；V005/V007的知识点和题目上下文FK。
- `exercise/QuizReviewController.java`、`report/ReportController.java`、Web `QuizPanel.tsx`：3题要求、正确数/分母/UI提示共同固定。
- `exportimport/ExportController.java`：整库tables入内存、同schema与CONTENT逐值匹配预检；`scripts/data-transfer.py`：恢复新目标及SQL/媒体分离，不是教材导入器。
- `apps/web/src/lib/media/{AudioController,timeline}.ts`、`demo-word-timings.json`：单句音源/特定Demo词点，不能等同整课级对齐。

## 独立审查时应验证的风险

先确认内容权利、全局稳定ID与教材edition/课文修订语义，再验证多课样本下的FK、旧作答可读性、共享音频时间轴和迁移策略。批量导入需证明在校验失败、DML失败、DDL部分成功、磁盘写失败下分别保留哪些状态；不能承诺“一次事务全部回滚”。规模测试需要独立授权的数据集，不能在现有学习库伪造348课或学习记录。

这些是评估结论和后续验收条件，不是本次开发计划或阶段启动授权。
