# MinerU 结构化原文

用 MinerU 精准解析 API（`model_version=vlm`，公式+表格开启）从 `competition_question/` 提取。Token 仅用于本次调用，未写入仓库。

| 文件 | 原文 | MinerU Markdown |
|------|------|-----------------|
| A 题 | `competition_question/A题/A题.pdf` | [problem-A.md](problem-A.md) |
| B 题 | `competition_question/B题/B题.pdf` | [problem-B.md](problem-B.md) |
| 竞赛通知 | `competition_question/关于举办…通知.pdf` | [contest-notice.md](contest-notice.md) |
| 承诺书 | `competition_question/（必读）…承诺书.docx` | [commitment.md](commitment.md) |
| 论文格式 | `competition_question/（必读）…论文格式规范.docx` | [paper-format.md](paper-format.md) |
| 问题1填表说明 | `competition_question/A题/附件7-….docx` | [attachment7-q1.md](attachment7-q1.md) |

各子目录的 `full.md` 为接口原始输出；根目录 `problem-A.md` / `problem-B.md` 为可读勘误版，修正了解析错误与组委会勘误。

人工整理版（字段、参数表、附件统计）仍以 [`docs/README.md`](../README.md) 为准；公式与表格版式以本目录为补充。
## 解析与勘误说明

以下内容保留在原始输出 `full.md` 中，根目录可读版已修正：

1. **A 题附件数据说明与相关参数的五处组委会勘误**：附件 1 的新增物流中心对应问题 4；附件 2 删除无人车行驶时间字段；附件 5 对应问题 3、问题 4；表 1 的 C 类时限包裹在问题三、四中考虑；表 3 的设备投资约束适用于问题 2–4。
2. **A 题表 2** 载重区间被识别错。正确为：
   - \(0<w\le 2\,\mathrm{kg}\) → \(40\,\mathrm{km/h}\)
   - \(2<w\le 4\,\mathrm{kg}\) → \(35\,\mathrm{km/h}\)
   - \(4<w\le 6\,\mathrm{kg}\) → \(30\,\mathrm{km/h}\)
3. **B 题公式 (1)** 右端第二项应为 \(\sum_{j\neq i} T_{i,j,t}\)（流出），MinerU 写成了与左端相同的 \(T_{ji,t}\)。
4. 页眉「第十一届…赛题」被重复抽成正文标题，可忽略。

