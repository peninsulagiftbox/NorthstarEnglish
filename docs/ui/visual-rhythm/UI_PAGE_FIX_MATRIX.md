# 实际页面与修复矩阵

7个实际主路由、13个主要界面状态。/仅重定向到/dashboard，单列为路由检查、不计页面。不存在独立课程详情、概念卡、学习计划、内容管理或账号资料路由。

| 路由 | 实际界面/模块 | 处理与证据 |
| --- | --- | --- |
| /login | 登录、注册模式 | 字段16px、label/input8px、切换按钮与本地说明24px；before/after-login-*、register-* |
| /dashboard | 首页、六步学习路径 | 共用报告布局、统计卡和页面容器；dashboard-* |
| /courses | 目录、原创课程、实际课程弹窗 | 书卡网格间距统一；弹窗已有布局复核、实际开启/关闭；courses-* |
| /lesson/[lessonId]?tab=text | 课文/句子助教/播放器 | 保留现有滚动布局，正文/助教2:1；lesson-text-* |
| 同路由 tab=dictation | 精听听写 | 共用Card/工具栏/主容器，保留听写逻辑；lesson-dictation-* |
| 同路由 tab=vocabulary | 精读、阅读题、概念入口 | 保留词卡密度；共用布局与按钮换行；lesson-vocabulary-* |
| 同路由 tab=speaking | 口语录音 | 只复核布局，无虚构录音/评分；lesson-speaking-* |
| 同路由 tab=writing | 写作与版本 | 共用布局，保留原草稿/版本处理；lesson-writing-* |
| 同路由 tab=quiz | Quiz和结果历史 | 共用布局；用真实错题产生有数据状态；lesson-quiz-*、populated-quiz-* |
| /review | 句子卡、跨课程概念卡 | 工具栏/结果分离、模块分区、空态和分页底部；review-*、concepts-*、populated-review-* |
| /reports | 学习统计、交卷与阅读历史 | 父Grid24/20px统一面板节奏、移动端说明换行；reports-*、populated-reports-* |
| /settings | 偏好、健康、数据迁移工具 | 共用网格和Card、移动端字段说明；settings-* |

每种受保护界面覆盖1280×800、1440×900、1920×1080、768×1024、390×844、320×844。登录/注册同6档；有数据状态额外覆盖1440/768/390。截图文件位于output/ui-review/visual-rhythm/，前缀before-/after-，主区滚动底部另存-bottom.png。
