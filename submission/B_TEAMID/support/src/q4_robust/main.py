"""问题四:送端碳排不确定性与鲁棒滚动调控。

四层递进:
1. 压力测试:固定问题三方案,在 S0–S3 与预算集最坏情景下核算逐年碳排放
   (纯算术,附件6A/6B)。
2. 静态 Γ-预算对等式:预算不确定集 Γ_t(Bertsimas & Sim 2004)内层 max
   对偶化,嵌回带显式碳缺口的 MILP;另以 viol=0 二分硬可行半径,
   不把含残余缺口的方案称为完整鲁棒方案。
3. 2026–2027 开工为"此时此地"决策,2028–2030 追加项目为"观望"
   决策。预算集部分采用可行性场景生成启发式(不是精确 C&CG);典型
   S0–S3 则建立硬碳上限、非预见性共享一阶段的最小最大相对遗憾模型。
4. 滚动时域在 S3 下逐年模拟,严格区分全周期条件目标、历史沉没项与
   objective-to-go,并在同一决策时点比较更新/不更新的未来成本。

不确定性传导口径(与问题二追踪管线一致):送端因子扰动 ξ_{j,y} 通过 2025
年碳流追踪的"省外输入分接入区消费份额矩阵" S_{ij} 传导至各区消费碳:

    ΔE_y(ξ) = κ_y · Σ_j ē_j·(ξ_{j,y} − 1) · W_{j,y},
    W_{j,y} = Σ_i (净需求_{i,y} − 光伏供电_{i,y}) · S_{ij}。

W 只依赖需求侧决策(节电/电气化/光伏),扰动无法靠改写购电台账回避,
补偿机制体现为需求侧项目加码与光伏替代——与官方 ρ·κ 简化口径自洽。
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
import pyomo.environ as pyo

from ..common import data_io
from ..common.paths import PLAN_YEARS, REGIONS, out_dir
from ..common.plotting import savefig as save_fig
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
        """给定 W_j 与显式预算缩放,返回预算集内最坏 ξ。

        ``gamma_scale`` 保留 1.0 默认值仅为兼容外部分析脚本;Q4 主流程的
        所有调用均显式传值,避免把设计集 τΓ 与统一 Γ 回测混淆。
        """
        if gamma_scale < 0:
            raise ValueError("gamma_scale 必须非负")
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
                xi = p4.worst_budget_xi(y, W, gamma_scale=1.0)
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


# -------------------------------------------- 单情景 / Γ-预算软缺口模型
def build_q4_model(p4: Params4, xi: dict | None = None,
                   robust_gamma_scale: float | None = None,
                   robust_from: int | None = None,
                   fixed_x: dict | None = None,
                   inv_scale: float = 1.0,
                   resource_scale: float = 1.0) -> pyo.ConcreteModel:
    """在 Q3 模型上改造:碳上限软化 + ξ 冲击经 W 传导(或 Γ-鲁棒对偶)。

    xi: {(j,y): ξ} 情景乘数(未给出即 1)。
    robust_gamma_scale: 非 None 时对鲁棒年份启用 Γ-预算对等式。
    robust_from: 仅对 y ≥ robust_from 的年份用鲁棒对等式,之前年份用 xi
        (滚动调控的"已观测 + 未来鲁棒"混合模式);None 表示全部不确定
        年份均鲁棒。
    fixed_x: 固定的开工决策 {(p,t): v}(两阶段/滚动用)。
    inv_scale: 年度投资上限统一倍数;默认 1 保持题设约束。
    resource_scale: C1--C5 年度施工资源上限统一倍数;默认 1。
    """
    pa = p4.pa
    m = build_model(pa, inv_scale=inv_scale,
                    resource_scale=resource_scale)
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


def plan_metrics(p4: Params4, m: pyo.ConcreteModel,
                 gamma_scale: float = 1.0) -> dict:
    """在指定 ``gamma_scale * Γ`` 下对一个已求解方案做独立最坏回测。"""
    pa = p4.pa
    inv = sum(pyo.value(m.x[p, t]) * pa.inv[p]
              for p in pa.projects for t in PLAN_YEARS)
    worst_viol = {}
    worst_emis = {}
    for y in UNC_YEARS:
        W = {j: pyo.value(m._W(m, j, y)) for j in REGIONS}
        xi = p4.worst_budget_xi(y, W, gamma_scale=gamma_scale)
        E = sum(pyo.value(m._emis(i, y)) for i in REGIONS) \
            + p4.delta_E(y, W, xi)
        worst_emis[y] = E
        worst_viol[y] = max(0.0, E - pa.cap_total[y])
    return dict(投资=inv, 预算缩放=gamma_scale, 最坏碳排放=worst_emis,
                最坏越限=worst_viol,
                总最坏越限=sum(worst_viol.values()),
                x={(p, t): pyo.value(m.x[p, t]) for p in pa.projects
                   for t in PLAN_YEARS if pyo.value(m.x[p, t]) > 1e-6})


def por_curve(p4: Params4) -> pd.DataFrame:
    """price-of-robustness:同时报告设计集与统一 Γ 回测口径。"""
    rows = []
    for tau in (0.0, 0.5, 1.0, 1.5, 2.0):
        m = build_q4_model(p4, robust_gamma_scale=tau)
        cost = solve(m)
        design_met = plan_metrics(p4, m, gamma_scale=tau)
        reference_met = plan_metrics(p4, m, gamma_scale=1.0)
        rows.append(dict(Gamma缩放=tau, 目标值_百万元=round(cost, 1),
                         投资_百万元=round(design_met["投资"], 1),
                         设计集tauGamma违约_kt=round(
                             design_met["总最坏越限"], 2),
                         统一Gamma回测违约_kt=round(
                             reference_met["总最坏越限"], 2),
                         # 兼容旧读取器;其口径始终是统一 Γ 回测。
                         最坏情景总越限_kt=round(
                             reference_met["总最坏越限"], 2)))
        if tau == 1.0:
            pd.DataFrame([dict(项目=p, 开工年=t, 规模=round(v, 3))
                          for (p, t), v in design_met["x"].items()]) \
                .to_csv(OUT / "q4_robust_schedule.csv", index=False,
                        encoding="utf-8-sig")
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "q4_por_curve.csv", index=False, encoding="utf-8-sig")
    return df


def _solve_hard_budget_model(p4: Params4, gamma_scale: float,
                             inv_scale: float = 1.0,
                             resource_scale: float = 1.0):
    """固定省级越限为零;仅凭 optimal/infeasible 证书判定可行性。"""
    m = build_q4_model(p4, robust_gamma_scale=gamma_scale,
                       inv_scale=inv_scale,
                       resource_scale=resource_scale)
    for y in PLAN_YEARS:
        m.viol[y].fix(0.0)
    opt = pyo.SolverFactory("appsi_highs")
    try:
        opt.config.mip_gap = 1e-6
    except Exception:
        pass
    # 禁止自动载入,使 infeasible 返回正式状态而不是在载入空解时抛错。
    res = opt.solve(m, load_solutions=False)
    termination = str(res.solver.termination_condition).lower()
    if termination == "infeasible":
        return False, m, None
    if termination != "optimal":
        raise RuntimeError(
            "硬可行性判定未取得 optimal/infeasible 证书: "
            f"status={res.solver.status}, termination={termination}")
    m.solutions.load_from(res)
    return True, m, float(pyo.value(m.obj))


def _minimum_violation_profile(p4: Params4, gamma_scale: float) -> tuple[dict, float]:
    """字典序求最小总缺口,再在该缺口下求成本最低方案。"""
    m = build_q4_model(p4, robust_gamma_scale=gamma_scale)
    m.obj.deactivate()
    m.min_viol_obj = pyo.Objective(
        expr=sum(m.viol[y] for y in PLAN_YEARS))
    solve(m)
    min_total = float(sum(pyo.value(m.viol[y]) for y in PLAN_YEARS))

    m.min_viol_obj.deactivate()
    m.min_viol_cap = pyo.Constraint(
        expr=sum(m.viol[y] for y in PLAN_YEARS) <= min_total + 1e-7)
    m.obj.activate()
    solve(m)
    gaps = {y: max(0.0, float(pyo.value(m.viol[y])))
            for y in PLAN_YEARS}
    return dict(
        分年最小硬缺口_kt=gaps,
        最小总硬缺口_kt=sum(gaps.values()),
        对应投资_百万元=sum(
            p4.pa.inv[p] * pyo.value(m.x[p, t])
            for p in p4.pa.projects for t in PLAN_YEARS),
        对应目标_百万元=float(pyo.value(m.obj)),
    ), min_total


def hard_feasibility_diagnostics(p4: Params4, target_scale: float = 1.0,
                                 upper_scale: float = 2.0,
                                 tolerance: float = 1e-4) -> dict:
    """二分求项目—资源体系可承受的最大硬鲁棒半径 τ*。

    τ* 是在所有 ``viol[y] == 0`` 时仍可行的最大 Γ 缩放。另在题设
    ``target_scale`` 下做字典序最小缺口,从而区分硬鲁棒可行与软约束
    近鲁棒方案。
    """
    if target_scale < 0 or upper_scale <= 0 or tolerance <= 0:
        raise ValueError("硬可行诊断参数必须为正")

    feasible_zero, _, _ = _solve_hard_budget_model(p4, 0.0)
    if not feasible_zero:
        raise RuntimeError("名义模型在硬碳上限下不可行,无法定义 τ*")

    hi_feasible, _, _ = _solve_hard_budget_model(p4, upper_scale)
    trace = []
    if hi_feasible:
        lo = hi = upper_scale
        radius_truncated = True
    else:
        lo, hi = 0.0, upper_scale
        radius_truncated = False
        iteration = 0
        while hi - lo > tolerance:
            iteration += 1
            mid = 0.5 * (lo + hi)
            feasible, _, _ = _solve_hard_budget_model(p4, mid)
            trace.append(dict(迭代=iteration, 试探tau=mid,
                              硬零越限可行=feasible,
                              可行下界tau=mid if feasible else lo,
                              不可行上界tau=hi if feasible else mid))
            if feasible:
                lo = mid
            else:
                hi = mid

    tau_star = lo
    _, radius_model, radius_cost = _solve_hard_budget_model(p4, tau_star)
    radius_investment = sum(
        p4.pa.inv[p] * pyo.value(radius_model.x[p, t])
        for p in p4.pa.projects for t in PLAN_YEARS)
    target_feasible, _, _ = _solve_hard_budget_model(p4, target_scale)
    gap, _ = _minimum_violation_profile(p4, target_scale)

    trace_df = pd.DataFrame(trace, columns=[
        "迭代", "试探tau", "硬零越限可行", "可行下界tau", "不可行上界tau"])
    trace_df.to_csv(OUT / "q4_hard_feasibility_trace.csv", index=False,
                    encoding="utf-8-sig")
    pd.DataFrame([
        dict(年份=y, 最小硬缺口_kt=gap["分年最小硬缺口_kt"][y])
        for y in PLAN_YEARS
    ]).to_csv(OUT / "q4_hard_gap_by_year.csv", index=False,
              encoding="utf-8-sig")

    return dict(
        搜索上界_tau=upper_scale,
        搜索上界是否仍可行=radius_truncated,
        硬可行半径_tau_star=tau_star,
        tau_star对应投资_百万元=radius_investment,
        tau_star对应目标_百万元=radius_cost,
        题设目标_tau=target_scale,
        题设目标是否完整硬可行=target_feasible,
        **gap,
    )


def _minimum_hard_restoration_scale(
        p4: Params4, relax: str, tolerance: float = 1e-5,
        initial_upper: float = 1.25, max_upper: float = 16.0) -> dict:
    """包络二分 Γ=1 硬零越限所需的单类约束最小统一放宽。"""
    if relax not in {"investment", "resource"}:
        raise ValueError("relax 必须是 investment 或 resource")
    if tolerance <= 0 or initial_upper <= 1 or max_upper < initial_upper:
        raise ValueError("恢复可行性搜索参数不合法")

    def solve_at(scale: float):
        kwargs = ({"inv_scale": scale, "resource_scale": 1.0}
                  if relax == "investment" else
                  {"inv_scale": 1.0, "resource_scale": scale})
        return _solve_hard_budget_model(
            p4, gamma_scale=1.0, **kwargs)

    started = time.perf_counter()
    baseline_feasible, _, _ = solve_at(1.0)
    if baseline_feasible:
        raise AssertionError("Gamma=1 在原约束下意外硬可行,无需恢复搜索")

    lo, hi = 1.0, initial_upper
    hi_feasible, _, _ = solve_at(hi)
    bracket_solves = 1
    while not hi_feasible and hi < max_upper:
        lo = hi
        hi = min(max_upper, 2.0 * hi)
        hi_feasible, _, _ = solve_at(hi)
        bracket_solves += 1
    if not hi_feasible:
        label = "年度投资" if relax == "investment" else "五类施工资源"
        raise RuntimeError(f"仅放宽{label}至 {max_upper:g} 倍仍无法恢复硬可行")

    iterations = 0
    while hi - lo > tolerance:
        iterations += 1
        mid = 0.5 * (lo + hi)
        feasible, _, _ = solve_at(mid)
        if feasible:
            hi = mid
        else:
            lo = mid

    # 独立重求两个边界,防止把二分缓存状态或求解器偶然误差当成验证。
    below_feasible, _, _ = solve_at(lo)
    critical_feasible, critical_model, critical_cost = solve_at(hi)
    if below_feasible or not critical_feasible:
        raise AssertionError("硬可行恢复二分的边界验证失败")
    critical_metrics = plan_metrics(p4, critical_model, gamma_scale=1.0)
    if critical_metrics["总最坏越限"] > 1e-4:
        raise AssertionError("临界方案未通过独立 Gamma=1 最坏情景回测")

    label = ("年度投资上限" if relax == "investment"
             else "C1--C5施工资源上限")
    return dict(
        放宽对象=label,
        鲁棒预算Gamma缩放=1.0,
        基准倍数=1.0,
        基准硬零越限可行=bool(baseline_feasible),
        最大不可行倍数_下界=lo,
        最小可行倍数_上界=hi,
        二分区间宽度=hi - lo,
        最小相对放宽上界_percent=100.0 * (hi - 1.0),
        二分容差=tolerance,
        临界倍数硬零越限可行=bool(critical_feasible),
        略低倍数=lo,
        略低倍数硬零越限可行=bool(below_feasible),
        临界方案独立Gamma回测总越限_kt=float(
            critical_metrics["总最坏越限"]),
        临界方案投资_百万元=float(critical_metrics["投资"]),
        临界方案目标_百万元=float(critical_cost),
        括界求解次数=bracket_solves,
        二分迭代次数=iterations,
        运行时间_s=time.perf_counter() - started,
    )


def hard_feasibility_restoration(p4: Params4,
                                 tolerance: float = 1e-5) -> pd.DataFrame:
    """分别放宽投资与五类资源,恢复 Γ=1 硬零越限并保存审计包络。"""
    rows = [
        _minimum_hard_restoration_scale(
            p4, "investment", tolerance=tolerance),
        _minimum_hard_restoration_scale(
            p4, "resource", tolerance=tolerance),
    ]
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "q4_hard_restoration.csv", index=False,
              encoding="utf-8-sig")
    return df


# ----------------------------------------- 两阶段可行性场景生成启发式
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


def feasibility_scenario_generation(p4: Params4, max_iter: int = 4):
    """按当前情景解的暴露 W 添加最坏顶点的可行性启发式。

    该过程没有求解标准两阶段 ARO 的 ``max_xi min_x2 Q`` 分离子问题,
    也不会添加零越限但追索成本更高的场景,因此不得称为精确 C&CG。
    """
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
                xi = p4.worst_budget_xi(y, W, gamma_scale=1.0)
                E = sum(pyo.value(sub._emis(i, y)) for i in REGIONS) \
                    + p4.delta_E(y, W, xi)
                worst.update({(j, y): xi[j] for j in REGIONS})
                viol += max(0.0, E - p4.pa.cap_total[y])
            if viol > 1.0 and worst not in scen_set.values():
                scen_set[f"WC{len(scen_set)}"] = worst
                new_added = True
                break
        log.append(dict(方法="可行性场景生成启发式",
                        迭代=it + 1, 情景数=len(scen_set),
                        目标值_百万元=round(cost, 1)))
        if not new_added:
            break
    x1 = {(p, t): pyo.value(m.x1[p, t]) for p in p4.pa.projects
          for t in FIRST_STAGE if pyo.value(m.x1[p, t]) > 1e-6}
    return cost, pd.DataFrame(log), x1, scen_set


def ccg_two_stage(p4: Params4, max_iter: int = 4):
    """兼容旧调用名;实际方法是可行性场景生成启发式。"""
    return feasibility_scenario_generation(p4, max_iter=max_iter)


# ------------------------------------------------------------- 滚动模拟
def _objective_components(p4: Params4, m: pyo.ConcreteModel,
                          years) -> dict:
    """按年份集合拆分 Q4 目标,供滚动时域正确核算 sunk/to-go。"""
    pa = p4.pa
    years = list(years)
    investment = sum(pa.inv[p] * pyo.value(m.x[p, t])
                     for p in pa.projects for t in years)
    regional_penalty = CARBON_PENALTY * sum(
        pyo.value(m.bex[i, y]) for i in REGIONS for y in years)
    unserved_penalty = VOLL * sum(
        pyo.value(m._dfinal(i, y) - m.served[i, y])
        for i in REGIONS for y in years)
    violation_kt = sum(pyo.value(m.viol[y]) for y in years)
    violation_penalty = CAP_VIOL_PENALTY * violation_kt
    flow_tiebreak = EPS_FLOW * sum(
        pyo.value(m.f[e, y, d]) for e in pa.channels
        for y in years for d in (0, 1))
    import_tiebreak = EPS_FLOW * sum(
        pyo.value(m.imp[i, y]) for i in REGIONS for y in years)
    total = (investment + regional_penalty + unserved_penalty
             + violation_penalty + flow_tiebreak + import_tiebreak)
    return dict(
        投资_百万元=float(investment),
        区域预算罚_百万元=float(regional_penalty),
        缺供罚_百万元=float(unserved_penalty),
        省级碳缺口_kt=float(violation_kt),
        省级碳缺口罚_百万元=float(violation_penalty),
        流量微小项_百万元=float(flow_tiebreak + import_tiebreak),
        目标合计_百万元=float(total),
    )


def rolling_simulation(p4: Params4, x1: dict) -> pd.DataFrame:
    """S3 路径下滚动调控:逐年观测 ξ,重解剩余期(已开工不可逆),
    未观测年份按 Γ-预算集防护。

    信息价值在同一 ``y_now``、同一已承诺状态下,用“不使用本年观测”
    与“使用本年观测”的 objective-to-go 之差定义,不跨年份比较含沉没
    成本的全周期目标。
    """
    committed = {(p, t): v for (p, t), v in x1.items()}
    for p in p4.pa.projects:       # 第一阶段未选即为 0,滚动中不可回溯补建
        for t in FIRST_STAGE:
            committed.setdefault((p, t), 0.0)
    rows = []
    for y_now in UNC_YEARS:
        xi_prior = {(j, y): p4.xi_of("S3", j, y)
                    for j in REGIONS for y in UNC_YEARS if y < y_now}
        no_update = build_q4_model(
            p4, xi=xi_prior, robust_gamma_scale=1.0,
            robust_from=y_now, fixed_x=committed)
        no_update_cost = solve(no_update)
        no_update_togo = _objective_components(
            p4, no_update, (y for y in PLAN_YEARS if y >= y_now))

        xi_known = {(j, y): p4.xi_of("S3", j, y)
                    for j in REGIONS for y in UNC_YEARS if y <= y_now}
        m = build_q4_model(p4, xi=xi_known, robust_gamma_scale=1.0,
                           robust_from=y_now + 1, fixed_x=committed)
        cost = solve(m)
        past = _objective_components(
            p4, m, (y for y in PLAN_YEARS if y < y_now))
        togo = _objective_components(
            p4, m, (y for y in PLAN_YEARS if y >= y_now))
        all_years = _objective_components(p4, m, PLAN_YEARS)
        if abs(all_years["目标合计_百万元"] - cost) > 1e-4:
            raise AssertionError("rolling 目标拆分与模型目标不一致")

        for p in p4.pa.projects:
            committed[(p, y_now)] = pyo.value(m.x[p, y_now])
        E = {}
        for y in UNC_YEARS:
            W = {j: pyo.value(m._W(m, j, y)) for j in REGIONS}
            xi_real = {j: p4.xi_of("S3", j, y) for j in REGIONS}
            E[y] = sum(pyo.value(m._emis(i, y)) for i in REGIONS) \
                + p4.delta_E(y, W, xi_real)
        information_value = (no_update_togo["目标合计_百万元"]
                             - togo["目标合计_百万元"])
        if information_value < -1e-5:
            raise AssertionError("同状态下使用本年信息反而提高最优未来成本")
        rows.append(dict(
                         决策年=y_now,
                         全周期条件目标_百万元=round(cost, 3),
                         历史已发生目标项_百万元=round(
                             past["目标合计_百万元"], 3),
                         历史沉没投资_百万元=round(past["投资_百万元"], 3),
                         剩余期目标_百万元=round(
                             togo["目标合计_百万元"], 3),
                         剩余期投资_百万元=round(togo["投资_百万元"], 3),
                         全周期省级碳缺口罚_百万元=round(
                             all_years["省级碳缺口罚_百万元"], 3),
                         剩余期省级碳缺口罚_百万元=round(
                             togo["省级碳缺口罚_百万元"], 3),
                         不使用本年信息剩余期目标_百万元=round(
                             no_update_togo["目标合计_百万元"], 3),
                         本年信息价值_百万元=round(
                             max(0.0, information_value), 3),
                         不使用本年信息全周期目标_百万元=round(
                             no_update_cost, 3),
                         **{f"E{y}_kt": round(E[y], 1) for y in UNC_YEARS},
                         **{f"越限{y}_kt": round(
                             max(0.0, E[y] - p4.pa.cap_total[y]), 2)
                            for y in UNC_YEARS}))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "q4_rolling.csv", index=False, encoding="utf-8-sig")
    return df


# ---------------------------------------- S0--S3 硬约束最小最大相对遗憾
def _typical_scenarios(p4: Params4) -> dict[str, dict]:
    return {
        s: {(j, y): p4.xi_of(s, j, y)
            for j in REGIONS for y in UNC_YEARS}
        for s in ("S0", "S1", "S2", "S3")
    }


def _scenario_violation(p4: Params4, m: pyo.ConcreteModel,
                        xi: dict) -> dict[int, float]:
    """独立回代给定路径,不依赖模型中的软缺口变量。"""
    out = {}
    for y in PLAN_YEARS:
        base = sum(pyo.value(m._emis(i, y)) for i in REGIONS)
        dev = 0.0
        if y in UNC_YEARS:
            W = {j: pyo.value(m._W(m, j, y)) for j in REGIONS}
            xi_y = {j: xi.get((j, y), 1.0) for j in REGIONS}
            dev = p4.delta_E(y, W, xi_y)
        out[y] = max(0.0, base + dev - p4.pa.cap_total[y])
    return out


def minimax_relative_regret_four_paths(p4: Params4) -> tuple[pd.DataFrame, dict]:
    """四条典型路径的硬 cap、两阶段最小最大相对遗憾模型。

    S0--S3 只作为无概率的典型路径集合。PI 基准允许从 2026 年起知道
    完整路径;非预见方案共享 2026--2027 开工,路径追索自 2028 年分开。
    """
    pa = p4.pa
    scenarios = _typical_scenarios(p4)
    pi = {}
    for name, xi in scenarios.items():
        m_pi = build_q4_model(p4, xi=xi)
        for y in PLAN_YEARS:
            m_pi.viol[y].fix(0.0)
        pi_cost = solve(m_pi, allow_infeasible=True)
        if pi_cost is None:
            raise RuntimeError(f"典型路径 {name} 在硬碳上限下不可行")
        pi[name] = dict(
            目标_百万元=float(pi_cost),
            投资_百万元=float(sum(
                pa.inv[p] * pyo.value(m_pi.x[p, t])
                for p in pa.projects for t in PLAN_YEARS)),
        )

    root = pyo.ConcreteModel("Q4_four_path_minimax_relative_regret")
    root.x1 = pyo.Var(pa.projects, list(FIRST_STAGE),
                      domain=pyo.NonNegativeReals)
    for p in ("P33", "P34", "P35"):
        for t in FIRST_STAGE:
            root.x1[p, t].domain = pyo.Binary
    root.eta_rel = pyo.Var(domain=pyo.NonNegativeReals)
    root.link = pyo.ConstraintList()
    root.regret_c = pyo.ConstraintList()
    root._blocks = {}
    cost_expr = {}

    for name, xi in scenarios.items():
        sub = build_q4_model(p4, xi=xi)
        sub.obj.deactivate()
        for y in PLAN_YEARS:
            sub.viol[y].fix(0.0)
        root.add_component(f"path_{name}", sub)
        root._blocks[name] = sub
        for p in pa.projects:
            for t in FIRST_STAGE:
                root.link.add(sub.x[p, t] == root.x1[p, t])
        cost_expr[name] = sub.obj.expr
        root.regret_c.add(
            root.eta_rel >= ((cost_expr[name] - pi[name]["目标_百万元"])
                             / pi[name]["目标_百万元"]))

    root.obj = pyo.Objective(expr=root.eta_rel)
    solve(root)
    eta_star = float(pyo.value(root.eta_rel))

    # 字典序第二层:保持最大相对遗憾最优,消除非绑定路径的任意高成本解。
    regret_tolerance = max(1e-7, 1e-6 * max(1.0, eta_star))
    root.eta_cap = pyo.Constraint(
        expr=root.eta_rel <= eta_star + regret_tolerance)
    root.obj.deactivate()
    root.tie_obj = pyo.Objective(expr=sum(cost_expr.values()))
    solve(root)

    first_stage_investment = float(sum(
        pa.inv[p] * pyo.value(root.x1[p, t])
        for p in pa.projects for t in FIRST_STAGE))
    rows, schedule_rows = [], []
    for name, xi in scenarios.items():
        sub = root._blocks[name]
        path_cost = float(pyo.value(cost_expr[name]))
        path_investment = float(sum(
            pa.inv[p] * pyo.value(sub.x[p, t])
            for p in pa.projects for t in PLAN_YEARS))
        abs_regret = path_cost - pi[name]["目标_百万元"]
        rel_regret = abs_regret / pi[name]["目标_百万元"]
        violation = _scenario_violation(p4, sub, xi)
        rows.append(dict(
            情景=name,
            PI目标_百万元=pi[name]["目标_百万元"],
            PI投资_百万元=pi[name]["投资_百万元"],
            非预见方案目标_百万元=path_cost,
            非预见方案投资_百万元=path_investment,
            共享一阶段投资_百万元=first_stage_investment,
            绝对遗憾_百万元=abs_regret,
            相对遗憾=rel_regret,
            相对遗憾_百分比=100.0 * rel_regret,
            总越限_kt=sum(violation.values()),
            最大年度越限_kt=max(violation.values()),
            硬碳约束满足=sum(violation.values()) <= 1e-5,
        ))
        for p in pa.projects:
            for t in PLAN_YEARS:
                value = float(pyo.value(sub.x[p, t]))
                if value > 1e-6:
                    schedule_rows.append(dict(
                        情景=name, 项目=p, 开工年=t, 规模=value,
                        阶段="共享一阶段" if t in FIRST_STAGE else "路径追索",
                        投资_百万元=pa.inv[p] * value))

    paths = pd.DataFrame(rows)
    paths.to_csv(OUT / "q4_regret_paths.csv", index=False,
                 encoding="utf-8-sig")
    pd.DataFrame(schedule_rows).to_csv(
        OUT / "q4_regret_schedule.csv", index=False, encoding="utf-8-sig")

    n_var = sum(1 for _ in root.component_data_objects(pyo.Var, active=True))
    n_binary = sum(1 for v in root.component_data_objects(
        pyo.Var, active=True) if v.is_binary())
    n_con = sum(1 for _ in root.component_data_objects(
        pyo.Constraint, active=True))
    result = dict(
        方法="S0-S3四路径硬cap最小最大相对遗憾",
        路径是否赋概率=False,
        非预见性口径="2026-2027共享;2028-2030路径追索",
        最大相对遗憾=float(paths["相对遗憾"].max()),
        最大相对遗憾_百分比=float(paths["相对遗憾_百分比"].max()),
        共享一阶段投资_百万元=first_stage_investment,
        四路径全部硬达标=bool(paths["硬碳约束满足"].all()),
        PI目标_百万元={r["情景"]: float(r["PI目标_百万元"])
                   for _, r in paths.iterrows()},
        路径目标_百万元={r["情景"]: float(r["非预见方案目标_百万元"])
                       for _, r in paths.iterrows()},
        路径投资_百万元={r["情景"]: float(r["非预见方案投资_百万元"])
                       for _, r in paths.iterrows()},
        模型规模=dict(变量=n_var, 二元变量=n_binary, 约束=n_con),
    )
    with open(OUT / "q4_regret_summary.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return paths, result


def make_regret_plot(paths: pd.DataFrame) -> None:
    """PI 与非预见方案的哑铃对照，不以柱/折线表示。"""
    import matplotlib.pyplot as plt

    from ..common.advanced_plots import dumbbell

    plot_setup()
    fig, (ax_cost, ax_inv) = plt.subplots(2, 1, figsize=(7.2, 5.4))
    dumbbell(ax_cost, paths["情景"], paths["PI目标_百万元"],
             paths["非预见方案目标_百万元"], "完全信息目标", "非预见目标")
    ax_cost.set_xlabel("目标值(百万元)")
    dumbbell(ax_inv, paths["情景"], paths["PI投资_百万元"],
             paths["非预见方案投资_百万元"], "完全信息投资", "非预见投资")
    ax_inv.set_xlabel("投资(百万元)")
    save_fig(fig, OUT / "fig_q4_regret.png")
    plt.close(fig)


def make_plots(stress: pd.DataFrame, por: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from ..common.advanced_plots import annotated_heatmap, connected_scatter

    plot_setup()

    piv = (stress.pivot_table(index="情景", columns="年份", values="越限_kt")
           .reindex(columns=UNC_YEARS))
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    im = annotated_heatmap(ax, piv.to_numpy(float), [str(c) for c in piv.columns],
                           list(piv.index), cmap="Reds", fmt=".1f",
                           skip_zero=False)
    fig.colorbar(im, ax=ax, shrink=0.85).set_label(r"越限 ktCO$_2$")
    save_fig(fig, OUT / "fig_q4_stress.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    inv = por["投资_百万元"].to_numpy(float)
    worst = por["最坏情景总越限_kt"].to_numpy(float)
    design = por["设计集tauGamma违约_kt"].to_numpy(float)
    tau = por["Gamma缩放"].to_numpy(float)
    labels = [rf"$\tau={t:g}$" for t in tau]
    sizes = 50 + 90 * (tau / max(float(tau.max()), 1e-9))
    connected_scatter(ax, inv, worst, labels, color="#0072B2", sizes=sizes)
    ax.scatter(inv, design, s=sizes, marker="s", color="#D55E00",
               edgecolors="white", linewidths=0.4, zorder=2,
               label=r"设计集 $\tau\Gamma$ 违约")
    ax.scatter([], [], s=40, color="#0072B2", label=r"统一 $\Gamma$ 回测违约")
    ax.set_xlabel("总投资(百万元)")
    ax.set_ylabel(r"省级碳缺口(ktCO$_2$)")
    ax.legend(fontsize=8)
    save_fig(fig, OUT / "fig_q4_por.png")
    plt.close(fig)


def main() -> None:
    p4 = Params4()

    stress = stress_test(p4)
    print("[Q4] 压力测试(问题三方案固定,越限 kt):")
    print(stress.pivot_table(index="情景", columns="年份", values="越限_kt")
          .to_string())

    por = por_curve(p4)
    print("[Q4] price-of-robustness(设计集与统一 Γ 回测双口径):")
    print(por.to_string(index=False))

    hard = hard_feasibility_diagnostics(p4)
    print("[Q4] 硬可行半径与 Γ=1 最小缺口:")
    print(json.dumps(hard, ensure_ascii=False, indent=2))

    restoration = hard_feasibility_restoration(p4)
    print("[Q4] Γ=1 硬零越限的单类约束最小统一放宽:")
    print(restoration.to_string(index=False))

    cost2, log, x1, scen_set = feasibility_scenario_generation(p4)
    log.to_csv(OUT / "q4_ccg_log.csv", index=False, encoding="utf-8-sig")
    print("[Q4] 可行性场景生成启发式(兼容文件 q4_ccg_log.csv):",
          log.to_dict("records"))

    rolling = rolling_simulation(p4, x1)
    print("[Q4] S3 滚动模拟:")
    print(rolling.to_string(index=False))

    regret_paths, regret = minimax_relative_regret_four_paths(p4)
    print("[Q4] S0--S3 四路径硬 cap 最小最大相对遗憾:")
    print(regret_paths.to_string(index=False))

    gamma1_soft = por[por["Gamma缩放"] == 1.0].iloc[0]
    nominal = por[por["Gamma缩放"] == 0.0].iloc[0]
    inv_restore = restoration[restoration["放宽对象"] == "年度投资上限"].iloc[0]
    res_restore = restoration[
        restoration["放宽对象"] == "C1--C5施工资源上限"].iloc[0]
    summary = dict(
        确定性方案投资_百万元=float(nominal["投资_百万元"]),
        确定性方案统一Gamma回测违约_kt=float(
            nominal["统一Gamma回测违约_kt"]),
        Gamma1软约束方案投资_百万元=float(gamma1_soft["投资_百万元"]),
        Gamma1软约束方案设计集违约_kt=float(
            gamma1_soft["设计集tauGamma违约_kt"]),
        Gamma1软约束方案统一Gamma回测违约_kt=float(
            gamma1_soft["统一Gamma回测违约_kt"]),
        Gamma1软约束溢价_百万元=round(
            float(gamma1_soft["投资_百万元"])
            - float(nominal["投资_百万元"]), 1),
        Gamma1是否完整硬可行=bool(hard["题设目标是否完整硬可行"]),
        硬可行半径_tau_star=float(hard["硬可行半径_tau_star"]),
        Gamma1最小总硬缺口_kt=float(hard["最小总硬缺口_kt"]),
        Gamma1分年最小硬缺口_kt=hard["分年最小硬缺口_kt"],
        Gamma1硬零越限_年度投资上限最小倍数=float(
            inv_restore["最小可行倍数_上界"]),
        Gamma1硬零越限_五类施工资源上限最小统一倍数=float(
            res_restore["最小可行倍数_上界"]),
        Gamma1硬零越限_恢复验证={
            "原约束可行": bool(inv_restore["基准硬零越限可行"]),
            "年度投资上限": {
                "最大不可行倍数_下界": float(
                    inv_restore["最大不可行倍数_下界"]),
                "最小可行倍数_上界": float(
                    inv_restore["最小可行倍数_上界"]),
                "临界倍数可行": bool(
                    inv_restore["临界倍数硬零越限可行"]),
                "略低倍数可行": bool(
                    inv_restore["略低倍数硬零越限可行"]),
                "独立Gamma回测总越限_kt": float(
                    inv_restore["临界方案独立Gamma回测总越限_kt"]),
            },
            "五类施工资源上限": {
                "最大不可行倍数_下界": float(
                    res_restore["最大不可行倍数_下界"]),
                "最小可行倍数_上界": float(
                    res_restore["最小可行倍数_上界"]),
                "临界倍数可行": bool(
                    res_restore["临界倍数硬零越限可行"]),
                "略低倍数可行": bool(
                    res_restore["略低倍数硬零越限可行"]),
                "独立Gamma回测总越限_kt": float(
                    res_restore["临界方案独立Gamma回测总越限_kt"]),
            },
        },
        可行性场景生成启发式目标_百万元=round(cost2, 1),
        可行性场景生成启发式情景数=len(scen_set),
        S3滚动末年越限_kt=float(rolling.iloc[-1]["越限2030_kt"]),
        S3滚动逐年信息价值_百万元={
            int(r["决策年"]): float(r["本年信息价值_百万元"])
            for _, r in rolling.iterrows()},
        四路径最小最大相对遗憾=regret,
        口径说明=("Gamma1方案允许省级碳缺口并按50百万元/kt处罚;"
                  "其完整Gamma硬可行性必须读取Gamma1是否完整硬可行与"
                  "Gamma1最小总硬缺口,不得称为完整鲁棒零越限。"),
    )
    with open(OUT / "q4_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    make_plots(stress, por)
    make_regret_plot(regret_paths)
    print("[Q4] summary:", summary)
    print(f"[Q4] 输出目录: {OUT}")


if __name__ == "__main__":
    main()
