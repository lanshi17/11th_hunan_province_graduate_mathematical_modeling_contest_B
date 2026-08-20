"""问题四:送端碳排不确定性与鲁棒滚动调控。

三层递进:
1. 压力测试:固定问题三方案,在 S0–S3 与预算集最坏情景下核算逐年碳排放
   (纯算术,附件6A/6B)。
2. 静态鲁棒对等式:预算不确定集 Γ_t(Bertsimas & Sim 2004)内层 max 对偶化,
   嵌回 MILP 整体重解;Γ 缩放扫描得 price-of-robustness 曲线。
3. 两阶段可调鲁棒(Ben-Tal et al. 2004):2026–2027 开工为"此时此地"决策,
   2028–2030 追加项目为"观望"决策;情景扩展形式 + C&CG 型顶点加列
   (Zeng & Zhao 2013);再按滚动时域在 S3 下逐年模拟
   (Silvente et al. 2015)。

不确定性传导口径(与问题二追踪管线一致):送端因子扰动 ξ_{j,y} 通过 2025
年碳流追踪的"省外输入分接入区消费份额矩阵" S_{ij} 传导至各区消费碳:

    ΔE_y(ξ) = κ_y · Σ_j ē_j·(ξ_{j,y} − 1) · W_{j,y},
    W_{j,y} = Σ_i (净需求_{i,y} − 光伏供电_{i,y}) · S_{ij}。

W 只依赖需求侧决策(节电/电气化/光伏),扰动无法靠改写购电台账回避,
补偿机制体现为需求侧项目加码与光伏替代——与官方 ρ·κ 简化口径自洽。
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pyomo.environ as pyo

from ..common import data_io
from ..common.paths import PLAN_YEARS, REGIONS, out_dir
from ..common.plotting import setup as plot_setup
from ..q3_portfolio.main import (CARBON_PENALTY, EPS_FLOW, VOLL, Params,
                                 build_model, solve)

Q2 = out_dir("q2")
Q3 = out_dir("q3")
OUT = out_dir("q4")

UNC_YEARS = [2028, 2029, 2030]
CAP_VIOL_PENALTY = 50.0     # 省级碳上限违约罚 百万元/kt(远高于减排成本)
FIRST_STAGE = (2026, 2027)


class Params4:
    def __init__(self) -> None:
        self.pa = Params()
        unc, self.gamma = data_io.load_uncertainty()
        self.xiU = {(r["区域"], int(r["年份"])): float(r["偏离系数上界"])
                    for _, r in unc.iterrows()}
        self.xiL = {(r["区域"], int(r["年份"])): float(r["偏离系数下界"])
                    for _, r in unc.iterrows()}
        sc = data_io.load_scenarios()
        self.scen = {}
        for s in ("S0", "S1", "S2", "S3"):
            sub = sc[sc["情景编号"] == s]
            self.scen[s] = {(i, int(r["年份"])): float(r[i])
                            for _, r in sub.iterrows() for i in REGIONS}

        share = pd.read_csv(Q2 / "q2_import_share.csv").set_index("区域")
        self.S = {(i, j): float(share.loc[i, f"来自{j}省外输入"])
                  for i in REGIONS for j in REGIONS}
        reg = pd.read_csv(Q3 / "q3_regional.csv")
        self.E_base_iy = {(r["区域"], int(r["年份"])): float(r["消费碳_kt"])
                          for _, r in reg.iterrows()}
        self.grid_base = {(r["区域"], int(r["年份"])):
                          float(r["净需求_GWh"]) - float(r["光伏供电_GWh"])
                          for _, r in reg.iterrows()}
        self.ebar = self.pa.imp_ef

    def W_base(self, j: str, y: int) -> float:
        """问题三方案下源自 j 区省外输入的消费电量。"""
        return sum(self.grid_base[i, y] * self.S[i, j] for i in REGIONS)

    def ucoef(self, j: str, y: int) -> float:
        """不利偏差单位系数 κ_y·ē_j·(ξU−1)(kt / GWh·W)。"""
        return self.pa.kappa[y] * self.ebar[j] * (self.xiU[j, y] - 1)

    def xi_of(self, name: str, j: str, y: int) -> float:
        if y not in UNC_YEARS:
            return 1.0
        return self.scen[name][(j, y)] if name in self.scen else 1.0

    def worst_budget_xi(self, y: int, W: dict, gamma_scale: float = 1.0):
        """给定 W_j,预算集内最坏 ξ(贪心取系数最大的 Γ 个,含分数)。"""
        if y not in UNC_YEARS:
            return {j: 1.0 for j in REGIONS}
        coefs = {j: self.ucoef(j, y) * W[j] for j in REGIONS}
        order = sorted(REGIONS, key=lambda j: -coefs[j])
        budget = self.gamma[y] * gamma_scale
        xi = {}
        for j in order:
            z = min(1.0, max(0.0, budget))
            budget -= z
            xi[j] = 1 + z * (self.xiU[j, y] - 1)
        return xi

    def delta_E(self, y: int, W: dict, xi: dict) -> float:
        return sum(self.pa.kappa[y] * self.ebar[j] * (xi[j] - 1) * W[j]
                   for j in REGIONS)


# ---------------------------------------------------------------- 压力测试
def stress_test(p4: Params4) -> pd.DataFrame:
    """固定问题三方案,各情景逐年碳排放 vs 上限。"""
    rows = []
    E_base_y = {y: sum(p4.E_base_iy[i, y] for i in REGIONS)
                for y in PLAN_YEARS}
    for name in ("S0", "S1", "S2", "S3", "预算集最坏"):
        for y in UNC_YEARS:
            W = {j: p4.W_base(j, y) for j in REGIONS}
            if name == "预算集最坏":
                xi = p4.worst_budget_xi(y, W)
            else:
                xi = {j: p4.xi_of(name, j, y) for j in REGIONS}
            dE = p4.delta_E(y, W, xi)
            E = E_base_y[y] + dE
            cap = p4.pa.cap_total[y]
            rows.append(dict(情景=name, 年份=y, 送端扰动增量_kt=round(dE, 1),
                             碳排放_kt=round(E, 1), 上限_kt=cap,
                             越限_kt=round(max(0.0, E - cap), 1)))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "q4_stress.csv", index=False, encoding="utf-8-sig")
    return df


# ------------------------------------------------- 单情景 / 静态鲁棒模型
def build_q4_model(p4: Params4, xi: dict | None = None,
                   robust_gamma_scale: float | None = None,
                   robust_from: int | None = None,
                   fixed_x: dict | None = None) -> pyo.ConcreteModel:
    """在 Q3 模型上改造:碳上限软化 + ξ 冲击经 W 传导(或 Γ-鲁棒对偶)。

    xi: {(j,y): ξ} 情景乘数(未给出即 1)。
    robust_gamma_scale: 非 None 时对鲁棒年份启用 Γ-预算对等式。
    robust_from: 仅对 y ≥ robust_from 的年份用鲁棒对等式,之前年份用 xi
        (滚动调控的"已观测 + 未来鲁棒"混合模式);None 表示全部不确定
        年份均鲁棒。
    fixed_x: 固定的开工决策 {(p,t): v}(两阶段/滚动用)。
    """
    pa = p4.pa
    m = build_model(pa)
    m.del_component(m.c_cap)
    m.del_component(m.obj)
    m.viol = pyo.Var(PLAN_YEARS, domain=pyo.NonNegativeReals)

    def W_expr(m, j, y):
        return sum((m._dfinal(i, y) - m._clean(i, y)) * p4.S[i, j]
                   for i in REGIONS)

    m._W = W_expr
    xi = xi or {}

    def is_robust(y):
        return (robust_gamma_scale is not None and y in UNC_YEARS
                and (robust_from is None or y >= robust_from))

    if robust_gamma_scale is not None:
        m.pi = pyo.Var(UNC_YEARS, domain=pyo.NonNegativeReals)
        m.mu = pyo.Var(REGIONS, UNC_YEARS, domain=pyo.NonNegativeReals)
        m.c_dual = pyo.ConstraintList()
        for y in UNC_YEARS:
            if not is_robust(y):
                continue
            for j in REGIONS:
                m.c_dual.add(m.pi[y] + m.mu[j, y]
                             >= p4.ucoef(j, y) * W_expr(m, j, y))

    def cap_rule(m, y):
        base = sum(m._emis(i, y) for i in REGIONS)
        if is_robust(y):
            protect = (p4.gamma[y] * robust_gamma_scale * m.pi[y]
                       + sum(m.mu[j, y] for j in REGIONS))
            return base + protect <= pa.cap_total[y] + m.viol[y]
        dev = sum(pa.kappa[y] * p4.ebar[j] * (xi.get((j, y), 1.0) - 1.0)
                  * W_expr(m, j, y) for j in REGIONS)
        return base + dev <= pa.cap_total[y] + m.viol[y]

    m.c_cap2 = pyo.Constraint(PLAN_YEARS, rule=cap_rule)

    if fixed_x is not None:
        for (p, t), v in fixed_x.items():
            m.x[p, t].fix(v)

    m.obj = pyo.Objective(expr=(
        sum(pa.inv[p] * m.x[p, t] for p in pa.projects for t in PLAN_YEARS)
        + CARBON_PENALTY * sum(m.bex[i, y] for i in REGIONS
                               for y in PLAN_YEARS)
        + VOLL * sum(m._dfinal(i, y) - m.served[i, y] for i in REGIONS
                     for y in PLAN_YEARS)
        + CAP_VIOL_PENALTY * sum(m.viol[y] for y in PLAN_YEARS)
        + EPS_FLOW * sum(m.f[e, y, d] for e in pa.channels
                         for y in PLAN_YEARS for d in (0, 1))
        + EPS_FLOW * sum(m.imp[i, y] for i in REGIONS for y in PLAN_YEARS)))
    return m


def plan_metrics(p4: Params4, m: pyo.ConcreteModel) -> dict:
    pa = p4.pa
    inv = sum(pyo.value(m.x[p, t]) * pa.inv[p]
              for p in pa.projects for t in PLAN_YEARS)
    worst_viol = {}
    for y in UNC_YEARS:
        W = {j: pyo.value(m._W(m, j, y)) for j in REGIONS}
        xi = p4.worst_budget_xi(y, W)
        E = sum(pyo.value(m._emis(i, y)) for i in REGIONS) \
            + p4.delta_E(y, W, xi)
        worst_viol[y] = max(0.0, E - pa.cap_total[y])
    return dict(投资=inv, 最坏越限=worst_viol,
                总最坏越限=sum(worst_viol.values()),
                x={(p, t): pyo.value(m.x[p, t]) for p in pa.projects
                   for t in PLAN_YEARS if pyo.value(m.x[p, t]) > 1e-6})


def por_curve(p4: Params4) -> pd.DataFrame:
    """price-of-robustness:Γ 缩放 0→2 的成本与最坏越限。"""
    rows = []
    for tau in (0.0, 0.5, 1.0, 1.5, 2.0):
        m = build_q4_model(p4, robust_gamma_scale=tau)
        cost = solve(m)
        met = plan_metrics(p4, m)
        rows.append(dict(Gamma缩放=tau, 目标值_百万元=round(cost, 1),
                         投资_百万元=round(met["投资"], 1),
                         最坏情景总越限_kt=round(met["总最坏越限"], 2)))
        if tau == 1.0:
            pd.DataFrame([dict(项目=p, 开工年=t, 规模=round(v, 3))
                          for (p, t), v in met["x"].items()]) \
                .to_csv(OUT / "q4_robust_schedule.csv", index=False,
                        encoding="utf-8-sig")
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "q4_por_curve.csv", index=False, encoding="utf-8-sig")
    return df


# ------------------------------------------------------- 两阶段 C&CG
def _solve_extensive(p4: Params4, scen_set: dict):
    """共享 2026–2027 开工的多情景扩展模型(min 一阶段成本 + 最坏二阶段)。"""
    pa = p4.pa
    root = pyo.ConcreteModel("Q4_2stage")
    root.x1 = pyo.Var(pa.projects, list(FIRST_STAGE),
                      domain=pyo.NonNegativeReals)
    for p in ("P33", "P34", "P35"):
        for t in FIRST_STAGE:
            root.x1[p, t].domain = pyo.Binary
    root.eta_wc = pyo.Var(domain=pyo.Reals)
    root.link = pyo.ConstraintList()
    root.epi = pyo.ConstraintList()
    root._blocks = {}

    stage1_cost = sum(pa.inv[p] * root.x1[p, t]
                      for p in pa.projects for t in FIRST_STAGE)
    for k, xi in scen_set.items():
        sub = build_q4_model(p4, xi=xi)
        sub.obj.deactivate()
        root.add_component(f"blk_{k}", sub)
        root._blocks[k] = sub
        for p in pa.projects:
            for t in FIRST_STAGE:
                root.link.add(sub.x[p, t] == root.x1[p, t])
        stage2 = (
            sum(pa.inv[p] * sub.x[p, t] for p in pa.projects
                for t in (2028, 2029, 2030))
            + CARBON_PENALTY * sum(sub.bex[i, y] for i in REGIONS
                                   for y in PLAN_YEARS)
            + VOLL * sum(sub._dfinal(i, y) - sub.served[i, y]
                         for i in REGIONS for y in PLAN_YEARS)
            + CAP_VIOL_PENALTY * sum(sub.viol[y] for y in PLAN_YEARS)
            + EPS_FLOW * sum(sub.f[e, y, d] for e in pa.channels
                             for y in PLAN_YEARS for d in (0, 1))
            + EPS_FLOW * sum(sub.imp[i, y] for i in REGIONS
                             for y in PLAN_YEARS))
        root.epi.add(root.eta_wc >= stage2)

    root.obj = pyo.Objective(expr=stage1_cost + root.eta_wc)
    cost = solve(root)
    return root, cost


def ccg_two_stage(p4: Params4, max_iter: int = 4):
    """顶点加列:以各情景解的 W 构造预算集最坏 ξ,若仍越限则加入重解。"""
    scen_set: dict[str, dict] = {
        "S3": {(j, y): p4.xi_of("S3", j, y) for j in REGIONS
               for y in UNC_YEARS}}
    log = []
    m = cost = None
    for it in range(max_iter):
        m, cost = _solve_extensive(p4, scen_set)
        new_added = False
        for k, sub in list(m._blocks.items()):
            worst, viol = {}, 0.0
            for y in UNC_YEARS:
                W = {j: pyo.value(sub._W(sub, j, y)) for j in REGIONS}
                xi = p4.worst_budget_xi(y, W)
                E = sum(pyo.value(sub._emis(i, y)) for i in REGIONS) \
                    + p4.delta_E(y, W, xi)
                worst.update({(j, y): xi[j] for j in REGIONS})
                viol += max(0.0, E - p4.pa.cap_total[y])
            if viol > 1.0 and worst not in scen_set.values():
                scen_set[f"WC{len(scen_set)}"] = worst
                new_added = True
                break
        log.append(dict(迭代=it + 1, 情景数=len(scen_set),
                        目标值_百万元=round(cost, 1)))
        if not new_added:
            break
    x1 = {(p, t): pyo.value(m.x1[p, t]) for p in p4.pa.projects
          for t in FIRST_STAGE if pyo.value(m.x1[p, t]) > 1e-6}
    return cost, pd.DataFrame(log), x1, scen_set


# ------------------------------------------------------------- 滚动模拟
def rolling_simulation(p4: Params4, x1: dict) -> pd.DataFrame:
    """S3 路径下滚动调控:逐年观测 ξ,重解剩余期(已开工不可逆),
    未观测年份按 Γ-鲁棒对待(稳健滚动)。"""
    committed = {(p, t): v for (p, t), v in x1.items()}
    for p in p4.pa.projects:       # 第一阶段未选即为 0,滚动中不可回溯补建
        for t in FIRST_STAGE:
            committed.setdefault((p, t), 0.0)
    rows = []
    for y_now in UNC_YEARS:
        xi_known = {(j, y): p4.xi_of("S3", j, y)
                    for j in REGIONS for y in UNC_YEARS if y <= y_now}
        m = build_q4_model(p4, xi=xi_known, robust_gamma_scale=1.0,
                           robust_from=y_now + 1, fixed_x=committed)
        cost = solve(m)
        for p in p4.pa.projects:
            committed[(p, y_now)] = pyo.value(m.x[p, y_now])
        E = {}
        for y in UNC_YEARS:
            W = {j: pyo.value(m._W(m, j, y)) for j in REGIONS}
            xi_real = {j: p4.xi_of("S3", j, y) for j in REGIONS}
            E[y] = sum(pyo.value(m._emis(i, y)) for i in REGIONS) \
                + p4.delta_E(y, W, xi_real)
        rows.append(dict(决策年=y_now, 剩余期目标_百万元=round(cost, 1),
                         **{f"E{y}_kt": round(E[y], 1) for y in UNC_YEARS},
                         **{f"越限{y}_kt": round(
                             max(0.0, E[y] - p4.pa.cap_total[y]), 2)
                            for y in UNC_YEARS}))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "q4_rolling.csv", index=False, encoding="utf-8-sig")
    return df


def make_plots(stress: pd.DataFrame, por: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    plot_setup()

    fig, ax = plt.subplots(figsize=(7.2, 4))
    for name, g in stress.groupby("情景"):
        ax.plot(g["年份"], g["碳排放_kt"], "o-", label=name)
    caps = stress.drop_duplicates("年份")
    ax.plot(caps["年份"], caps["上限_kt"], "k--", lw=2, label="年度上限")
    ax.set_xticks(UNC_YEARS)
    ax.set_ylabel(r"消费侧碳排放 ktCO$_2$")
    ax.set_title("问题三方案在送端碳因子情景下的压力测试")
    ax.legend(fontsize=8)
    fig.savefig(OUT / "fig_q4_stress.png")
    plt.close(fig)

    fig, ax1 = plt.subplots(figsize=(7.2, 4))
    ax1.plot(por["Gamma缩放"], por["投资_百万元"], "o-", color="#1f77b4",
             label="总投资")
    ax1.set_xlabel(r"不确定预算缩放 $\tau(\Gamma_t \times \tau)$")
    ax1.set_ylabel("总投资(百万元)", color="#1f77b4")
    ax2 = ax1.twinx()
    ax2.plot(por["Gamma缩放"], por["最坏情景总越限_kt"], "s--",
             color="crimson", label="最坏情景总越限")
    ax2.set_ylabel(r"最坏情景总越限(ktCO$_2$)", color="crimson")
    ax2.grid(False)
    ax1.set_title("鲁棒性的代价(price of robustness)")
    fig.savefig(OUT / "fig_q4_por.png")
    plt.close(fig)


def main() -> None:
    p4 = Params4()

    stress = stress_test(p4)
    print("[Q4] 压力测试(问题三方案固定,越限 kt):")
    print(stress.pivot_table(index="情景", columns="年份", values="越限_kt")
          .to_string())

    por = por_curve(p4)
    print("[Q4] price-of-robustness:")
    print(por.to_string(index=False))

    cost2, log, x1, scen_set = ccg_two_stage(p4)
    log.to_csv(OUT / "q4_ccg_log.csv", index=False, encoding="utf-8-sig")
    print("[Q4] 两阶段 C&CG:", log.to_dict("records"))

    rolling = rolling_simulation(p4, x1)
    print("[Q4] S3 滚动模拟:")
    print(rolling.to_string(index=False))

    static_robust = por[por["Gamma缩放"] == 1.0].iloc[0]
    nominal = por[por["Gamma缩放"] == 0.0].iloc[0]
    summary = dict(
        确定性方案投资_百万元=float(nominal["投资_百万元"]),
        确定性最坏越限_kt=float(nominal["最坏情景总越限_kt"]),
        静态鲁棒投资_百万元=float(static_robust["投资_百万元"]),
        静态鲁棒最坏越限_kt=float(static_robust["最坏情景总越限_kt"]),
        鲁棒溢价_百万元=round(float(static_robust["投资_百万元"])
                              - float(nominal["投资_百万元"]), 1),
        两阶段目标_百万元=round(cost2, 1),
        两阶段情景数=len(scen_set),
        S3滚动末年越限_kt=float(rolling.iloc[-1]["越限2030_kt"]),
    )
    with open(OUT / "q4_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    make_plots(stress, por)
    print("[Q4] summary:", summary)
    print(f"[Q4] 输出目录: {OUT}")


if __name__ == "__main__":
    main()
