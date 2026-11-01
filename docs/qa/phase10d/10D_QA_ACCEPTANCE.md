# Phase 10D-QA 独立验收（第一轮）

日期：2026-10-31。结论：**BLOCKED（QA-PREP 完成；QA-EXEC 待 CORE 冻结候选与集成授权）**。

## 验收条目状态（对照任务书§十四）

| 条目 | 状态 |
| --- | --- |
| 1. D01 核心正反例实际通过 | NOT VERIFIED / BLOCKED_BY_CORE |
| 2. D02 并发/幂等/来源测试实际通过 | BLOCKED_BY_CORE（实现不存在） |
| 3. 非法跨课/跨版本数据不能入库 | 设计检查通过（复合 FK 设计正确）；实测 NOT VERIFIED |
| 4. 同形异义不错误合并 | 设计检查通过（kind+canonical_key+sense_key 唯一键）；实测 NOT VERIFIED |
| 5. Attempt 来源不可变、可追溯 | 服务端快照设计正确；SQL 层可变性 QA-BUG-003；实测 NOT VERIFIED |
| 6. 多来源复习卡不覆盖历史 | BLOCKED_BY_CORE |
| 7. 旧复习卡及旧测验成绩不变 | NOT VERIFIED（对账工具已备） |
| 8. 自评不伪造客观学习成绩 | BLOCKED_BY_CORE |
| 9. 新增迁移能安全恢复 | CORE 已声明 D-1 迁移演练 PASS；QA 复验 BLOCKED_BY_CORE |
| 10. 测试结果绑定真实候选版本 | 未绑定（候选未冻结） |
| 11. 无未解决 P0/P1 | **不满足**：QA-BUG-001（P1，STATIC）待 CORE 修复 |
| 12. 关键 PASS 有可追溯运行证据 | 不适用（本轮无运行时 PASS） |

## 最终建议

1. 不得宣布 10D 下一切片或 10E 进入条件满足。
2. CORE 优先处理 QA-BUG-001（lesson-scope occurrence 重复登记），并在冻结候选中给出 QA-BUG-002..007 的修复或书面裁定。
3. 冻结候选提供：commit SHA + 未提交文件 SHA-256 清单、隔离库授权入口、fixture 播种支持。
4. QA-EXEC 就绪：测试计划、fixture、SQL 负例、对账查询均已备（`qa/phase10d/`）。

本报告不构成对 CORE D01 实现的否认定论——静态发现需在冻结候选上实测确认后方可定级为最终缺陷。
