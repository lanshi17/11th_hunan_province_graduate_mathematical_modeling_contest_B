支撑材料说明（匿名）

本目录提供论文全部可运行源程序与计算产物，不含题目原始 Excel。

运行（在解压后的项目根目录）：

    python3.12 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    .venv/bin/python -m src.q1_reconcile.main
    .venv/bin/python -m src.q2_carbonflow.main --bootstrap-samples 500
    .venv/bin/python -m src.q3_portfolio.main
    .venv/bin/python -m src.q4_robust.main
    .venv/bin/python -m src.q5_report.main
    .venv/bin/python -m src.deepen.main          # 加分件，不覆盖 q1–q4
    .venv/bin/python -m src.verify_outputs

数据：data/raw/problem-B/*.csv 由官方附件转换（UTF-8）。
结果：src/outputs/q1…q5 与 src/outputs/deepen/。
论文源：paper/main.tex（XeLaTeX）。
绘图：SciencePlots + XeLaTeX（需 TeX Live，含 ctex）。

求解器：Clarabel（Q1 凸 Huber 调和）、HiGHS（Q3/Q4 MILP）。
