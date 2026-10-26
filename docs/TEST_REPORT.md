# Phase 09 最终测试报告

日期：2026-10-26（Asia/Shanghai）。本地核心工程 **PASS_WITH_NOTES**。完整命令、失败与修正、截图和边界见 `docs/progress/PHASE_09.md`；原始证据在本地忽略目录 `docs/evidence/phase-09/`，trace位于`.playwright-cli/traces/`。

| 层 | 真实结果 | 主要证据 |
|---|---|---|
| 依赖/构建 | 锁文件安装通过；Node22/npm10/Java21；Web typecheck/lint/25项单测/生产build通过，未改依赖 | npm-ci、npm-versions、typecheck-final、lint-final、web-tests-final、main-web-final-deploy.log |
| Java/MySQL | 真实MySQL8.4/schema008，20项，0失败/错误/跳过，生产包成功 | api-verify-resume.log |
| Python保护 | 12项通过；此前沙箱2项Error已在本机重跑通过 | python-delivery.log |
| 学习闭环 | 新浏览器→课程→第6句→盲听错答/回听→阅读证据→跟读跳过→作文两版/独立草稿→错测验→到期翻卡自评→刷新，passed=true/pageErrors=[] | full-learning-loop-20261026143113.txt |
| 故障/媒体 | 音频404重试、真实离线草稿、500/导出失败注入、麦克风拒绝/虚拟录音真实解码/轨道释放、快速切句和焦点，passed=true/pageErrors=[] | release-boundaries-20261026143219.txt |
| 全新实例初始化 | 新MySQL空应用库迁移到008、两内容版本20句、37表重复初始化hash相同、零历史；新浏览器零数据首页→课程→10句 | fresh-mysql-init/fresh-browser.log |
| 独立恢复 | 新容器/卷3310、新schema，37表逐值相同、1份ready媒体大小/SHA一致；新浏览器草稿/历史/复习与录音实际解码 | recovery-mysql-start、restore-values、revisit-source、revisit-restore.log |
| 重启/续学 | 独立DB真实停止503→重启恢复；真实浏览器播放原句后提交；同event只计一次；续学后API重启37表及媒体相同 | recovery-restart-continue、restore-continued-browser、restored-after-continue-restart.log |
| 拒绝恢复 | 已存在目标、损坏checksum、缺ready媒体拒绝；失败包没有创建目标schema | restore-rejections.log |
| 安全 | Host/Origin/写标记/MIME/CORS拒绝、回环绑定、no-store/nosniff、27份JS/HTML无配置秘密、应用日志不含秘密/测试原始输入 | security-delivery、api-smoke-delivery.log |
| 基础UI | 1440/375无溢出、播放器边界、控件标签、键盘/弹窗焦点；抽样辅助文字对比度≥4.7039 | ui-final、main-readonly-retest.log、截图audit-* |
| 主站保护 | 原学习历史36表逐值未变；一次延迟测试请求改变浏览恢复点，已严格核验后CAS恢复原字段，只版本/更新时间前进。只读拦截修正后复验无写入 | main-resume-reconcile-final、main-readonly-after-final.log及主站trace |

不可冒称已验：Chrome/Safari实体麦克风、Safari/Firefox全流程、另一台Mac安装/灾难恢复、完整WCAG合规、依赖漏洞清零或模型调用。无AI/ASR/专业发音评估属既定产品边界；内容/声音授权pending_review继续阻塞素材正式发布。
