#!/usr/bin/env bash
# 按湖南农业大学领队三点要求打包：承诺书 + 论文文件夹 + 邮件 zip
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEAM_ID="202618011017"
NAME="B${TEAM_ID}"
STAGE="$ROOT/submission/B_TEAMID"
DELIVER="$ROOT/submission/交培养单位"
FOLDER="$DELIVER/${NAME}"
SUPPORT="${NAME}_支撑材料"
COMMIT_DOCX="$ROOT/competition_question/（必读）第十一届湖南省研究生数学建模竞赛承诺书.docx"
SIGNED_SOURCE="${SIGNED_COMMITMENT_PDF:-}"
SIGNED_TMP=""

# 可选：签字后用 SIGNED_COMMITMENT_PDF=/path/to/signed.pdf 重新打包。
# 必须先复制到独立临时文件，因为下面会重建整个交付目录。
if [[ -n "$SIGNED_SOURCE" ]]; then
  if [[ ! -f "$SIGNED_SOURCE" ]]; then
    echo "signed commitment not found: $SIGNED_SOURCE" >&2
    exit 2
  fi
  SIGNED_TMP="$(mktemp "${TMPDIR:-/tmp}/mathmodel-signed-commitment.XXXXXX.pdf")"
  cp -a "$SIGNED_SOURCE" "$SIGNED_TMP"
fi
cleanup() {
  if [[ -n "$SIGNED_TMP" && -f "$SIGNED_TMP" ]]; then
    rm -f "$SIGNED_TMP"
  fi
}
trap cleanup EXIT

[[ -s "$ROOT/paper/main.pdf" ]]
[[ -f "$ROOT/reports/RESULTS_REPORT.md" ]]
[[ -f "$ROOT/reports/VERIFY_REPORT.md" ]]
PAGES="$(pdfinfo "$ROOT/paper/main.pdf" | awk '/^Pages:/ {print $2}')"
if [[ -z "$PAGES" || "$PAGES" -gt 25 ]]; then
  echo "paper page count invalid: ${PAGES:-unknown}" >&2
  exit 2
fi

# 先验收再改交付目录，避免把旧包删掉后才发现上游结果失效。
(cd "$ROOT" && uv run python -m src.verify_outputs >/dev/null)

rm -rf "$STAGE" "$DELIVER"
mkdir -p "$STAGE/support/data/raw/problem-B" "$STAGE/support/paper" \
  "$FOLDER/${SUPPORT}" "$DELIVER"

cp -a "$ROOT/paper/main.pdf" "$STAGE/${NAME}.pdf"

rsync -a --delete \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  "$ROOT/src/" "$STAGE/support/src/"

rsync -a --delete \
  "$ROOT/data/raw/problem-B/" "$STAGE/support/data/raw/problem-B/"

cp -a "$ROOT/paper/main.tex" "$ROOT/paper/compile.sh" "$ROOT/paper/README.md" \
  "$ROOT/paper/main.pdf" "$STAGE/support/paper/"
cp -a "$ROOT/requirements.txt" "$STAGE/support/requirements.txt"
cp -a "$ROOT/paper/SUPPORT_README.txt" "$STAGE/support/README.txt"
mkdir -p "$STAGE/support/docs"
cp -a "$ROOT/reports/RESULTS_REPORT.md" \
  "$ROOT/reports/VERIFY_REPORT.md" \
  "$STAGE/support/docs/"

rsync -a --delete "$STAGE/support/" "$FOLDER/${SUPPORT}/"
cp -a "$STAGE/${NAME}.pdf" "$FOLDER/${NAME}.pdf"
cp -a "$STAGE/${NAME}.pdf" "$DELIVER/${NAME}.pdf"
cp -a "$COMMIT_DOCX" "$DELIVER/（必读）第十一届湖南省研究生数学建模竞赛承诺书.docx"

python3 - <<PY
import re
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, "/home/lanshi/.claude/skills/docx/scripts")
from office.soffice import run_soffice

