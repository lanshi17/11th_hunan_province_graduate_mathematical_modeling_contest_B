"""深化计算:评委会追问与一等奖加分件。

写入 src/outputs/deepen/,不覆盖 q1–q4 主结果。
"""
from __future__ import annotations

import json
from math import factorial

import numpy as np
import pandas as pd
import pyomo.environ as pyo

from ..common import data_io
from ..common.paths import CHANNELS, PLAN_YEARS, REGIONS, out_dir
from ..common.plotting import savefig as save_fig
from ..common.plotting import setup as plot_setup
from ..q2_carbonflow.main import load_inputs, responsibility, run_tracing
from ..q3_portfolio.main import (EF_PV, Params, build_model, extract,
                                 merit_order, solve)
from ..q4_robust.main import (FIRST_STAGE, UNC_YEARS, Params4, build_q4_model,
                              feasibility_scenario_generation, plan_metrics,
                              _objective_components)

Q1 = out_dir("q1")
Q2 = out_dir("q2")
Q3 = out_dir("q3")
Q4 = out_dir("q4")
OUT = out_dir("deepen")

RES_COL = {
    "C1": "C1工业改造", "C2": "C2建筑改造", "C3": "C3交通电气化",
    "C4": "C4分布式光伏", "C5": "C5输电升级",
}

NODE_POS = {
    "A1": (0.05, 0.82), "A2": (0.38, 0.90),
    "A3": (0.12, 0.50), "A4": (0.42, 0.52), "A5": (0.78, 0.58),
    "A6": (0.10, 0.14), "A7": (0.42, 0.10), "A8": (0.78, 0.18),
}


def _spearman(a, b) -> float:
    ra = pd.Series(a).rank()
    rb = pd.Series(b).rank()
    return float(ra.corr(rb))


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / max(len(a | b), 1)


def _footprint(x: dict, tol: float = 1e-4) -> set:
    return {(p, t) for (p, t), v in x.items() if v > tol}


def _sched_footprint(sched: pd.DataFrame) -> set:
    return {(r["项目"], int(r["开工年"])) for _, r in sched.iterrows()
            if float(r["开工规模"]) > 1e-4}


# ---------------------------------------------------------------- Q2 Shapley
def carbon_transfer_matrix(rm, cm, rho_m) -> np.ndarray:
    """CF[j,i]: 通道 j→i 到达电量 × 送端碳势,年度合计 ktCO2。"""
    idx = {r: k for k, r in enumerate(REGIONS)}
    cf = np.zeros((8, 8))
    months = sorted(rm["月份"].unique())
    for t, m in enumerate(months):
        sub = cm[cm["月份"] == m]
        for _, row in sub.iterrows():
            j, i = idx[row["送端区域"]], idx[row["受端区域"]]
            cf[j, i] += float(row["受端电量"]) * float(rho_m[t, j])
    return cf


def shapley_values(p_plus: np.ndarray, cf: np.ndarray) -> np.ndarray:
    """v(S)=Σ_{i∈S} P+_i + Σ_{j∉S,i∈S} CF_{j→i}; 精确枚举 2^8=256。"""
    n = 8
    fact = [factorial(k) for k in range(n + 1)]
    vcache = np.empty(1 << n)
    for mask in range(1 << n):
        psum = 0.0
        inflow = 0.0
        for i in range(n):
            if not (mask & (1 << i)):
                continue
            psum += p_plus[i]
            for j in range(n):
                if mask & (1 << j):
                    continue
                inflow += cf[j, i]
        vcache[mask] = psum + inflow
    phi = np.zeros(n)
    full = (1 << n) - 1
    for i in range(n):
        bit = 1 << i
        acc = 0.0
        rest = full ^ bit
        sub = rest
        while True:
            s = sub.bit_count()
            w = fact[s] * fact[n - s - 1] / fact[n]
            acc += w * (vcache[sub | bit] - vcache[sub])
            if sub == 0:
                break
            sub = (sub - 1) & rest
        phi[i] = acc
    return phi, float(vcache[full])


