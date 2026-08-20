# 第十一届湖南省研究生数学建模竞赛 · 结构化文档

本目录是 `competition_question/` 原始赛题包的结构化转写，供建模、数据读取与论文撰写使用。原文 PDF / Excel / Word 仍以赛题包为准。

## 文档地图

| 文档 | 内容 |
|------|------|
| [contest/notice.md](contest/notice.md) | 竞赛通知：组织、时间、提交、评审 |
| [contest/paper-format.md](contest/paper-format.md) | 论文格式、命名与压缩包提交规范 |
| [contest/commitment.md](contest/commitment.md) | 参赛承诺书要点 |
| [problem-A/problem.md](problem-A/problem.md) | A 题：无人车–无人机协同配送 |
| [problem-A/attachments.md](problem-A/attachments.md) | A 题附件数据字典与规模统计 |
| [problem-A/result-template.md](problem-A/result-template.md) | 问题 1 结果表填写说明 |
| [problem-B/problem.md](problem-B/problem.md) | B 题：区域电网碳流追踪与低碳调度 |
| [problem-B/attachments.md](problem-B/attachments.md) | B 题附件数据字典与字段说明 |
| [../references/README.md](../references/README.md) | A/B 题核验文献（每题 ≥20 篇） |
| [mineru/README.md](mineru/README.md) | MinerU 解析的赛题 Markdown 原文 |

## 赛题一览

| 题号 | 标题 | 子问题 | 核心对象 |
|------|------|--------|----------|
| A | 无人车-无人机协同配送优化问题研究 | 4 | 23 个物流节点、39 条干线、最多 1000 个需求点 |
| B | 考虑送端碳排不确定性的区域电网鲁棒碳流追踪与低碳调度 | 5 | 8 个区域、11 条输电通道、2026–2030 项目库 |

## 关键赛程（摘自通知）

- 竞赛时间：2026-08-20 08:00 至 2026-08-24 12:00
- 提交物：承诺书 PDF、论文 PDF、支撑材料 zip；由培养单位领队统一发送
- 论文命名：`选题+队号`，例如 `A202618001001.pdf`
- 正文不超过 25 页；附录须含主要源程序，否则按违规处理

## 转写约定

1. 公式、参数表、约束按题面整理为可引用的条目，不改写题意。
2. 附件以实际 Excel 为准；题面文字与表格不一致处，在对应文档中标明。
3. 原始路径均相对于项目根目录下的 `competition_question/`。
4. Excel 附件已转为 CSV，见 [`data/raw/`](../data/raw/README.md)。
