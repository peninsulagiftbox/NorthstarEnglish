# Phase 10D-QA R7 独立恢复验收

日期：2026-11-04（Asia/Shanghai）。结论：**D01-M04、D01-M05 与建议 M06 PASS。**

## 源数据与身份

- 源容器 3385，UUID `35965c3f-d823-11f1-be71-b6b8e525f6a4`，独立数据卷。
- 源库包含旧 Demo、课程、知识概念与来源、旧句卡、Quiz、写作草稿/修订、3 行 `knowledge_occurrence.location_guard`、1 条 13,820 字节原创浏览器合成录音。
- 录音 SHA-256：`629c780a219ee8f034a6c514f7c89cd100f2efe5707b325d27c68ca8315ddd05`。
- 源容器在 3397 导出前曾 OOM（退出 137）；扩容到 2 GiB 并重启后核对 UUID、写作 1/2、录音 1、Quiz 2、概念来源 8、生成列 3 行一致。OOM 属测试容器资源限制，不判业务缺陷。

## 3397 final2 恢复

- 目标容器：`northstar-qa-final-r7-restore-final2-20261104`，端口 3397。
- 目标 UUID：`1535b7bf-d856-11f1-84a9-7acea4c389b4`，独立卷 `northstar-qa-final-r7-restore-final2-20261104-data`。
- 数据由原版 `data-transfer.py backup` 和逐表逻辑恢复链生成；首次尝试遗留的 0 字节 `source.sql` 已改名为 `source.failed-first-attempt.sql`，未被覆盖。
- 59 张表逐 PK/逐值与源库一致；`flyway_schema_history` 尾部为 012.11。
- 生成列 `knowledge_occurrence.location_guard` 3 行；录音文件 SHA-256 与数据库元数据一致。
- 备份 SHA-256：`153013404a0378883c923a9eeb5e65b24dccdb55d163c58e42ad485e4192a1d1`；history 文本 SHA-256：`6182ace2d4cfc701510926216981d17d9efcff9de7090d16a9034993a67e2bd0`。

证据：`qa/phase10d-final-r7/evidence/r7-independent-restore-final2-result.json`。

## 恢复后真实续学

- 独立 API 读取 4 门课、2 个概念、8 个旧概念来源。
- 录音 API 返回原始字节，SHA-256 与源库一致。
- 新增阅读 Attempt：eventId `217ee9a4-5d9d-450e-9b66-e595356b6511`，attemptId `0c55145b-8a9f-49dc-9e4b-67fbf4a8a577`。
- 同 eventId 重放返回相同回执；旧 Quiz、旧录音和 `review_result` 哈希不变。
- API 重启后关键表哈希一致，health 报告 012.11，录音再次读取一致。

证据：`qa/phase10d-final-r7/evidence/r7-recovered-study-result.json`。

## 3386 首次用例

3386 目标 UUID `2b242be2-d824-11f1-baec-767a5e58531a` 也完成 59 表、生成列和录音恢复，并曾通过续学；其结果保留为 `r7-independent-restore-result.json` 与 `r7-recovered-study-first-result.json`。最终验收以 3397 为准，因其覆盖完整写作历史。

## 剩余缺口

备份 `COMPLETE` 标记缺失仍被接受是独立恢复安全缺口，见最终验收入口；本报告的 PASS 仅限定数据、媒体和续学恢复本身。
