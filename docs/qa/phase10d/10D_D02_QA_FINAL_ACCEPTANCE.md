# Phase 10D-D02 QA 最终验收（P1修复候选待复测）

日期：2026-11-02。上轮独立QA结论：**FAIL**。当前状态：**CORE已修复，等待新候选独立QA复测**。

QA-D02-R4-BUG-001已在CORE定向修复：受限字段裁剪前保存游标；同时修复合法occurrence ID游标被误判422的问题。CORE在新3373测试库完成红绿验证及7/7相关集成回归，并用新JAR在原3364失败库完成只读HTTP/真实浏览器验证，数据库全表哈希未变。

新JAR SHA-256：771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6。
新336项输入清单SHA-256：31131ea6b5a92b87ff12d32e61ad6fef9896e2028d16ecba5b7e9368f60b1a6c。

交付：output/review/northstar-phase10d2-p1-candidate.jar 与 northstar-phase10d2-p1-sanitized-evidence.zip。
详细改动、运行日志、范围与未重复测试项见 docs/progress/PHASE_10D_2_P1.md。

历史失败及最小复现见 [风险补证报告](10D_D02_QA_RISK_CLOSURE.md)。原R1/R3/风险补证证据包保留；旧JAR结果仅归属旧候选。独立QA应按新JAR重新执行受限分页与浏览器展示回归，完成后再决定最终PASS与用户签收。

本轮CORE自测不替代独立QA签收；未部署、未提交或进入10E。