def run_shapley() -> dict:
    print("[deepen] Shapley 责任共担…")
    rm, cm, ef_local, ef_ext = load_inputs()
    rho_m, _, _ = run_tracing(rm, cm, ef_local, ef_ext, "sender")
    resp = responsibility(rm, cm, ef_local, ef_ext, rho_m)
    p_plus = resp["扩展生产责任P+"].to_numpy(float)
    c_full = resp["消费责任全口径C+"].to_numpy(float)
    cf = carbon_transfer_matrix(rm, cm, rho_m)
    phi, vN = shapley_values(p_plus, cf)

    cf_df = pd.DataFrame(np.round(cf, 2), index=REGIONS,
                         columns=[f"至{r}" for r in REGIONS])
    cf_df.insert(0, "从", REGIONS)
    cf_df.to_csv(OUT / "q2_carbon_transfer.csv", index=False,
                 encoding="utf-8-sig")

    rounded = pd.read_csv(Q2 / "q2_responsibility.csv")
    out = rounded.copy()
    out["Shapley责任"] = np.round(phi, 2)
    out.to_csv(OUT / "q2_responsibility_shapley.csv", index=False,
               encoding="utf-8-sig")

    rows = []
    for lam in (0.3, 0.5, 0.7):
        col = f"共担责任(λ={lam})"
        rlam = out[col].to_numpy(float)
        rows.append(dict(
            方案=col,
            与Shapley的MAE_kt=round(float(np.mean(np.abs(rlam - phi))), 2),
            Spearman=round(_spearman(rlam, phi), 4),
        ))
    cmp_df = pd.DataFrame(rows)
    cmp_df.to_csv(OUT / "q2_lambda_vs_shapley.csv", index=False,
                  encoding="utf-8-sig")

    summary = dict(
        vN=round(vN, 4),
        Pplus合计=round(float(p_plus.sum()), 4),
        Shapley合计=round(float(phi.sum()), 4),
        守恒相对误差=float(abs(phi.sum() - vN) / max(abs(vN), 1e-12)),
        Spearman_vs_P=round(_spearman(phi, p_plus), 4),
        Spearman_vs_C=round(_spearman(phi, c_full), 4),
        Spearman_vs_lambda05=round(
            _spearman(phi, out["共担责任(λ=0.5)"].to_numpy(float)), 4),
        最接近Shapley的λ方案=str(cmp_df.loc[cmp_df["与Shapley的MAE_kt"].idxmin(),
                                      "方案"]),
        区域Shapley={r: round(float(v), 2) for r, v in zip(REGIONS, phi)},
        通道碳转移合计kt=round(float(cf.sum()), 2),
    )
    plot_carbon_network(cf, out)
    plot_responsibility_four(out)
    print(f"  v(N)={vN:.2f}, Σφ={phi.sum():.2f}, "
          f"最接近 {summary['最接近Shapley的λ方案']}")
    return summary


