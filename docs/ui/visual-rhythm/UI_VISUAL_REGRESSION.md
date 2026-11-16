# 前后视觉复核

对比入口：output/ui-review/visual-rhythm/index.html，可选择页面/状态/尺寸及底部、概念卡局部。共171组配对视图，逐文件SHA记录在screenshot-manifest.json。

最终配对截图均来自production构建，同一Chrome、相同合成账户、相同视口和真实数据。空态和有数据态分别使用固定账户；不把不同数据状态作为前后对比。报告生成时间、已流逝时间和Quiz选项随机顺序属于动态内容，不要求逐像素一致。

应用在main-shell内部滚动，浏览器fullPage截图不能自动展开这个滚动容器。为此保存顶部与实际滚动到底的-bottom.png；概念卡另外保存完整section截图。登录页也有内部滚动，注册截图在真实切换按钮自动滚入表单后保存，不把它误称为整页长图。

| 代表证据 | 人工复核结论 |
| --- | --- |
| before/after-concepts-1440.png | 标题、说明、操作、卡片与分页清楚分层；0→24px；无需增添阴影或粗边框 |
| before/after-concepts-390.png、review-390-bottom.png | 工具栏自然分两行，距面板20px；图标标题紧凑；底部文字有16px组间距与页面安全空间 |
| before/after-populated-concepts-1440.png | 真实beside概念卡5条来源；按钮、提示、来源和末尾说明可辨；无大空面板强行拉高 |
| before/after-populated-review-390-bottom.png | 中文、日期和来源计数自然换行，按钮在卡片内，分页不贴边 |
| before/after-reports-1440-bottom.png | 原相邻明细卡贴靠消除，统一24px模块间距；无额外大卡片嵌套 |
| before/after-settings-390.png | 表单和操作区保持紧凑；卡片内20px留白，按钮不超屏 |
| before/after-login-768.png、register-320.png | 保留原品牌双栏/手机单栏，字段关系与切换按钮/说明分离 |
| before/after-lesson-dictation-1440.png、lesson-writing-390.png | 保留224px桌面导航和76px播放器；主/助教约2:1；Tab换行与工作台滚动保持可用 |

还对首页、目录、报告、精读、口语、Quiz与平板截图进行了文件与几何检查。人工视觉观察是代表性复核，不假称逐一由真人审核了所有171组；主要界面全量几何检查与代表性审美复核分别报告。

综合判断：原最显著的按钮贴卡片、复习模块贴靠、报告明细卡无间距、登录操作贴说明已改善；保留学习工作台的信息密度，没有将每项内容改为超大卡片。
