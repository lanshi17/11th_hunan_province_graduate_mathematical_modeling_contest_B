"""问题三:区域碳预算分配与低碳项目组合优化(五年 MILP)。

结构(Koltsaklis & Dagoumas 2018 投资-运行耦合范式):
- 碳预算分配层:全省消费侧年度上限(附件4B,硬约束)按"惯性份额 + 公平
  份额"凸组合分解为区域软预算(Raupach et al. 2014; Zhou & Wang 2016;
  Wang et al. 2013),超额按影子碳价 0.2 百万元/kt(即 200 元/tCO2)计罚。
- 项目组合层:35 个项目 × 5 年开工规模 MILP;效益自 开工年+建设周期 起
  生效;施工资源 C1–C5、年度投资上限、互斥(同年不能开工)、协同(累计
  规模均达 30% 上限后工业节电 +5%,McCormick 线性化)。
- 运行层:区域年度能量平衡(本地电源 ≤ 附件3B 基准规模、省外输入 ≤ 年容量
  上限、通道容量与线损用问题一校正值,升级项目改变容量与线损)。

碳核算(附件4B 官方简化):E_{i,y} = ρ_i·κ_y·(净需求 − 光伏就地供电)
+ EF_pv·光伏供电 − 直接减排;交通电气化新增用电计入净需求(间接排放),
其燃油替代计直接减排,不重复计算。ρ_i 为问题二 2025 终端碳强度,κ_y 为
基准供电碳强度调整系数。
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pyomo.environ as pyo

from ..common import data_io
from ..common.paths import CHANNELS, PLAN_YEARS, REGIONS, out_dir
from ..common.plotting import setup as plot_setup

Q1 = out_dir("q1")
Q2 = out_dir("q2")
OUT = out_dir("q3")

EF_PV = 0.045                    # 光伏排放因子 kgCO2/kWh(附件3A)
CARBON_PENALTY = 0.2             # 区域预算超额罚 百万元/ktCO2(≈200元/t)
VOLL = 10.0                      # 缺供罚 百万元/GWh(≈10元/kWh)
EPS_FLOW = 1e-4                  # 流量微小成本,消除退化环流
# 预算分配惯性权重:2026 年 0.85 线性过渡至 2030 年 0.65
# ("祖父份额→公平份额"的动态混合,Raupach 2014; Zhou & Wang 2016)
W_INERTIA = {2026: 0.85, 2027: 0.80, 2028: 0.75, 2029: 0.70, 2030: 0.65}


class Params:
    """从附件与 Q1/Q2 输出组装模型参数。"""

    def __init__(self, w_inertia: dict | None = None) -> None:
        w_inertia = w_inertia or W_INERTIA
        dev = data_io.load_region_development().set_index("区域")
        con = data_io.load_annual_constraints().set_index("年份")
        self.prj = data_io.load_projects().set_index("项目编号")
        self.res_lim = data_io.load_resource_limits().set_index("年份")
        ps = data_io.load_power_structure().set_index("区域")
        net = data_io.load_network().set_index("通道编号")
        rho = pd.read_csv(Q2 / "q2_rho_annual.csv").set_index("区域")
        eta = pd.read_csv(Q1 / "q1_eta.csv").set_index("通道")

        self.years = PLAN_YEARS
        self.regions = REGIONS
        self.projects = list(self.prj.index)
        self.channels = CHANNELS

        g = dev["2026—2030年均需求增速"]
        base = dev["2025终端用电基数(GWh)"]
        self.D_base = {(i, y): float(base[i] * (1 + g[i]) ** (y - 2025))
                       for i in REGIONS for y in self.years}
        self.kappa = con["基准供电碳强度调整系数(相对2025)"].to_dict()
        self.cap_total = con["消费侧碳排放上限(ktCO2)"].to_dict()
        self.min_serve = con["最低供能满足率"].to_dict()
        self.rho = rho["2025终端碳强度"].to_dict()

        self.gen_base = {i: float(ps.loc[i, ["2025火电(GWh)", "2025水电(GWh)",
                                             "2025风电(GWh)", "2025光伏(GWh)"]]
                                  .sum()) for i in REGIONS}
        self.imp_cap = ps["省外输入年容量上限(GWh)"].to_dict()
        self.imp_ef = ps["省外输入排放因子"].to_dict()

        self.ch_end = {e: (net.loc[e, "区域1"], net.loc[e, "区域2"])
                       for e in CHANNELS}
        self.ch_cap = {e: float(net.loc[e, "月度基准容量"]) for e in CHANNELS}
        self.eta = {e: float(eta.loc[e, "调和后估计"]) for e in CHANNELS}

        p = self.prj
        self.region_of = p["区域/位置"].to_dict()
        self.maxtot = p["最大总规模"].to_dict()
        self.maxstart = p["年度最大开工规模"].to_dict()
        self.inv = p["单位投资(百万元)"].to_dict()
        self.build = p["建设周期(年)"].astype(int).to_dict()
        self.save_u = p["节电量(GWh/单位·年)"].to_dict()
        self.clean_u = p["新增清洁供电(GWh/单位·年)"].to_dict()
        self.load_u = p["新增用电(GWh/单位·年)"].to_dict()
        self.abate_u = p["直接减排(ktCO2/单位·年)"].to_dict()
        self.chcap_u = p["新增输电容量(GWh/月·单位)"].to_dict()
        self.etadrop_u = p["线损率降低(百分点/单位)"].to_dict()
        self.rtype = p["施工资源类型"].to_dict()
        self.rneed = p["单位施工资源需求"].to_dict()

        self.upgrade_of = {"P33": "E04", "P34": "E05", "P35": "E09"}
        self.mutex = [("P33", "P35"), ("P34", "P35")]
        self.synergy = {"SYN-A2": ("P05", "P08"), "SYN-A4": ("P13", "P16"),
                        "SYN-A6": ("P21", "P24"), "SYN-A8": ("P29", "P32")}

        # 区域碳预算:惯性(2025消费碳份额)+ 公平(当年需求份额)
        resp = pd.read_csv(Q2 / "q2_responsibility.csv").set_index("区域")
        c2025 = resp["消费责任全口径C+"]
        inertia = (c2025 / c2025.sum()).to_dict()
        self.budget = {}
        for y in self.years:
            w = w_inertia[y]
            dsum = sum(self.D_base[i, y] for i in REGIONS)
            for i in REGIONS:
                eq = self.D_base[i, y] / dsum
                self.budget[i, y] = (w * inertia[i]
                                     + (1 - w) * eq) * self.cap_total[y]


def build_model(pa: Params, inv_scale: float = 1.0,
                cap_scale: float = 1.0, carbon_penalty: float | None = None,
                voll: float | None = None, discount: float = 0.0
                ) -> pyo.ConcreteModel:
    m = pyo.ConcreteModel("Q3")
    Y, P, R, E = pa.years, pa.projects, pa.regions, pa.channels
    upg = set(pa.upgrade_of)

    m.x = pyo.Var(P, Y, domain=pyo.NonNegativeReals)      # 开工规模
    for p in upg:                                          # 通道升级 0/1 回路
        for y in Y:
            m.x[p, y].domain = pyo.Binary
    m.s = pyo.Var(pa.synergy.keys(), Y, domain=pyo.Binary)  # 协同触发
    m.wsyn = pyo.Var(pa.synergy.keys(), Y, domain=pyo.NonNegativeReals)
    m.gen = pyo.Var(R, Y, domain=pyo.NonNegativeReals)
    m.imp = pyo.Var(R, Y, domain=pyo.NonNegativeReals)
    m.f = pyo.Var(E, Y, [0, 1], domain=pyo.NonNegativeReals)  # 两方向流
    m.fu = pyo.Var(E, Y, [0, 1], domain=pyo.NonNegativeReals)  # f×升级 线性化
    m.served = pyo.Var(R, Y, domain=pyo.NonNegativeReals)
    m.bex = pyo.Var(R, Y, domain=pyo.NonNegativeReals)     # 区域预算超额

    def xop(p, y):  # 已投运规模
        return sum(m.x[p, t] for t in Y if t + pa.build[p] <= y)

    def cumstart(p, y):
        return sum(m.x[p, t] for t in Y if t <= y)

    # ---- 项目侧约束 ----
    m.c_tot = pyo.Constraint(P, rule=lambda m, p:
                             sum(m.x[p, t] for t in Y) <= pa.maxtot[p])
    m.c_start = pyo.Constraint(P, Y, rule=lambda m, p, t:
                               m.x[p, t] <= pa.maxstart[p])
    m.c_res = pyo.Constraint(["C1", "C2", "C3", "C4", "C5"], Y,
                             rule=lambda m, k, t: sum(
                                 pa.rneed[p] * m.x[p, t] for p in P
                                 if pa.rtype[p] == k)
                             <= float(pa.res_lim.loc[t, {
                                 "C1": "C1工业改造", "C2": "C2建筑改造",
                                 "C3": "C3交通电气化", "C4": "C4分布式光伏",
                                 "C5": "C5输电升级"}[k]]))
    m.c_inv = pyo.Constraint(Y, rule=lambda m, t: sum(
        pa.inv[p] * m.x[p, t] for p in P)
        <= inv_scale * float(pa.res_lim.loc[t, "年度投资上限(百万元)"]))
    m.c_mut = pyo.Constraint(range(len(pa.mutex)), Y, rule=lambda m, k, t:
                             m.x[pa.mutex[k][0], t]
                             + m.x[pa.mutex[k][1], t] <= 1)

    # 协同触发与 McCormick(w = Xop_industrial × s)
    m.c_syn = pyo.ConstraintList()
    for r, (p_ind, p_pv) in pa.synergy.items():
        for y in Y:
            m.c_syn.add(0.3 * pa.maxtot[p_ind] * m.s[r, y]
                        <= cumstart(p_ind, y))
            m.c_syn.add(0.3 * pa.maxtot[p_pv] * m.s[r, y]
                        <= cumstart(p_pv, y))
            xm = pa.maxtot[p_ind]
            m.c_syn.add(m.wsyn[r, y] <= xop(p_ind, y))
            m.c_syn.add(m.wsyn[r, y] <= xm * m.s[r, y])

    def save(i, y):
        base = sum(pa.save_u[p] * xop(p, y) for p in P
                   if pa.region_of[p] == i)
        extra = sum(0.05 * pa.save_u[p_ind] * m.wsyn[r, y]
                    for r, (p_ind, _) in pa.synergy.items()
                    if pa.region_of[p_ind] == i)
        return base + extra

    def clean(i, y):
        return sum(pa.clean_u[p] * xop(p, y) for p in P
                   if pa.region_of[p] == i)

    def newload(i, y):
        return sum(pa.load_u[p] * xop(p, y) for p in P
                   if pa.region_of[p] == i)

    def abate(i, y):
        return sum(pa.abate_u[p] * xop(p, y) for p in P
                   if pa.region_of[p] == i)

    def dfinal(i, y):
        return pa.D_base[i, y] - save(i, y) + newload(i, y)

    def upgrade_op(e, y):  # 通道 e 升级是否已投运(线性 0/1 表达式)
        for p, ch in pa.upgrade_of.items():
            if ch == e:
                return xop(p, y)
        return 0

    # ---- 运行层 ----
    m.c_gen = pyo.Constraint(R, Y, rule=lambda m, i, y:
                             m.gen[i, y] <= pa.gen_base[i])
    m.c_imp = pyo.Constraint(R, Y, rule=lambda m, i, y:
                             m.imp[i, y] <= pa.imp_cap[i])
    m.c_fcap = pyo.ConstraintList()
    m.c_mc = pyo.ConstraintList()
    for e in E:
        dcap = pa.chcap_u.get({"E04": "P33", "E05": "P34",
                               "E09": "P35"}.get(e, ""), 0.0)
        fmax = 12 * (pa.ch_cap[e] + (dcap or 0.0))
        for y in Y:
            u = upgrade_op(e, y)
            cap_y = 12 * pa.ch_cap[e] + 12 * (dcap or 0.0) * u \
                if not isinstance(u, int) else 12 * pa.ch_cap[e]
            m.c_fcap.add(m.f[e, y, 0] + m.f[e, y, 1] <= cap_y)
            for d in (0, 1):
                if isinstance(u, int):     # 不可升级通道
                    m.c_mc.add(m.fu[e, y, d] == 0)
                else:                       # fu = f × u 的 McCormick 包络
                    m.c_mc.add(m.fu[e, y, d] <= m.f[e, y, d])
                    m.c_mc.add(m.fu[e, y, d] <= fmax * u)
                    m.c_mc.add(m.fu[e, y, d]
                               >= m.f[e, y, d] - fmax * (1 - u))

    def delivered(e, y, d):
        """方向 d 的到达电量 = (1−η)f + Δη·f·u。"""
        p_up = {"E04": "P33", "E05": "P34", "E09": "P35"}.get(e)
        eta_drop = (pa.etadrop_u[p_up] / 100.0) if p_up else 0.0
        return ((1 - pa.eta[e]) * m.f[e, y, d]
                + eta_drop * m.fu[e, y, d])

    def balance_rule(m, i, y):
        inflow = sum(delivered(e, y, 0) for e in E if pa.ch_end[e][1] == i) \
            + sum(delivered(e, y, 1) for e in E if pa.ch_end[e][0] == i)
        outflow = sum(m.f[e, y, 0] for e in E if pa.ch_end[e][0] == i) \
            + sum(m.f[e, y, 1] for e in E if pa.ch_end[e][1] == i)
        return (m.gen[i, y] + clean(i, y) + m.imp[i, y] + inflow - outflow
                == m.served[i, y])

    m.c_bal = pyo.Constraint(R, Y, rule=balance_rule)
    m.c_smin = pyo.Constraint(R, Y, rule=lambda m, i, y:
                              m.served[i, y] >= pa.min_serve[y] * dfinal(i, y))
    m.c_smax = pyo.Constraint(R, Y, rule=lambda m, i, y:
                              m.served[i, y] <= dfinal(i, y))

    # ---- 碳约束 ----
    def emis(i, y):
        rc = pa.rho[i] * pa.kappa[y]
        return (rc * (dfinal(i, y) - clean(i, y)) + EF_PV * clean(i, y)
                - abate(i, y))

    m.c_cap = pyo.Constraint(Y, rule=lambda m, y: sum(
        emis(i, y) for i in R) <= cap_scale * pa.cap_total[y])
    m.c_budget = pyo.Constraint(R, Y, rule=lambda m, i, y:
                                emis(i, y) - cap_scale * pa.budget[i, y]
                                <= m.bex[i, y])

    # ---- 目标 ----
    cp_ = CARBON_PENALTY if carbon_penalty is None else carbon_penalty
    voll_ = VOLL if voll is None else voll
    m.obj = pyo.Objective(expr=(
        sum(pa.inv[p] * m.x[p, t] / (1.0 + discount) ** (t - 2026)
            for p in P for t in Y)
        + cp_ * sum(m.bex[i, y] for i in R for y in Y)
        + voll_ * sum(dfinal(i, y) - m.served[i, y] for i in R for y in Y)
        + EPS_FLOW * sum(m.f[e, y, d] for e in E for y in Y for d in (0, 1))
        + EPS_FLOW * sum(m.imp[i, y] for i in R for y in Y)))
    m._emis, m._dfinal, m._save = emis, dfinal, save
    m._clean, m._newload, m._abate, m._xop = clean, newload, abate, xop
    return m


def solve(m: pyo.ConcreteModel, allow_infeasible: bool = False) -> float | None:
    """求解;不可行时返回 None(allow_infeasible)或抛错。"""
    opt = pyo.SolverFactory("appsi_highs")
    try:
        opt.config.mip_gap = 1e-6
    except Exception:
        pass
    try:
        res = opt.solve(m)
    except RuntimeError as err:
        if allow_infeasible and "feasible solution was not found" in str(err):
            return None
        raise
    try:
        tc = str(res.solver.termination_condition)
    except AttributeError:
        tc = str(res.termination_condition)
    if "optimal" not in tc.lower():
        if allow_infeasible:
            return None
        raise AssertionError(tc)
    return float(pyo.value(m.obj))


def extract(pa: Params, m: pyo.ConcreteModel) -> dict:
    Y, P, R = pa.years, pa.projects, pa.regions
    sched = []
    for p in P:
        for t in Y:
            v = pyo.value(m.x[p, t])
            if v > 1e-6:
                sched.append(dict(项目=p, 区域=pa.region_of[p],
                                  名称=pa.prj.loc[p, "项目名称"], 开工年=t,
                                  开工规模=round(v, 3),
                                  投资_百万元=round(v * pa.inv[p], 2)))
    sched_df = pd.DataFrame(sched)

    yearly = []
    for y in Y:
        E_y = sum(pyo.value(m._emis(i, y)) for i in R)
        yearly.append(dict(
            年份=y,
            投资_百万元=round(sum(pyo.value(m.x[p, y]) * pa.inv[p]
                                  for p in P), 2),
            消费侧碳排放_kt=round(E_y, 1),
            碳上限_kt=pa.cap_total[y],
            碳裕度_kt=round(pa.cap_total[y] - E_y, 1),
            总节电_GWh=round(sum(pyo.value(m._save(i, y)) for i in R), 1),
            光伏供电_GWh=round(sum(pyo.value(m._clean(i, y)) for i in R), 1),
            交通新增用电_GWh=round(sum(pyo.value(m._newload(i, y))
                                       for i in R), 1),
            直接减排_kt=round(sum(pyo.value(m._abate(i, y)) for i in R), 1),
            缺供_GWh=round(sum(pyo.value(m._dfinal(i, y) - m.served[i, y])
                               for i in R), 3),
            区域预算超额合计_kt=round(sum(pyo.value(m.bex[i, y])
                                          for i in R), 1),
        ))
    yearly_df = pd.DataFrame(yearly)

    regional = []
    for i in R:
        for y in Y:
            regional.append(dict(
                区域=i, 年份=y,
                净需求_GWh=round(pyo.value(m._dfinal(i, y)), 1),
                光伏供电_GWh=round(pyo.value(m._clean(i, y)), 1),
                消费碳_kt=round(pyo.value(m._emis(i, y)), 1),
                区域预算_kt=round(pa.budget[i, y], 1),
                预算超额_kt=round(pyo.value(m.bex[i, y]), 2),
                省外输入_GWh=round(pyo.value(m.imp[i, y]), 1)))
    return dict(sched=sched_df, yearly=yearly_df,
                regional=pd.DataFrame(regional))


def merit_order(pa: Params) -> pd.DataFrame:
    """静态单位减排成本(2030 口径,不含协同),用于解释 MILP 选择。"""
    rows = []
    for p in pa.projects:
        i = pa.region_of[p]
        if p in pa.upgrade_of:
            continue
        rc = pa.rho[i] * pa.kappa[2030]
        abate = (pa.save_u[p] * rc + pa.clean_u[p] * (rc - EF_PV)
                 + pa.abate_u[p] - pa.load_u[p] * rc)
        if abate <= 1e-9:
            continue
        rows.append(dict(项目=p, 区域=i, 名称=pa.prj.loc[p, "项目名称"],
                         年减排_kt_每单位=round(abate, 3),
                         单位投资_百万元=pa.inv[p],
                         单位减排成本_百万元每kt年=round(pa.inv[p] / abate, 2),
                         规划期内可用年数上限=int(5 - pa.build[p])))
    return pd.DataFrame(rows).sort_values("单位减排成本_百万元每kt年")


def shadow_prices(pa: Params) -> pd.DataFrame:
    """碳上限影子价格:CAP_y +10 kt 的有限差分。"""
    base = solve(build_model(pa))
    rows = []
    for y in pa.years:
        pa2 = Params()
        pa2.cap_total = dict(pa.cap_total)
        pa2.cap_total[y] += 10.0
        rows.append(dict(年份=y, 影子价格_百万元每kt=round(
            (base - solve(build_model(pa2))) / 10.0, 4)))
    return pd.DataFrame(rows)


def sensitivity(pa: Params) -> pd.DataFrame:
    """投资上限 × 碳上限网格,方案稳定性(项目-年 Jaccard)与成本变化。"""
    def footprint(m):
        return {(p, t) for p in pa.projects for t in pa.years
                if pyo.value(m.x[p, t]) > 1e-4}

    m0 = build_model(pa)
    c0 = solve(m0)
    f0 = footprint(m0)
    rows = []
    for inv_s in (0.8, 0.9, 1.0, 1.1, 1.2):
        for cap_s in (0.97, 1.0, 1.03):
            if inv_s == 1.0 and cap_s == 1.0:
                rows.append(dict(投资上限倍数=1.0, 碳上限倍数=1.0,
                                 总成本_百万元=round(c0, 1), Jaccard=1.0))
                continue
            mm = build_model(pa, inv_scale=inv_s, cap_scale=cap_s)
            c = solve(mm, allow_infeasible=True)
            if c is None:
                rows.append(dict(投资上限倍数=inv_s, 碳上限倍数=cap_s,
                                 总成本_百万元=np.nan, Jaccard=np.nan))
                continue
            f = footprint(mm)
            jac = len(f & f0) / max(len(f | f0), 1)
            rows.append(dict(投资上限倍数=inv_s, 碳上限倍数=cap_s,
                             总成本_百万元=round(c, 1), Jaccard=round(jac, 3)))
    return pd.DataFrame(rows)


def make_plots(res: dict, merit: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    plot_setup()

    y = res["yearly"]
    fig, ax1 = plt.subplots(figsize=(7.2, 4))
    ax1.plot(y["年份"], y["消费侧碳排放_kt"], "o-", label="优化后消费侧碳排放")
    ax1.plot(y["年份"], y["碳上限_kt"], "s--", color="crimson", label="年度碳上限")
    ax1.set_ylabel(r"ktCO$_2$")
    ax1.set_title("五年方案:消费侧碳排放轨迹与年度上限")
    ax1.legend(loc="upper right")
    ax2 = ax1.twinx()
    ax2.bar(y["年份"], y["投资_百万元"], alpha=0.25, color="gray", width=0.5)
    ax2.set_ylabel("年度投资(百万元)")
    ax2.grid(False)
    fig.savefig(OUT / "fig_q3_carbon_trajectory.png")
    plt.close(fig)

    s = res["sched"]
    piv = s.pivot_table(index="项目", columns="开工年", values="开工规模",
                        aggfunc="sum").fillna(0)
    fig, ax = plt.subplots(figsize=(7, max(3.0, 0.3 * len(piv))))
    im = ax.imshow(piv.to_numpy(), cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(piv.columns)), piv.columns)
    ax.set_yticks(range(len(piv)), piv.index)
    ax.set_title("项目开工规模安排(单位:各自规模单位)")
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.savefig(OUT / "fig_q3_schedule.png")
    plt.close(fig)

    top = merit.head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.barh(top["项目"] + " " + top["区域"], top["单位减排成本_百万元每kt年"])
    ax.set_xlabel(r"单位减排成本(百万元 / ktCO$_2\cdot$年,2030 口径)")
    ax.set_title("候选项目单位减排成本排序(前 12)")
    fig.savefig(OUT / "fig_q3_merit_order.png")
    plt.close(fig)


def main() -> None:
    pa = Params()
    m = build_model(pa)
    cost = solve(m)
    res = extract(pa, m)
    merit = merit_order(pa)
    print(f"[Q3] 最优目标 {cost:.1f} 百万元")
    print(res["yearly"].to_string(index=False))

    res["sched"].to_csv(OUT / "q3_schedule.csv", index=False,
                        encoding="utf-8-sig")
    res["yearly"].to_csv(OUT / "q3_yearly.csv", index=False,
                         encoding="utf-8-sig")
    res["regional"].to_csv(OUT / "q3_regional.csv", index=False,
                           encoding="utf-8-sig")
    merit.to_csv(OUT / "q3_merit_order.csv", index=False, encoding="utf-8-sig")

    sp = shadow_prices(pa)
    sp.to_csv(OUT / "q3_shadow_prices.csv", index=False, encoding="utf-8-sig")
    print("[Q3] 碳上限影子价格:\n", sp.to_string(index=False))

    sens = sensitivity(pa)
    sens.to_csv(OUT / "q3_sensitivity.csv", index=False, encoding="utf-8-sig")
    print("[Q3] 敏感性(Jaccard 方案稳定性):\n", sens.to_string(index=False))

    inv_total = float(res["sched"]["投资_百万元"].sum()) if len(
        res["sched"]) else 0.0
    bex_total = float(res["yearly"]["区域预算超额合计_kt"].sum())
    summary = dict(
        总投资_百万元=round(inv_total, 1),
        区域预算超额罚_百万元=round(CARBON_PENALTY * bex_total, 1),
        目标函数_百万元=round(cost, 1),
        入选项目数=int(res["sched"]["项目"].nunique()),
        碳排放全部达标=bool((res["yearly"]["碳裕度_kt"] >= -1e-6).all()),
        通道升级=sorted(res["sched"][res["sched"]["项目"]
                                     .isin(["P33", "P34", "P35"])]["项目"]
                        .unique().tolist()),
    )
    with open(OUT / "q3_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    make_plots(dict(**res, sens=sens), merit)
    print("[Q3] summary:", summary)
    print(f"[Q3] 输出目录: {OUT}")


if __name__ == "__main__":
    main()
