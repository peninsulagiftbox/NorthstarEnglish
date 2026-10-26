> 当前 Phase 09-R（2026-10-26）已完成固定候选隔离复验，见 [09-R 报告](PHASE_09_R_ACCEPTANCE_REPORT.md) 与 [矩阵](ACCEPTANCE_MATRIX.md)。下文为此前交接审计原文，保留当时结论与证据边界，不能替代本次结果。

# 已知问题、证据缺口与风险

2026-10-26。严重度用于安排独立复核顺序，不等同已证明生产故障。全部仅记录，未修复。

| ID | 类型/影响 | 证据与复核方向 |
|---|---|---|
| K01 | 发布阻塞：原创文本与配音来源仍 pending_review | content/demo-01/v1/manifest.json、v2/manifest.json 的 licenses/releaseReady；不能因已能播放而批准分发。ZIP不含MP3或原型二进制 |
| K02 | 验收证据不一致 | IMPLEMENTATION_PLAN 顶部 Phase09未开始；PHASE_09/TEST_REPORT仍BLOCKED；当天原始日志已部分成功。以本交接逐项证据表核查，不能任选最乐观描述 |
| K03 | 安全门禁仅有其他执行成功证据，本次未独立复验 | 初次security-runtime.log为Build assets missing；后续security-runtime-final/security-delivery有passed:true，27份JS资产。本次未重跑，退出码未知；保留失败/成功两类，不推断凭据泄露 |
| K04 | 重复启动/恢复收尾证据缺口 | 初次repeated-init构建失败，最终repeated-init-final成功。新增restore-values/续学/重启/重访支持37表与1份隔离媒体，但recovery-restart-continue中还有HTTP422；本次未独立重复，不能证明所有私人媒体或新机恢复 |
| K05 | 本次执行环境阻塞 | Python10项8通过2Error（ps、回环绑定）；Java12项6通过6Error（Mockito自附加）；GET全被回环权限拒绝。本机权限重试被自动审批拒绝，未绕过；纯Java6项另跑通过 |
| K06 | 四册扩展存在硬编码和结构约束 | ContentPackage/ContentSeeder 固定demo-01、10句、3题；V002 book只catalog_only、start_ms=0和音频唯一；V007及ReportController固定3题。详见扩展评估 |
| K07 | 设备与跨平台未验收 | 实体Chrome/Safari麦克风、Firefox、真实手机、后台节流及辅助技术未测；虚拟麦克风不替代实体验收；本次未逐图检查旧截图 |
| K08 | 录音与未同步草稿备份边界 | RecorderPanel/recording目录未加密；文件和SQL非原子；JSON export不含录音Blob和浏览器缓冲；Origin变化/存储清除会丢未同步草稿 |
| K09 | 长期记录/大规模性能未证明 | ReportController逐版本多查询、阅读历史无分页；ExportController全表内存快照；课程payload整课返回；无大量课次/多年记录基准测试 |
| K10 | 兼容性证据有限 | stable_key版本内唯一，不提供跨版本拆句/合句映射；导入要求相同schema/内容基线，无通用跨教材升级或回滚工具 |
| K11 | 人工协调Flyway历史需专项复核 | 原 docs/progress/PHASE_08.md“补充恢复、安全与运行交付”记载：V008 ALTER已提交但登记超时，后人工复制已核对迁移签名并execution_time=0；本次不读私有DB/日志，无法独立确认实际DDL和历史表完全一致。不得隐去或声称自动迁移全程无异常 |
| K12 | 本地无认证边界 | LocalAccessFilter和回环约束不是账号认证；仅本机个人使用；本次未实际验证监听/所有安全响应 |
| K13 | 学习证据是行为观察，不是能力评分 | audioPlayed/answerExposed/播放时长/翻卡依赖客户端；simple_v1是人工自评调度；AI/ASR/音素评分未实现，前端已明确标记 |
| K14 | 源码交付不能独立复现音频闭环 | MP3因授权和二进制排除不入包；ContentPackageTest.loadsRealFrozenBundle和API启动需要原哈希素材。不得用重生成音频补位后宣称同一构建/数据验收 |
| K15 | 当前工作区不是已提交发行版 | HEAD停在Phase08，Phase09文件和部分现有脚本/CSS/README未提交；GIT_CHANGE_SUMMARY和基线哈希明确记录。ZIP为工作区快照，无签名发行标签 |

未发现问题不等于已证明无问题：本次没有执行依赖漏洞扫描、渗透测试、数据库损坏演练、长时间性能测试或真实用户学习成效评估。这些不记PASS。