def plot_carbon_network(cf: np.ndarray, resp: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyArrowPatch

    plot_setup()
    net = data_io.load_network()
    fig, ax = plt.subplots(figsize=(7.6, 6.2))
    ax.set_xlim(-0.08, 1.08)
    ax.set_ylim(-0.08, 1.08)
    ax.set_aspect("equal")
    ax.axis("off")

    for _, row in net.iterrows():
        a, b = NODE_POS[row["区域1"]], NODE_POS[row["区域2"]]
        ax.plot([a[0], b[0]], [a[1], b[1]], color="#d0d0d0", lw=1.2, zorder=1)

    mx = float(cf.max()) if cf.max() > 0 else 1.0
    idx = {r: k for k, r in enumerate(REGIONS)}
    for j in REGIONS:
        for i in REGIONS:
            val = cf[idx[j], idx[i]]
            if val < 8.0:
                continue
            p0, p1 = np.array(NODE_POS[j]), np.array(NODE_POS[i])
            vec = p1 - p0
            nrm = np.linalg.norm(vec)
            if nrm < 1e-9:
                continue
            u = vec / nrm
            start, end = p0 + 0.07 * u, p1 - 0.07 * u
            ax.add_patch(FancyArrowPatch(
                start, end, arrowstyle="-|>", mutation_scale=11,
                lw=0.6 + 3.2 * val / mx, color="#c0392b", alpha=0.75,
                zorder=2))
            mid = 0.5 * (start + end) + 0.04 * np.array([-u[1], u[0]])
            ax.text(mid[0], mid[1], f"{val:.0f}", fontsize=7,
                    color="#7b241c", ha="center", va="center", zorder=4,
                    bbox=dict(boxstyle="round,pad=0.12", fc="white",
                              ec="none", alpha=0.75))

    pplus = resp.set_index("区域")["扩展生产责任P+"]
    cplus = resp.set_index("区域")["消费责任全口径C+"]
    netc = cplus - pplus
    vmax = float(np.abs(netc).max())
    for r in REGIONS:
        x, y = NODE_POS[r]
        t = 0.5 * (netc[r] / vmax + 1.0) if vmax > 0 else 0.5
        color = plt.cm.RdBu_r(t)
        ax.add_patch(Circle((x, y), 0.055, facecolor=color,
                            edgecolor="#333", lw=1.1, zorder=3))
        ax.text(x, y, r, ha="center", va="center", fontsize=9,
                fontweight="bold", zorder=5)
        ax.text(x, y - 0.085, f"净{(netc[r]):+.0f}", ha="center",
                fontsize=7, color="#333")

    save_fig(fig, OUT / "fig_q2_carbon_flow_network.png")
    plt.close(fig)


def plot_responsibility_four(resp: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from ..common.advanced_plots import annotated_heatmap

    plot_setup()
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    idx = resp.set_index("区域").reindex(REGIONS)
    mat = np.column_stack([
        idx["扩展生产责任P+"], idx["消费责任全口径C+"],
        idx["共担责任(λ=0.5)"], idx["Shapley责任"],
    ]).astype(float)
    im = annotated_heatmap(
        ax, mat, [r"$P^+$", r"$C^+$", r"$\lambda=0.5$", "Shapley"],
        REGIONS, cmap="YlOrRd", fmt=".0f")
    fig.colorbar(im, ax=ax, shrink=0.85).set_label(r"ktCO$_2$")
    save_fig(fig, OUT / "fig_q2_responsibility_shapley.png")
    plt.close(fig)


# ---------------------------------------------------------------- Q1 敏感性
def q1_param_sensitivity() -> pd.DataFrame:
    print("[deepen] Q1 损耗先验与 σ 敏感性…")
    from ..q1_reconcile import main as q1m

    ds = q1m.Dataset()
    base_rate = q1m.LOSS_PRIOR_RATE
    base_sig = {k: v for k, v in q1m.SIG.items()}
    rows = []

    def metrics(tag, kind, value, res):
        e05 = float(res.eta_hat[CHANNELS.index("E05")])
        loss_rate = float(res.loss.sum() / max(res.dem.sum(), 1e-9))
        return dict(
            类型=kind, 设定=tag, 参数值=value,
            稳健目标值=round(float(res.obj), 6),
            描述性观测RSS每项=round(
                float(res.standardized_data_rss) / res.n_obs, 8),
            区内损耗率=round(loss_rate, 5),
            E05线损估计=round(e05, 5),
        )

    try:
        for rate in (0.03, 0.05, 0.08):
            q1m.LOSS_PRIOR_RATE = rate
            q1m.SIG = dict(base_sig)
            res = q1m.reconcile(ds, method="huber")
            rows.append(metrics(f"区内损耗先验 {int(rate * 100)}%",
                                "损耗先验", rate, res))
        q1m.LOSS_PRIOR_RATE = base_rate
        for scale in (0.5, 1.0, 2.0):
            q1m.SIG = {k: (rel * scale, floor)
                       for k, (rel, floor) in base_sig.items()}
            res = q1m.reconcile(ds, method="huber")
            rows.append(metrics(f"相对不确定度 ×{scale:g}",
                                "σ缩放", scale, res))
    finally:
        q1m.LOSS_PRIOR_RATE = base_rate
        q1m.SIG = dict(base_sig)

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "q1_param_sensitivity.csv", index=False,
              encoding="utf-8-sig")
    print(df.to_string(index=False))
    return df


# -------------------------------------------- Q3 碳核算(无求解器,用于基准)
def _xop(pa: Params, x: dict, p: str, y: int) -> float:
    return sum(x.get((p, t), 0.0) for t in pa.years
               if t + pa.build[p] <= y)


def _cumstart(pa: Params, x: dict, p: str, y: int) -> float:
    return sum(x.get((p, t), 0.0) for t in pa.years if t <= y)


def unit_abate(pa: Params, p: str, y: int) -> float:
    i = pa.region_of[p]
    rc = pa.rho[i] * pa.kappa[y]
    return (pa.save_u[p] * rc + pa.clean_u[p] * (rc - EF_PV)
            + pa.abate_u[p] - pa.load_u[p] * rc)


def eval_plan(pa: Params, x: dict) -> dict:
    E, bex = {}, 0.0
    for y in pa.years:
        tot = 0.0
        for i in REGIONS:
            save = sum(pa.save_u[p] * _xop(pa, x, p, y)
                       for p in pa.projects if pa.region_of[p] == i)
            for _, (p_ind, p_pv) in pa.synergy.items():
                if pa.region_of[p_ind] != i:
                    continue
                if (_cumstart(pa, x, p_ind, y) >= 0.3 * pa.maxtot[p_ind]
                        and _cumstart(pa, x, p_pv, y) >= 0.3 * pa.maxtot[p_pv]):
                    save += 0.05 * pa.save_u[p_ind] * _xop(pa, x, p_ind, y)
            clean = sum(pa.clean_u[p] * _xop(pa, x, p, y)
                        for p in pa.projects if pa.region_of[p] == i)
            newload = sum(pa.load_u[p] * _xop(pa, x, p, y)
                          for p in pa.projects if pa.region_of[p] == i)
            abate = sum(pa.abate_u[p] * _xop(pa, x, p, y)
                        for p in pa.projects if pa.region_of[p] == i)
            dfinal = pa.D_base[i, y] - save + newload
            rc = pa.rho[i] * pa.kappa[y]
            e = rc * (dfinal - clean) + EF_PV * clean - abate
            tot += e
            bex += max(0.0, e - pa.budget[i, y])
        E[y] = tot
    inv = sum(x.get((p, t), 0.0) * pa.inv[p]
              for p in pa.projects for t in pa.years)
    viol = {y: max(0.0, E[y] - pa.cap_total[y]) for y in pa.years}
    return dict(E=E, inv=inv, bex=bex, viol=viol,
                feasible=all(v <= 1e-3 for v in viol.values()))


def greedy_just_meet(pa: Params) -> dict:
    """按 2030 单位减排成本升序,逐年补到刚好满足省级碳上限。"""
    x = {(p, t): 0.0 for p in pa.projects for t in pa.years}
    remaining = {p: pa.maxtot[p] for p in pa.projects}
    res_left = {(k, t): float(pa.res_lim.loc[t, RES_COL[k]])
                for k in RES_COL for t in pa.years}
    inv_left = {t: float(pa.res_lim.loc[t, "年度投资上限(百万元)"])
                for t in pa.years}
    order = list(merit_order(pa)["项目"])

    def room(p, t):
        k = pa.rtype[p]
        need = pa.rneed[p]
        cap_res = res_left[k, t] / need if need > 1e-12 else remaining[p]
        cap_inv = inv_left[t] / pa.inv[p] if pa.inv[p] > 1e-12 else remaining[p]
        return min(remaining[p], pa.maxstart[p] - x[p, t], cap_res, cap_inv)

    def commit(p, t, add):
        x[p, t] += add
        remaining[p] -= add
        res_left[pa.rtype[p], t] -= pa.rneed[p] * add
        inv_left[t] -= pa.inv[p] * add

    for y in pa.years:
        guard = 0
        while True:
            guard += 1
            cur = eval_plan(pa, x)
            gap = cur["E"][y] - pa.cap_total[y]
            if gap <= 1e-4 or guard > 8000:
                break
            placed = False
            for p in order:
                ab = unit_abate(pa, p, y)
                if ab <= 1e-9:
                    continue
                t_last = y - pa.build[p]
                for t in pa.years:
                    if t > t_last:
                        continue
                    r = room(p, t)
                    if r <= 1e-8:
                        continue
                    add = min(r, gap / ab)
                    if add <= 1e-8:
                        continue
                    commit(p, t, add)
                    placed = True
                    break
                if placed:
                    break
            if not placed:
                break
    x_nz = {k: v for k, v in x.items() if v > 1e-8}
    met = eval_plan(pa, x)
    return dict(x=x_nz, **met)


def milp_snapshot(tag: str, pa: Params, m, cost: float | None) -> dict:
    if cost is None:
        return dict(方案=tag, 可行=False, 目标_百万元=np.nan,
                    投资_百万元=np.nan, Jaccard=np.nan,
                    入选项目数=0, 预算超额合计_kt=np.nan)
    res = extract(pa, m)
    inv = float(res["sched"]["投资_百万元"].sum()) if len(res["sched"]) else 0.0
    bex = float(res["yearly"]["区域预算超额合计_kt"].sum())
    fp = {(p, t) for p in pa.projects for t in pa.years
          if pyo.value(m.x[p, t]) > 1e-4}
    return dict(
        方案=tag, 可行=True, 目标_百万元=round(cost, 1),
        投资_百万元=round(inv, 1),
        入选项目数=int(res["sched"]["项目"].nunique()) if len(res["sched"]) else 0,
        预算超额合计_kt=round(bex, 1),
        缺供合计_GWh=round(float(res["yearly"]["缺供_GWh"].sum()), 3),
        footprint=fp, sched=res["sched"], yearly=res["yearly"],
    )


def q3_baselines_and_sens() -> dict:
    print("[deepen] Q3 无项目 / 贪心 / 折现 / 罚参数 / 惯性权重…")
    pa = Params()
    base_sched = pd.read_csv(Q3 / "q3_schedule.csv")
    base_fp = _sched_footprint(base_sched)
    base_yearly = pd.read_csv(Q3 / "q3_yearly.csv").set_index("年份")

    empty = eval_plan(pa, {})
    greedy = greedy_just_meet(pa)
    traj = pd.DataFrame(
        [dict(年份=y,
              无项目碳_kt=round(empty["E"][y], 1),
              MILP碳_kt=float(base_yearly.loc[y, "消费侧碳排放_kt"]),
              贪心碳_kt=round(greedy["E"][y], 1),
              碳上限_kt=pa.cap_total[y],
              无项目越限_kt=round(empty["viol"][y], 1),
              贪心越限_kt=round(greedy["viol"][y], 1),
              MILP投资_百万元=float(base_yearly.loc[y, "投资_百万元"]))
         for y in pa.years]
    )
    traj.to_csv(OUT / "q3_no_project_vs_milp.csv", index=False,
                encoding="utf-8-sig")

    g_sched = pd.DataFrame([
        dict(项目=p, 开工年=t, 开工规模=round(v, 3),
             投资_百万元=round(v * pa.inv[p], 2))
        for (p, t), v in sorted(greedy["x"].items())
    ])
    g_sched.to_csv(OUT / "q3_greedy_schedule.csv", index=False,
                   encoding="utf-8-sig")
    g_fp = _footprint(greedy["x"])

    with open(Q3 / "q3_summary.json", encoding="utf-8") as f:
        q3s = json.load(f)
    baselines = pd.DataFrame([
        dict(方案="无项目", 投资_百万元=0.0,
             五年总越限_kt=round(sum(empty["viol"].values()), 1),
             区域预算超额合计_kt=round(empty["bex"], 1),
             碳约束可行=empty["feasible"], Jaccard=0.0,
             入选项目数=0),
        dict(方案="贪心(按单位减排成本补到上限)",
             投资_百万元=round(greedy["inv"], 1),
             五年总越限_kt=round(sum(greedy["viol"].values()), 1),
             区域预算超额合计_kt=round(greedy["bex"], 1),
             碳约束可行=greedy["feasible"],
             Jaccard=round(_jaccard(g_fp, base_fp), 3),
             入选项目数=len({p for p, _ in g_fp})),
        dict(方案="MILP(主方案)",
             投资_百万元=q3s["总投资_百万元"],
             五年总越限_kt=0.0,
             区域预算超额合计_kt=round(float(
                 base_yearly["区域预算超额合计_kt"].sum()), 1),
             碳约束可行=True, Jaccard=1.0,
             入选项目数=int(base_sched["项目"].nunique())),
    ])
    baselines.to_csv(OUT / "q3_baselines.csv", index=False, encoding="utf-8-sig")

    # ---- 折现 / 罚参数 / VOLL / 惯性权重 ----
    sens_rows = []

    def add_milp_row(tag, kind, value, pa_, **kw):
        print(f"  求解 {tag}…")
        m = build_model(pa_, **kw)
        cost = solve(m, allow_infeasible=True)
        snap = milp_snapshot(tag, pa_, m, cost)
        jac = (_jaccard(snap["footprint"], base_fp)
               if snap["可行"] and "footprint" in snap else np.nan)
        row = dict(类型=kind, 设定=tag, 参数值=value,
                   可行=snap["可行"],
                   目标_百万元=snap["目标_百万元"],
                   投资_百万元=snap["投资_百万元"],
                   Jaccard=round(jac, 3) if jac == jac else np.nan,
                   入选项目数=snap["入选项目数"],
                   预算超额合计_kt=snap.get("预算超额合计_kt", np.nan),
                   缺供合计_GWh=snap.get("缺供合计_GWh", np.nan))
        sens_rows.append(row)
        return snap

    def add_base_row(tag, kind, value):
        sens_rows.append(dict(
            类型=kind, 设定=tag, 参数值=value, 可行=True,
            目标_百万元=q3s["目标函数_百万元"],
            投资_百万元=q3s["总投资_百万元"], Jaccard=1.0,
            入选项目数=q3s["入选项目数"],
            预算超额合计_kt=round(float(
                base_yearly["区域预算超额合计_kt"].sum()), 1),
            缺供合计_GWh=round(float(base_yearly["缺供_GWh"].sum()), 3),
        ))

    add_base_row("折现率 0%(主方案)", "折现率", 0.0)
    add_milp_row("折现率 8%", "折现率", 0.08, pa, discount=0.08)
    add_milp_row("区域预算罚 0.1", "区域预算罚", 0.1, pa, carbon_penalty=0.1)
    add_base_row("区域预算罚 0.2(主方案)", "区域预算罚", 0.2)
    add_milp_row("区域预算罚 0.4", "区域预算罚", 0.4, pa, carbon_penalty=0.4)
    add_milp_row("缺供罚 VOLL=5", "VOLL", 5.0, pa, voll=5.0)
    add_base_row("缺供罚 VOLL=10(主方案)", "VOLL", 10.0)
    add_milp_row("缺供罚 VOLL=20", "VOLL", 20.0, pa, voll=20.0)
    add_milp_row("惯性权重全期 0.50", "惯性权重w", 0.50,
                 Params(w_inertia={y: 0.50 for y in PLAN_YEARS}))
    add_base_row("惯性权重 0.85→0.65(主方案)", "惯性权重w", 0.65)
    add_milp_row("惯性权重全期 0.85", "惯性权重w", 0.85,
                 Params(w_inertia={y: 0.85 for y in PLAN_YEARS}))

    sens = pd.DataFrame(sens_rows)
    sens.to_csv(OUT / "q3_param_sensitivity.csv", index=False,
                encoding="utf-8-sig")
    print(sens.to_string(index=False))

    plot_q3_no_project(traj)
    return dict(
        无项目五年总越限_kt=round(sum(empty["viol"].values()), 1),
        无项目2030碳_kt=round(empty["E"][2030], 1),
        无项目2030上限_kt=pa.cap_total[2030],
        贪心投资_百万元=round(greedy["inv"], 1),
        贪心可行=greedy["feasible"],
        贪心Jaccard=round(_jaccard(g_fp, base_fp), 3),
        贪心入选项目数=len({p for p, _ in g_fp}),
        MILP投资_百万元=q3s["总投资_百万元"],
        折现8投资=float(sens.loc[sens["设定"] == "折现率 8%", "投资_百万元"].iloc[0]),
        折现8目标=float(sens.loc[sens["设定"] == "折现率 8%", "目标_百万元"].iloc[0]),
        折现8_Jaccard=float(sens.loc[sens["设定"] == "折现率 8%", "Jaccard"].iloc[0]),
        VOLL方案是否变化=bool(
            sens.loc[sens["类型"] == "VOLL", "Jaccard"].fillna(0).min() < 0.999),
        罚参数表=sens[sens["类型"] == "区域预算罚"][
            ["设定", "投资_百万元", "预算超额合计_kt", "Jaccard"]
        ].to_dict("records"),
        惯性权重表=sens[sens["类型"] == "惯性权重w"][
            ["设定", "投资_百万元", "预算超额合计_kt", "Jaccard"]
        ].to_dict("records"),
    )


def plot_q3_no_project(traj: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from ..common.advanced_plots import annotated_heatmap

    plot_setup()
    cap = traj["碳上限_kt"].to_numpy(float)
    mat = np.vstack([
        traj["无项目碳_kt"].to_numpy(float) - cap,
        traj["贪心碳_kt"].to_numpy(float) - cap,
        traj["MILP碳_kt"].to_numpy(float) - cap,
    ])
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    lim = float(np.nanmax(np.abs(mat))) or 1.0
    im = annotated_heatmap(ax, mat, [str(y) for y in traj["年份"]],
                           ["无项目", "贪心", "MILP"], cmap="RdBu_r",
                           fmt=".0f", vmin=-lim, vmax=lim)
    fig.colorbar(im, ax=ax, shrink=0.85).set_label(r"相对上限差额 ktCO$_2$")
    save_fig(fig, OUT / "fig_q3_no_project.png")
    plt.close(fig)


# ------------------------------------------------ Q4 三方案 + S_ij 局限
def sij_limitation(p4: Params4) -> dict:
    print("[deepen] S_ij 冻结假设的定量局限…")
    reg = pd.read_csv(Q3 / "q3_regional.csv")
    r2030 = reg[reg["年份"] == 2030].set_index("区域")
    xi = {j: p4.xi_of("S3", j, 2030) for j in REGIONS}
    W_trace = {j: p4.W_base(j, 2030) for j in REGIONS}
    W_access = {j: float(r2030.loc[j, "省外输入_GWh"]) for j in REGIONS}
    # 混合:2025 份额 80% + 向 A4 枢纽集中 20%(示意 2030 格局漂移)
    W_shift = {}
    for j in REGIONS:
        w = 0.8 * W_trace[j]
        if j == "A4":
            w += 0.2 * sum(W_trace.values())
        W_shift[j] = w
    d_trace = p4.delta_E(2030, W_trace, xi)
    d_access = p4.delta_E(2030, W_access, xi)
    d_shift = p4.delta_E(2030, W_shift, xi)
    rows = [
        dict(传导口径="2025碳流份额S_ij×(净需求−光伏)(主方案)",
             S3_2030增量_kt=round(d_trace, 1)),
        dict(传导口径="接入区省外输入电量(忽略转供)",
             S3_2030增量_kt=round(d_access, 1)),
        dict(传导口径="S向A4集中20%的示意漂移",
             S3_2030增量_kt=round(d_shift, 1)),
    ]
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "q4_sij_limitation.csv", index=False, encoding="utf-8-sig")
    return dict(
        S3_2030_主方案增量_kt=round(d_trace, 1),
        S3_2030_接入区口径增量_kt=round(d_access, 1),
        S3_2030_A4集中示意增量_kt=round(d_shift, 1),
        接入区口径相对主方案偏差=round(
            (d_access - d_trace) / max(abs(d_trace), 1e-9), 4),
    )


def _s3_violations(p4: Params4, m) -> dict:
    out = {}
    for y in UNC_YEARS:
        W = {j: pyo.value(m._W(m, j, y)) for j in REGIONS}
        xi = {j: p4.xi_of("S3", j, y) for j in REGIONS}
        E = sum(pyo.value(m._emis(i, y)) for i in REGIONS) + p4.delta_E(y, W, xi)
        out[y] = max(0.0, E - p4.pa.cap_total[y])
    return out


def rolling_with_investment(p4: Params4, x1: dict,
                            scen: str = "S3") -> tuple[pd.DataFrame, float]:
    """复制 Q4 滚动逻辑,但不写回 q4_rolling.csv;返回投资合计。"""
    committed = {(p, t): v for (p, t), v in x1.items()}
    for p in p4.pa.projects:
        for t in FIRST_STAGE:
            committed.setdefault((p, t), 0.0)
    rows = []
    for y_now in UNC_YEARS:
        xi_known = {(j, y): p4.xi_of(scen, j, y)
                    for j in REGIONS for y in UNC_YEARS if y <= y_now}
        m = build_q4_model(p4, xi=xi_known, robust_gamma_scale=1.0,
                           robust_from=y_now + 1, fixed_x=committed)
        cost = solve(m)
        togo = _objective_components(
            p4, m, (y for y in PLAN_YEARS if y >= y_now))
        for p in p4.pa.projects:
            committed[(p, y_now)] = pyo.value(m.x[p, y_now])
        E, viol = {}, {}
        for y in UNC_YEARS:
            W = {j: pyo.value(m._W(m, j, y)) for j in REGIONS}
            xi_real = {j: p4.xi_of(scen, j, y) for j in REGIONS}
            E[y] = (sum(pyo.value(m._emis(i, y)) for i in REGIONS)
                    + p4.delta_E(y, W, xi_real))
            viol[y] = max(0.0, E[y] - p4.pa.cap_total[y])
        inv_so_far = sum(committed.get((p, t), 0.0) * p4.pa.inv[p]
                         for p in p4.pa.projects for t in PLAN_YEARS
                         if t <= y_now)
        rows.append(dict(情景=scen, 决策年=y_now,
                         全周期条件目标_百万元=round(cost, 1),
                         剩余期目标_百万元=round(
                             togo["目标合计_百万元"], 1),
                         剩余期投资_百万元=round(togo["投资_百万元"], 1),
                         累计投资_百万元=round(inv_so_far, 1),
                         **{f"越限{y}_kt": round(viol[y], 2) for y in UNC_YEARS}))
    inv_total = sum(committed.get((p, t), 0.0) * p4.pa.inv[p]
                    for p in p4.pa.projects for t in PLAN_YEARS)
    return pd.DataFrame(rows), float(inv_total), committed


def q4_three_schemes() -> dict:
    print("[deepen] Q4 确定性 / Γ=1软防御 / S3滚动 对照…")
    p4 = Params4()
    stress = pd.read_csv(Q4 / "q4_stress.csv")
    por = pd.read_csv(Q4 / "q4_por_curve.csv")
    with open(Q4 / "q4_summary.json", encoding="utf-8") as f:
        q4_summary = json.load(f)
    s3 = stress[stress["情景"] == "S3"].set_index("年份")
    nom = por[por["Gamma缩放"] == 0.0].iloc[0]
    rob = por[por["Gamma缩放"] == 1.0].iloc[0]

    print("  重解 Γ=1 软约束方案以核算 S3 越限…")
    m_rob = build_q4_model(p4, robust_gamma_scale=1.0)
    solve(m_rob)
    rob_s3 = _s3_violations(p4, m_rob)
    rob_met = plan_metrics(p4, m_rob)

    print("  重跑可行性场景生成启发式 + 滚动以提取投资…")
    _, log, x1, _ = feasibility_scenario_generation(p4)
    roll_s3, roll_inv, committed = rolling_with_investment(p4, x1, "S3")
    roll_s1, roll_inv_s1, _ = rolling_with_investment(p4, x1, "S1")
    roll_s0, roll_inv_s0, _ = rolling_with_investment(p4, x1, "S0")
    roll_all = pd.concat([roll_s3, roll_s1, roll_s0], ignore_index=True)
    roll_all.to_csv(OUT / "q4_rolling_with_investment.csv", index=False,
                    encoding="utf-8-sig")
    sched = pd.DataFrame([
        dict(项目=p, 开工年=t, 规模=round(v, 3))
        for (p, t), v in committed.items() if v > 1e-6
    ])
    sched.to_csv(OUT / "q4_rolling_schedule.csv", index=False,
                 encoding="utf-8-sig")
    roll_s3_v = {y: float(roll_s3.iloc[-1][f"越限{y}_kt"]) for y in UNC_YEARS}

    gamma_slim = por.rename(columns={"Gamma缩放": "tau"})[
        ["tau", "投资_百万元", "设计集tauGamma违约_kt",
         "统一Gamma回测违约_kt"]]
    gamma_slim.to_csv(OUT / "q4_gamma_sensitivity.csv", index=False,
                      encoding="utf-8-sig")

    table = pd.DataFrame([
        dict(方案="确定性(问题三主方案)",
             总投资_百万元=float(nom["投资_百万元"]),
             S3_2028越限_kt=float(s3.loc[2028, "越限_kt"]),
             S3_2029越限_kt=float(s3.loc[2029, "越限_kt"]),
             S3_2030越限_kt=float(s3.loc[2030, "越限_kt"]),
             预算集最坏总越限_kt=float(nom["最坏情景总越限_kt"]),
             推荐="压力底线,不宜单独采用"),
        dict(方案="Γ=1软约束防御",
             总投资_百万元=round(float(rob_met["投资"]), 1),
             S3_2028越限_kt=round(rob_s3[2028], 1),
             S3_2029越限_kt=round(rob_s3[2029], 1),
             S3_2030越限_kt=round(rob_s3[2030], 1),
             预算集最坏总越限_kt=round(float(rob_met["总最坏越限"]), 2),
             推荐=(
                 f"仍有{q4_summary['Gamma1最小总硬缺口_kt']:.2f} kt"
                 "结构性缺口,不可称完整硬鲁棒")),
        dict(方案="S3滚动(已观测年用真值,未来年Γ-软防御)",
             总投资_百万元=round(roll_inv, 1),
             S3_2028越限_kt=roll_s3_v[2028],
             S3_2029越限_kt=roll_s3_v[2029],
             S3_2030越限_kt=roll_s3_v[2030],
             预算集最坏总越限_kt=np.nan,
             推荐="给定S3路径下零越限;不是对完整Γ集合的硬保证"),
    ])
    table.to_csv(OUT / "q4_three_schemes.csv", index=False, encoding="utf-8-sig")
    plot_three_schemes(table)
    sij = sij_limitation(p4)
    return dict(
        三方案=table.to_dict("records"),
        滚动投资_百万元=round(roll_inv, 1),
        滚动S1投资_百万元=round(roll_inv_s1, 1),
        滚动S0投资_百万元=round(roll_inv_s0, 1),
        滚动剩余期目标=roll_s3[["决策年", "剩余期目标_百万元",
                                "累计投资_百万元"]].to_dict("records"),
        Gamma1软方案投资核对=round(float(rob["投资_百万元"]), 1),
        可行性场景生成日志=log.to_dict("records"),
        Sij局限=sij,
    )


def plot_three_schemes(table: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    plot_setup()
    names = ["确定性", r"$\Gamma=1$软防御", "S3滚动"]
    inv = table["总投资_百万元"].to_numpy(float)
    v2030 = table["S3_2030越限_kt"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    colors = ["#D55E00", "#0072B2", "#009E73"]
    markers = ["s", "o", "D"]
    ax.annotate("", xy=(inv[1], v2030[1]), xytext=(inv[0], v2030[0]),
                arrowprops=dict(arrowstyle="->", color="#666", lw=1.1))
    for i, name in enumerate(names):
        ax.scatter(inv[i], v2030[i], s=70, color=colors[i], marker=markers[i],
                   zorder=3, label=name, edgecolors="white", linewidths=0.4)
        dx, dy = (8, 8) if i != 2 else (8, -14)
        ax.annotate(f"{name} ({inv[i]:.1f}, {v2030[i]:.1f})",
                    (inv[i], v2030[i]), textcoords="offset points",
                    xytext=(dx, dy), fontsize=8)
    ax.set_xlabel("总投资(百万元)")
    ax.set_ylabel(r"S3 情景 2030 越限(ktCO$_2$)")
    ax.legend(fontsize=8, loc="upper right")
    save_fig(fig, OUT / "fig_q4_three_schemes.png")
    plt.close(fig)


def main() -> None:
    summary = {}
    summary["shapley"] = run_shapley()
    summary["q1_sens"] = q1_param_sensitivity().to_dict("records")
    summary["q3"] = q3_baselines_and_sens()
    summary["q4"] = q4_three_schemes()
    with open(OUT / "deepen_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    print("[deepen] 完成:", OUT)


if __name__ == "__main__":
    main()
