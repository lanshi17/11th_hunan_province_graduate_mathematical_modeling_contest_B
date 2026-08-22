# 提交与重打包报告

检查日期：2026-08-22。

## 结论

- **匿名论文与支撑材料：PASS，已重打包。**
- **对外发送：BLOCKED。** 承诺书目前仍是预填打印稿，没有三名队员、指导教师签名，也没有填写日期；不得把当前 ZIP 作为正式签字件发送。

## 最终预打包文件

- ZIP：`submission/B202618011017.zip`
- 论文：`submission/B202618011017.pdf`
- 预填承诺书：`submission/B202618011017_承诺书.pdf`
- 培养单位工作目录：`submission/交培养单位/`
- 重打包前旧版本备份：`_tmp/submission-pre-repack.tp1B2z/`

## 验收结果

| 项目 | 结果 | 说明 |
| --- | --- | --- |
| ZIP 完整性 | PASS | `unzip -t` 无错误 |
| ZIP 体积 | PASS | 6,775,701 bytes，约 6.46 MiB，小于一般 20 MiB 限制 |
| ZIP 条目数 | PASS | 190 |
| 顶层结构 | PASS | 仅 `B202618011017_承诺书.pdf` 和 `B202618011017/` |
| 论文命名 | PASS | `B202618011017.pdf` |
| 论文格式 | PASS | 22 页、A4、Author 元数据为空，正文不超过 25 页 |
| 论文一致性 | PASS | 源 PDF、根目录副本、培养单位副本、ZIP 内论文及支撑材料内论文 SHA256 全部一致 |
| 论文 SHA256 | PASS | `c6e1ca8aab399f3cfde461e4c75c07ade955d44f993b125313df91b4cbdd04fa` |
| 支撑材料复现验收 | PASS | 在解压后的支撑目录执行 `python -m src.verify_outputs`：86 PASS，0 FAIL |
| 新增关键工件 | PASS | 包含 Q2 `uncertainty.py`/Bootstrap、Q3 $\varepsilon$-Pareto、Q4 regret/restoration、最终结果与验收报告 |
| 匿名检查 | PASS | 论文及匿名文件夹对姓名、学校、指导教师、邮箱、完整队号扫描 0 命中 |
| 环境泄露检查 | PASS | `/home/lanshi`、`/mnt/data` 扫描 0 命中 |
| 缓存和敏感文件 | PASS | 无 `.git`、`__pycache__`、pyc、日志、aux、env、key、pem 等 |
| 陈旧说明 | PASS | 不再打包旧 `figure-captions.md`/`deepen-results.md`，改为最终 `RESULTS_REPORT.md` 与 `VERIFY_REPORT.md` |
| 承诺书字段 | PASS | B 题、完整队号、学校、三名队员和指导教师已预填；一页 A4 |
| 承诺书签名与日期 | **FAIL** | PDF 无数字签名、无签名图像，日期为空 |

## 签字后安全重打包

完成四方签名并填写日期后，把签字 PDF 保存在 `submission/交培养单位/` 之外，再执行：

```bash
SIGNED_COMMITMENT_PDF=/绝对路径/B202618011017_承诺书_已签.pdf bash submission/pack.sh
```

脚本会先把签字件复制到独立临时文件，再重建交付目录，避免签字件被覆盖。签字后仍须复核 ZIP 内承诺书哈希与签字源文件一致，并由培养单位领队渠道在 2026-08-24 12:00 前发送。
