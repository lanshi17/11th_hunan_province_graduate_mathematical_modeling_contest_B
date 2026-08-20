# 原始表格 CSV

由 `competition_question/` 中的 Excel 附件转换，编码 UTF-8（带 BOM），每工作表一个文件。多表工作簿文件名形如 `附件1_A_区域月度监测.csv`。

字段说明见：

- [docs/problem-A/attachments.md](../../docs/problem-A/attachments.md)
- [docs/problem-B/attachments.md](../../docs/problem-B/attachments.md)

B 题部分 CSV 保留了 Excel 中的标题行、空行和表末说明，读取时需跳过元数据行。
