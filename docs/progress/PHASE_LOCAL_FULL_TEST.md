# 测试服完整测试记录

日期：2026-11-11。结论：服务可用，学习闭环通过；数据库全量回归未通过。

## 服务与环境

- Web `127.0.0.1:3100`、API `127.0.0.1:8085`、MySQL `127.0.0.1:3308` 正常；两路 health UP，migrationVersion=013.04。
- 上轮受限环境 curl 失败不能证明服务退出，本轮在可访问宿主机的环境中纠正该结论。
- 项目 Node22/npm10/Java21，通过 `scripts/local.py exec` 选择，未修改全局版本。
- 启动沿用 `scripts/dev-up.sh`。数据库写测试使用新建的 `retest-20261111`、`retest-20261111b` 隔离容器，保留失败现场。

## 执行结果

| 检查 | 结果 | 日志 |
| --- | --- | --- |
| 前端单元 | 43/43 PASS | `.local/test-web-20261111.log` |
| 类型检查 | PASS | `.local/test-typecheck-20261111.log` |
| ESLint | PASS，既有 KnowledgeConcepts.tsx 未使用 busy 警告 | `.local/test-lint-20261111.log` |
| Java 非数据库配置 | 55项，0失败0错误，33跳过；解除 JVM 附加限制后成功 | `.local/test-java-20261111-unrestricted.log` |
| 隔离 API/Web 构建 | PASS | `docs/handoff/evidence/phase10e/retest-*-build-*.log` |
| 工具测试 | 24/24 PASS；需要允许临时 HTTP 监听 | `.local/test-python-20261111-unrestricted.log` |
| 既有浏览器冒烟 | PASS，真实健康、加载/503/恢复、键盘、四档尺寸 | `.local/test-browser-20261111.log` |
| 完整学习闭环 | PASS，真实播放、听写幂等、阅读来源、作文两版、测验到复习、草稿恢复；pageErrors=[] | `.local/test-learning-loop-20261111.log` |
| 隔离数据库全量回归 | 55项，52通过、1失败、1错误、1跳过 | `docs/handoff/evidence/phase10e/retest-integration-aligned-20261111-1794384111275932000.log` |

闭环结构化结果：`docs/handoff/evidence/phase10e/demo-browser-result.json`。截图：`output/playwright/phase10e-demo/`；实际查看了 workbench-1440.png。

## 已复现问题

1. 首轮隔离配置 WEB_PORT=13185 与两个知识测试固定 Origin=3196 不一致，造成403。第二轮新库对齐3196后，ConceptReviewIntegrationTest通过。
2. KnowledgeNormalizationIntegrationTest:38 查询全部 bank/vocabulary，期望1但返回3。只读确认另外两行是导入测试建立的 sample-bank-finance、sample-bank-river-edge，存在测试数据范围相互影响；该结果不能证明二进制排序规则失效。
3. KnowledgeSourcesIntegrationTest:407 清理 sentence_identity 时，被 sentence.fk_sentence_identity 拒绝。清理按固定版本删除句子，仍有引用身份的句子残留；需进一步检查测试版本清理范围。

本轮未修改业务代码或测试断言以掩盖失败。

## 限制

- 真人麦克风、真实声音质量和许可人工验收未测；浏览器闭环录音步骤为明确跳过。
- 有一项环境条件测试跳过，不能把全套测试宣称全部通过。
- 本报告不代表10E人工审核或10F启动授权。
