# UI 视觉节奏专项

2026-11-16。UI_VISUAL_RHYTHM_PASS，等待用户人工审阅，不部署。

只在独立UI工作树实施，保护主工作区G2/G3混合改动。6个产品文件：globals.css、review/page.tsx、LearningReport.tsx、LessonWorkspace.tsx、ReviewQueue.tsx、ConceptReviewQueue.tsx；新增scripts/ui浏览器证据驱动与docs/ui/visual-rhythm八份报告、docs/ui/spacing-audit.md入口。账号前端与CSS原有变更属于继承基线。

扩展既有root间距token，复习父Grid负责工具栏/结果24px（手机20px），结果/分页16px；空态280/240px，报告面板24/20px，页面最大宽1600px。保留224px桌面导航、76px播放器和滚动约束。

7个实际路由、13个界面状态，11个根因问题（P0 0/P1 4/P2 7）已处理。typecheck、lint（1既有warning）、43项Node测试、独立production build通过；前后各81检查组合，171组配对截图；75个受保护+6个auth组合的指定几何关系通过；14项生产交互与加载/失败/恢复通过。

截图：output/ui-review/visual-rhythm/；交互式对比index.html；指标、断言与候选SHA清单同目录。完整决策、命令结果、初期失败、未测试边界与G3新候选交接见docs/ui/visual-rhythm/。

未执行Java/数据库迁移或业务代码修改；专用API使用冻结JAR、既有v5合成库，启动确认019.03无新迁移。新Web BUILD_ID mCLsBtsPLlGOc1mzMjcxn与冻结aBTmXloOWxhDVxC7oGAjD分开，测试代理5197不能当作正式配置。

下一步：用户审核UI效果；若要进个人Beta，按目标配置重新构建、回归、更新manifest及正式审批，等待新候选明确部署授权。本轮不自动commit/merge/push/deploy。
