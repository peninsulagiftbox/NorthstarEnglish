# 布局组件变更

实际产品变更限6个文件，不修改Java、SQL、API客户端、评分、调度和统计公式。

| 文件（仓库相对路径） | 改动 |
| --- | --- |
| apps/web/src/app/globals.css | 扩展现有root间距变量；统一页面宽度、Card/工具栏/EmptyState/报告布局；移动端工具栏和页头换行；登录字段及操作/说明分隔 |
| apps/web/src/app/review/page.tsx | 句子队列标题归入对应section，移除散落的eyebrow标题 |
| apps/web/src/components/review/ReviewQueue.tsx | 具名section、标题说明header、工具栏与结果Grid分组；原处理函数、请求和条件不变 |
| apps/web/src/components/review/ConceptReviewQueue.tsx | 同上；分页计数放在结果组内，父容器统一处理留白 |
| apps/web/src/components/LearningReport.tsx | Fragment改为report-layout容器，以gap统一面板间距；指标与文案表达式不变 |
| apps/web/src/components/lesson/LessonWorkspace.tsx | 内容来源弹窗的版本链接改用既有toolbar，避免相邻按钮贴靠 |

共享Card、Button、EmptyState仍复用Primitives.tsx，未新增只包div的React组件。Tabs仍是既有LessonTabs。没有独立PageHeader/Form组件，不凭空引入新封装；登录字段继续使用原生label/input。

工作树继承了主工作区此前的登录页与AppShell账号实现，以及globals.css已有改动；它们是截图和构建基线，不是本次UI新增功能。审查应以baseline-build与build-source的6个源码差异为准，详见output/ui-review/visual-rhythm/candidate-manifest.json。不能把git diff HEAD中的账号差异归为本次授权修改。

Next开发命令自动生成apps/web/AGENTS.md、next-env.d.ts；依赖通过本机已有node_modules链接复用。它们不属于UI产品变更。构建产物、账户会话和原始日志留在忽略目录，不提交。