deliver = Path("$DELIVER")
blank = deliver / "（必读）第十一届湖南省研究生数学建模竞赛承诺书.docx"
filled = deliver / "承诺书_已填打印稿.docx"
replacements = {
    "我们参赛选择的题号是（从组委会提供的赛题中选择一项填写）：":
        "我们参赛选择的题号是（从组委会提供的赛题中选择一项填写）：B",
    "我们的参赛编号（请填写完整参赛编号）：":
        "我们的参赛编号（请填写完整参赛编号）：$TEAM_ID",
    "所属学校（请填写完整的全名）：":
        "所属学校（请填写完整的全名）：湖南农业大学",
    "1.  ": "1.  杨正帅",
    ">2. <": ">2. 郝锦涛<",
    ">3. <": ">3. 马澳<",
}
advisor_old = (
    '指导教师或指导教师组负责人</w:t></w:r>'
    '<w:r><w:rPr><w:rFonts w:hAnsi="宋体" w:cs="Tahoma"/><w:sz w:val="21"/></w:rPr>'
    '<w:t xml:space="preserve"> </w:t></w:r>'
    '<w:proofErr w:type="gramStart"/>'
    '<w:r><w:rPr><w:rFonts w:hAnsi="宋体" w:cs="Tahoma"/><w:sz w:val="21"/></w:rPr>'
    '<w:t>(</w:t></w:r>'
    '<w:r><w:rPr><w:rFonts w:hAnsi="宋体" w:cs="Tahoma" w:hint="eastAsia"/>'
    '<w:sz w:val="21"/></w:rPr><w:t>打印后签名</w:t></w:r>'
    '<w:r><w:rPr><w:rFonts w:hAnsi="宋体" w:cs="Tahoma"/><w:sz w:val="21"/></w:rPr>'
    '<w:t>)</w:t></w:r><w:proofErr w:type="gramEnd"/>'
    '<w:r><w:rPr><w:rFonts w:hAnsi="宋体" w:cs="Tahoma" w:hint="eastAsia"/>'
    '<w:sz w:val="21"/></w:rPr><w:t>：</w:t></w:r></w:p>'
)
advisor_new = advisor_old.replace("：</w:t></w:r></w:p>", "：李长云</w:t></w:r></w:p>")

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    unzip = td / "unzip"
    unzip.mkdir()
    with zipfile.ZipFile(blank) as z:
        z.extractall(unzip)
    doc_xml = unzip / "word" / "document.xml"
    text = doc_xml.read_text(encoding="utf-8")
    for old, new in replacements.items():
        if old not in text:
            raise SystemExit(f"missing pattern: {old!r}")
        text = text.replace(old, new, 1)
    if advisor_old not in text:
        raise SystemExit("missing advisor pattern")
    text = text.replace(advisor_old, advisor_new, 1)
    doc_xml.write_text(text, encoding="utf-8")
    with zipfile.ZipFile(filled, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(unzip.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(unzip).as_posix())

commit_pdf = deliver / "${NAME}_承诺书.pdf"
for src, dest in (
    (blank, deliver / "承诺书_空白打印稿.pdf"),
    (filled, commit_pdf),
):
    r = run_soffice(
        ["--headless", "--convert-to", "pdf", "--outdir", str(deliver), str(src)],
        capture_output=True, text=True,
    )
    print(r.stdout)
    print(r.stderr)
    if r.returncode != 0:
        raise SystemExit(r.returncode)
    produced = src.with_suffix(".pdf")
    if produced.resolve() != dest.resolve():
        produced.replace(dest)
    print("commitment pdf", dest)

# 匿名检查：论文与支撑材料不得出现身份
banned = ("杨正帅", "郝锦涛", "马澳", "李长云", "湖南农业大学", "190325652")
root = Path("$FOLDER")
hits = []
for p in root.rglob("*"):
    if not p.is_file():
        continue
    if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".zip"}:
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for word in banned:
        if word in text:
            hits.append(f"{p.relative_to(root)}: {word}")
if hits:
    raise SystemExit("identity leaked into paper/support:\n" + "\n".join(hits))

pdf_text = Path("$FOLDER/${NAME}.pdf").read_bytes()
# 粗查二进制中的 UTF-8 姓名
for word in banned:
    if word.encode("utf-8") in pdf_text:
        raise SystemExit(f"identity leaked into paper PDF: {word}")
print("anonymity ok")
PY

if [[ -n "$SIGNED_TMP" ]]; then
  cp -a "$SIGNED_TMP" "$DELIVER/${NAME}_承诺书.pdf"
  echo "commitment source: signed PDF supplied by SIGNED_COMMITMENT_PDF"
else
  echo "WARNING: commitment is a prefilled unsigned draft; sign and date it before sending"
fi

cp -a "$ROOT/submission/提交说明.txt" "$DELIVER/提交说明.txt"

# 发给领队：承诺书在匿名文件夹外，zip 文件名为题号+队号
rm -f "$DELIVER/${NAME}.zip" "$ROOT/submission/${NAME}.zip" \
  "$ROOT/submission/B_TEAMID.zip" "$ROOT/submission/B_TEAMID.pdf" \
  "$ROOT/submission/交培养单位_B题_${TEAM_ID}.zip" \
  "$ROOT/submission/交培养单位_B题_待填队号.zip"
(
  cd "$DELIVER"
  zip -r -q "${NAME}.zip" "${NAME}_承诺书.pdf" "${NAME}"
)
cp -a "$DELIVER/${NAME}.zip" "$ROOT/submission/${NAME}.zip"
cp -a "$DELIVER/${NAME}_承诺书.pdf" "$ROOT/submission/${NAME}_承诺书.pdf"
cp -a "$FOLDER/${NAME}.pdf" "$ROOT/submission/${NAME}.pdf"

echo "==== 发给领队 ===="
ls -lh "$DELIVER/${NAME}.zip" "$DELIVER/${NAME}_承诺书.pdf" "$FOLDER"
echo "==== zip 顶层 ===="
unzip -l "$DELIVER/${NAME}.zip" | head -25
echo "==== 体积 ===="
python3 - <<PY
from pathlib import Path
z = Path(r"$DELIVER/${NAME}.zip")
mb = z.stat().st_size / 1024 / 1024
print(f"{z.name} = {mb:.2f} MB  (组委会一般限 20 MB)")
if mb > 20:
    raise SystemExit("zip exceeds 20MB")
print("邮件：190325652@qq.com")
print("主题：湖南研究生数学建模竞赛材料")
print("附件：${NAME}.zip")
PY
