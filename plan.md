# 方案

要依次调用这些 skill，按照里面要求完成任务。

用户偏好（沿用已有工程，不重建目录骨架）：
- 排版引擎：LaTeX（`paper/main.tex`，xelatex 两遍）
- 竞赛类型：第十一届湖南省研究生数学建模竞赛
- 论文语言：中文
- 子问题数量：已知 5 个（问题一至问题五）
- 本轮性质：在已完成的 Q1–Q5 管线与 16 页论文上做加分向优化，不改主方案数值

已有工程布局（不迁移到 skill 默认的 `code/` / `figures/`）：
- 代码：`src/q1_reconcile` … `src/q5_report`、`src/deepen`
- 结果与数据图：`src/outputs/q1` … `src/outputs/deepen`
- 论文：`paper/main.tex`
- 建模底稿：`docs/problem-B/plan.md`

workflow:
   step      skills
1. 赛题分析与建模设计 - `2analysis-modeling`（已完成；本轮只核对题面覆盖缺口）
2. 编程实现和图表生成 - `3coding-visual`
3. 流程与架构图绘制 - `4drawio`（路线图用 TikZ 嵌入论文，保证与正文字体一致）
4. 竞赛论文撰写 - `5writing`
5. 验证和验收 - `6verity`

本轮优化目标（按题面得分点，不改 985.5 / 454.5 / 4848.8 等主数字）：

1. 问题一：残差热图色标截断于 ±6 却未标出 z=32.5；影响度只有文字、没有图。
2. 问题二：题面要求“追溯来源”，`fig_q2_origin_mix` 已生成但未入正文；水电区季节性碳势缺少来源分解对照。
3. 问题三：开工热图默认插值，看起来像半年连续条，与逐年开工决策不符。
4. 问题分析：写了“技术路线如图式所示”但没有图。
5. 写作：正文泄露 `src/outputs/`；图内重复写大标题（应交给 caption）。
