> 当前 Phase 09-R 固定候选复验见 [09-R 报告](handoff/PHASE_09_R_ACCEPTANCE_REPORT.md)。本地已测核心工程 PASS；公开素材授权 FAIL；全平台发布 NOT VERIFIED。以下为历史 Phase09原文，失败记录与当时标签保留。

# 本地交付与素材发布清单

截至2026-10-26。本地工程 **PASS_WITH_NOTES**，用户最终审核待完成。素材正式发布 **BLOCKED**。不能以本地测试结果替代内容权利审核或实体设备验收。

- [x] 项目Node22/npm10、Java21、Docker/Compose与MySQL8.4身份/回环端口核验；原服务恢复。
- [x] .env原字节/0600保留，重复init不覆盖；既有容器不重建，已有数据库卷未删除。
- [x] 锁文件安装、typecheck/lint/25项Web测试/build、20项Java/MySQL测试、12项Python保护测试实际通过。
- [x] 1440×900全学习闭环与375布局、故障/无AI/目录边界、幂等事件、特殊字符/XSS、键盘/焦点/抽样对比度通过。
- [x] 完整SQL逻辑快照+ready录音在独立新MySQL容器/卷/新schema恢复；37表/媒体核对、真实数据库停止/重启、浏览器续学和API再次重启通过。
- [x] 从新实例空应用库迁移/播种与重复启动不改37表；实际零数据API/UI和首次Demo入口通过。
- [x] Host/Origin/CORS/写标记/Content-Type、回环绑定、敏感值和应用日志检查通过，失败日志/trace保留。
- [x] 主站学习作答/作文/测验/复习/录音未新增或覆盖。一次测试恢复点变化已CAS恢复，row_version/updated_at前进；不宣称本轮主库零写入。
- [ ] Chrome/Safari实体麦克风允许、拒绝、刷新回放、人工自评由人工逐项记录；虚拟设备不代替。
- [ ] 另一台全新Mac复现、Safari/Firefox全流程验收。
- [ ] 补齐原创文本和合成声音的权利人/生成工具/许可与分发范围；当前pending_review、releaseReady=false，不公开分发素材。
- [ ] 用户最终审核与单独授权的Git提交/推送或正式发布。

AC-17跨设备同步和AC-18全课波形按一期范围延期；专业ASR、真实AI和更多课程须另行评审。本阶段不开展这些新模块。
