"""只刷新论文用图，不重解 Q3/Q4/deepen 的优化器。

用法：.venv/bin/python -m src.refresh_figures
"""
from __future__ import annotations

import pandas as pd

from .common.paths import OUT_DIR
from .deepen.main import (plot_carbon_network, plot_q3_no_project,
                          plot_responsibility_four, plot_three_schemes)
from .q3_portfolio.main import make_plots as q3_plots
from .q4_robust.main import make_plots as q4_plots


def main() -> None:
    from .q2_carbonflow.main import main as q2_main

    print("[refresh] Q1 作图（残差现场算，其余读 CSV）…")
    from .q1_reconcile.main import Dataset, make_plots as q1_plots
    q1_plots(Dataset(), None,
             pd.read_csv(OUT_DIR / "q1/q1_adjustments.csv"),
             pd.read_csv(OUT_DIR / "q1/q1_influence.csv"))
    print("[refresh] Q2 碳流 + 作图…")
    q2_main(n_bootstrap=0, propagate_q3=False)

    print("[refresh] Q3 作图（读已有 CSV）…")
    q3_plots(
        {"yearly": pd.read_csv(OUT_DIR / "q3/q3_yearly.csv"),
         "sched": pd.read_csv(OUT_DIR / "q3/q3_schedule.csv"),
         "regional": pd.read_csv(OUT_DIR / "q3/q3_regional.csv")},
        pd.read_csv(OUT_DIR / "q3/q3_merit_order.csv"),
    )

    print("[refresh] Q4 作图（读已有 CSV）…")
    q4_plots(pd.read_csv(OUT_DIR / "q4/q4_stress.csv"),
             pd.read_csv(OUT_DIR / "q4/q4_por_curve.csv"))
    from .q4_robust.main import make_regret_plot
    make_regret_plot(pd.read_csv(OUT_DIR / "q4/q4_regret_paths.csv"))

    print("[refresh] Q2 区间图（读已有 CSV）…")
    from .q2_carbonflow.uncertainty import (_plot_channel_uncertainty,
                                            _plot_uncertainty)
    _plot_uncertainty(pd.read_csv(OUT_DIR / "q2/q2_rho_annual_interval.csv"),
                      pd.read_csv(OUT_DIR / "q2/q2_bootstrap_convergence.csv"))
    _plot_channel_uncertainty(
        pd.read_csv(OUT_DIR / "q2/q2_channel_carbon_interval.csv"))

    print("[refresh] deepen 作图（读已有 CSV）…")
    cf_df = pd.read_csv(OUT_DIR / "deepen/q2_carbon_transfer.csv")
    cf = cf_df[[c for c in cf_df.columns if c.startswith("至")]].to_numpy(float)
    resp = pd.read_csv(OUT_DIR / "deepen/q2_responsibility_shapley.csv")
    plot_carbon_network(cf, resp)
    plot_responsibility_four(resp)
    plot_q3_no_project(pd.read_csv(OUT_DIR / "deepen/q3_no_project_vs_milp.csv"))
    plot_three_schemes(pd.read_csv(OUT_DIR / "deepen/q4_three_schemes.csv"))
    print("[refresh] 完成")


if __name__ == "__main__":
    main()
