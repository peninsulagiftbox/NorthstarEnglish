# 最小冻结候选：段落与同版句关联

仅用于明确隔离的10B-1演练，不在源应用默认迁移目录，当前未应用。源码基线HEAD为98bfedc8ac43ab68aea5447f2790cd3777b0a764；四份候选文件hash单列于candidate-manifest.json，不称为已提交的新commit。首次应用后文件冻结，后续变化必须重做双路径/恢复。

| 版本 | 改动 | 前置断言 | 后置断言 |
| --- | --- | --- | --- |
| 009.01 | 新paragraph表 | V008实际结构/history匹配；无同名表 | 表/3个唯一键、sequence正值CHECK、version FK存在；旧表旧列逐值不变 |
| 009.02 | sentence新增可空paragraph_id | paragraph存在；原sentence无该列 | 新列NULL；旧列逐值不变；旧索引/FK/CHECK全部保留 |
| 009.03 | 两版Demo派生段落与新列回填（独立DML事务） | lesson仅demo-01；version恰demo-01-v1/v2；每版10句，paragraph空 | 2段/20关联，全部同版；所有原列/旧行/旧hash不变 |
| 009.04 | 新列NOT NULL、新索引、同版FK | 全部关联非空且同版 | 约束正反例有效；旧列逐值相同；新列按上述固定映射白名单比较 |

白名单仅新paragraph全表和sentence.paragraph_id，不允许修改任何原列，包括payload/hash/ID/事件/草稿/作文父链/复习/录音状态。四个文件按独立恢复状态拆分；不改V001–V008，不实现身份登记/发布业务或UI，不扩展音轨/题量/知识/导入/教学。

空库路径明确在V001–V008后、此候选前，用冻结旧应用在隔离空目标播种原Demo；随后应用相同四文件，再用只追加这四SQL的隔离JAR验证重复启动。不能先加NOT NULL再让旧播种器插入无paragraph_id的新句。此顺序不是完整新应用初始化能力验收；10B-2若改初始化或DDL须重做对应安全演练。

候选每个DDL文件单语句，边界保存schema/history与旧列快照；009.03每条DML记录语句hash/日志并验证事务。故障目标不得repair/clean/删除；部分成功状态不是可整体ROLLBACK。
