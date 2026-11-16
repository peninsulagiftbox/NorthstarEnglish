# 全站空间审计

范围：7个实际主路由、13个界面状态；目录弹窗、来源弹窗、句子卡和跨课程概念卡作为页面内模块另查。原用户截图未附原图文件，以需求描述及本轮真实before截图为依据。源码HEAD与前后6文件SHA、BUILD_ID见candidate-manifest.json。

问题按根因合并，不把每个视口的同一缺陷重复计数：P0 0、P1 4、P2 7，共11项。以下为本轮确认并处理的问题；未发现关键操作不可访问的P0。

| ID | 优先级/类型 | Route / 页面 | Before截图（output/ui-review/visual-rhythm/） | 组件/规则与具体问题 | 修复策略 |
| --- | --- | --- | --- | --- | --- |
| S01 | P1 分组 | /review 两类复习 | before-concepts-1440.png、before-review-390-bottom.png | ReviewQueue/ConceptReviewQueue，toolbar后直接Card，结果卡上间距0 | review-section父Grid统一gap24/20 |
| S02 | P1 贴靠 | /reports 报告 | before-reports-1440-bottom.png | LearningReport末尾两个无margin的Card直接相邻 | report-layout父Grid统一gap24/20 |
| S03 | P1 分区 | /review 复习 | before-review-1280.png | 前一空态后立即eyebrow和boundary，缺少模块独立层级 | section header+h2；异组40/32上间距及32/24内距 |
| S04 | P1 贴靠 | /login 账户 | before-register-1440.png | auth-switch紧贴login-local-note，两个圆角控件边界相接 | 切换区下24px，字段密度保留 |
| S05 | P2 底部 | /review 概念卡 | before-concepts-390.png | 分页计数段落紧贴Card，margin-top为0 | review-results父Grid16px，页面底部32/40px |
| S06 | P2 空态比例 | /review、/courses | before-concepts-1440.png | 通用45px垂直padding、40px图标和段落margin叠加，内部组合松散 | 图标32px、组内gap12；复习面板280/240最小高，内容自适应 |
| S07 | P2 文本行宽 | 全站、大屏 | before-review-1920.png | main无max-width，长说明跟随可用空间延伸 | main最大1600px，复习说明85ch |
| S08 | P2 节奏一致性 | /dashboard /courses /settings /reports | before-dashboard-1440.png、before-settings-768.png | 网格20px与报告20/0px混杂，Card末段margin增加不一致内距 | 共用panel-gap与Card尾项归零；不改任务密集组件 |
| S09 | P2 按钮分组 | /lesson/[lessonId] 来源弹窗 | 由源码确认，原弹窗布局人工交互复核；无弹窗before单图 | LessonWorkspace版本链接连续输出在p中，没有按钮gap | 改用既有toolbar、自然换行，不改版本链接 |
| S10 | P2 对齐 | /reports /settings | before-reports-390.png | service-list的dt/dd在窄屏自然挤压换行，说明起点不稳定 | 窄屏dd整行左对齐、组内8px；文本可换行 |
| S11 | P2 表单节奏 | /login 注册 | before-register-390.png | auth-form字段14px、label-input6px；与全站刻度未统一 | 复用16px字段间距、8pxlabel-input；移动页头允许换行 |

静态范围审计还检查了App Router layout、全局CSS、现有brand tokens、Primitives、LessonTabs、CatalogPages、LearningReport、SettingsPanel及工作台六Tab。没有额外Tailwind配置文件；Tailwind4由现有PostCSS接入。课文的最小高度是现有保滚动约束，本次不将其误判成复习空态问题。

不适用：没有表格筛选页、图表页、独立账号权限页或内容管理Web页，未虚构这些页面的PASS。麦克风实体权限不是本次间距缺陷，记录在测试边界中。
