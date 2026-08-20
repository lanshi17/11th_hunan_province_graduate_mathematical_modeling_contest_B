#!/usr/bin/env bash
# 打包交培养单位的三件套：承诺书（空白打印稿）+ 论文 PDF + 上交作品 zip
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$ROOT/submission/B_TEAMID"
DELIVER="$ROOT/submission/交培养单位"
COMMIT_DOCX="$ROOT/competition_question/（必读）第十一届湖南省研究生数学建模竞赛承诺书.docx"

rm -rf "$STAGE" "$DELIVER"
mkdir -p "$STAGE/support/data/raw/problem-B" "$STAGE/support/paper" "$DELIVER"

cp -a "$ROOT/paper/main.pdf" "$STAGE/B_TEAMID.pdf"

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
cp -a "$ROOT/docs/problem-B/figure-captions.md" \
  "$ROOT/docs/problem-B/deepen-results.md" \
  "$STAGE/support/docs/"

# 上交作品 zip：根目录即为「选题+队号.pdf」+ support/
( cd "$STAGE" && zip -r -q "$DELIVER/B_TEAMID.zip" B_TEAMID.pdf support )

cp -a "$STAGE/B_TEAMID.pdf" "$DELIVER/B_TEAMID.pdf"
cp -a "$COMMIT_DOCX" "$DELIVER/（必读）第十一届湖南省研究生数学建模竞赛承诺书.docx"

python3 - <<PY
import sys
sys.path.insert(0, "/home/lanshi/.claude/skills/docx/scripts")
from office.soffice import run_soffice
from pathlib import Path
deliver = Path("$DELIVER")
src = deliver / "（必读）第十一届湖南省研究生数学建模竞赛承诺书.docx"
r = run_soffice(
    ["--headless", "--convert-to", "pdf", "--outdir", str(deliver), str(src)],
    capture_output=True, text=True,
)
print(r.stdout)
print(r.stderr)
if r.returncode != 0:
    raise SystemExit(r.returncode)
pdf = src.with_suffix(".pdf")
pdf.rename(deliver / "承诺书_空白打印稿.pdf")
print("commitment pdf", deliver / "承诺书_空白打印稿.pdf")
PY

cp -a "$ROOT/submission/提交说明.txt" "$DELIVER/提交说明.txt"
cp -a "$ROOT/submission/改名.sh" "$DELIVER/改名.sh"
chmod +x "$DELIVER/改名.sh"

( cd "$ROOT/submission" && rm -f 交培养单位_B题_待填队号.zip && zip -r -q 交培养单位_B题_待填队号.zip 交培养单位 )

cp -a "$DELIVER/B_TEAMID.zip" "$ROOT/submission/B_TEAMID.zip"

echo "==== 交培养单位 ===="
ls -lh "$DELIVER"
echo "==== 体积 ===="
ls -lh "$ROOT/submission/交培养单位_B题_待填队号.zip" "$DELIVER/B_TEAMID.zip"
unzip -l "$DELIVER/B_TEAMID.zip" | head -20
echo "..."
unzip -l "$DELIVER/B_TEAMID.zip" | tail -3
pdfinfo "$DELIVER/B_TEAMID.pdf" | grep -E 'Pages|Title|Author'
python3 - <<PY
from pathlib import Path
z = Path(r"$DELIVER") / "B_TEAMID.zip"
mb = z.stat().st_size / 1024 / 1024
print(f"上交作品 zip = {mb:.2f} MB  (限 20 MB)")
if mb > 20:
    raise SystemExit("zip exceeds 20MB")
PY
