"""问题一:多源能源数据一致性校正与可信性评价。

主方法是守恒约束下的标准化 Huber 数据调和；加权最小二乘(WLS)保留为
对照。Huber 在小残差区与 WLS 一致，在粗差区转为线性增长，从而避免
少数异常观测支配全网校正。通道工程线损只作为年度聚合软先验进入一次
稳定凸优化，求解后再由年度送/受端调和电量估计线损率，不再做会漂移的
固定次数 eta 回灌。

平衡口径:入流按受端计量(过网损耗已扣),出流按送端计量,通道损耗
"落在线上";区内输配损耗 L_{i,t} 为非负自由变量,先验 5% × 终端用电。
影响度采用同一算法下的对称有限差分，并分别报告用电与线损无量纲弹性。
"""
from __future__ import annotations

import json

import cvxpy as cp
import numpy as np
import pandas as pd

from ..common import data_io
from ..common.paths import CHANNELS, MONTHS, REGIONS, SECTORS, SOURCES, out_dir
from ..common.plotting import savefig as save_fig
from ..common.plotting import setup as plot_setup

OUT = out_dir("q1")

GEN_COLS = [f"{s}发电量" for s in SOURCES]
IMP_COL = "省外输入电量"
TOT_COL = "终端用电合计"

# 相对不确定度(σ = max(rel·|obs|, floor)),月度监测较粗、年度汇总较准
SIG = {
    "gen": (0.020, 1.0), "imp": (0.020, 0.5), "dem": (0.020, 1.0),
    "demtot": (0.015, 1.0), "flow": (0.025, 0.5),
    "ann": (0.015, 2.0), "ann_ch": (0.015, 1.0),
}
LOSS_PRIOR_RATE = 0.05          # 区内输配损耗先验比例
LOSS_PRIOR_REL = 0.5            # 先验松弛度(σ = 0.5×先验值)
ETA_PRIOR_REL, ETA_PRIOR_FLOOR = 0.010, 0.3
DEFAULT_METHOD = "huber"
HUBER_DELTA = 1.5               # 作用于已除以 σ 的标准化残差
INFLUENCE_REL_STEP = 0.05


def _sigma(obs: np.ndarray, key: str) -> np.ndarray:
    rel, floor = SIG[key]
    return np.maximum(rel * np.abs(np.nan_to_num(obs)), floor)


class Dataset:
    """把附件 1/2 对齐成建模用数组。行序:mr 原始 96 行(月主序)。"""

    def __init__(self) -> None:
        self.mr = data_io.load_monthly_region()
        self.mc = data_io.load_monthly_channel()
        self.ann = data_io.load_annual_summary().set_index("区域")
        self.aux_top, self.aux_ch = data_io.load_aux_monitor()
        self.net = data_io.load_network().set_index("通道编号")

        self.gen_obs = self.mr[GEN_COLS].to_numpy(float)            # (96,4)
        self.imp_obs = self.mr[IMP_COL].to_numpy(float)             # (96,)
        self.dem_obs = self.mr[SECTORS].to_numpy(float)             # (96,4)
        self.tot_obs = self.mr[TOT_COL].to_numpy(float)             # (96,)
        self.row_region = self.mr["区域"].to_numpy()
        self.row_month = self.mr["月份"].to_numpy()

        self.sent_obs = self.mc["送端计量电量"].to_numpy(float)     # (132,)
        self.recv_obs = self.mc["受端计量电量"].to_numpy(float)
        self.cap = self.mc["通道月度容量上限"].to_numpy(float)
        self.zero_flow = (self.sent_obs <= 1e-9) & (self.recv_obs <= 1e-9)
        self.eta_eng = self.net["工程参考线损率"].reindex(CHANNELS).to_numpy(float)

        # 每个 (区域,月) 的进/出通道行号
        self.in_rows = {(r, m): [] for r in REGIONS for m in MONTHS}
        self.out_rows = {(r, m): [] for r in REGIONS for m in MONTHS}
        for j, row in self.mc.iterrows():
            self.out_rows[(row["送端区域"], row["月份"])].append(j)
            self.in_rows[(row["受端区域"], row["月份"])].append(j)
        self.ch_rows = {e: self.mc.index[self.mc["通道编号"] == e].tolist()
                        for e in CHANNELS}


def detect_anomalies(ds: Dataset) -> pd.DataFrame:
    """校正前的异常/不一致清单(供论文表格与影响度候选)。"""
    rows = []

    def add(kind, loc, field, detail, severity):
        rows.append(dict(类型=kind, 位置=loc, 字段=field, 说明=detail,
                         严重度=round(float(severity), 4)))

    # 1) 缺失
    for i in np.argwhere(ds.mr[GEN_COLS + SECTORS + [IMP_COL, TOT_COL]]
                         .isna().to_numpy()):
        r, c = i
        col = (GEN_COLS + SECTORS + [IMP_COL, TOT_COL])[c]
        add("缺失", f"{ds.row_month[r]}/{ds.row_region[r]}", col, "监测值为空", 1)

    # 2) 部门和 ≠ 合计
    sec_sum = np.nansum(ds.dem_obs, axis=1)
    with np.errstate(invalid="ignore"):
        rel = np.abs(sec_sum - ds.tot_obs) / np.maximum(ds.tot_obs, 1e-9)
    for r in np.where(rel > 0.005)[0]:
        add("口径不一致", f"{ds.row_month[r]}/{ds.row_region[r]}",
            "部门和vs合计", f"相对偏差 {rel[r]:.2%}", rel[r])

    # 3) 月度累加 vs 年度汇总(附件2A)
    mr = ds.mr.copy()
    mr["本地发电量"] = mr[GEN_COLS].sum(axis=1)
    agg = mr.groupby("区域")[["本地发电量", IMP_COL, TOT_COL, "工业用电"]].sum()
    pairs = [("本地发电量", "本地发电量"), (IMP_COL, "省外输入电量"),
             (TOT_COL, "终端用电量"), ("工业用电", "工业用电量")]
    for r in REGIONS:
        for mcol, acol in pairs:
            a, m = ds.ann.loc[r, acol], agg.loc[r, mcol]
            if max(abs(a), abs(m)) < 1e-6:
                continue
            rel = abs(a - m) / max(abs(a), 1e-9)
            if rel > 0.01:
                add("两套系统矛盾", r, f"月度Σ{mcol} vs 年度{acol}",
                    f"月度Σ={m:.1f}, 年度={a:.1f}, 偏差 {rel:.2%}", rel)

    # 4) 通道月度隐含损耗率异常 / 超容量
    with np.errstate(divide="ignore", invalid="ignore"):
        implied = 1 - ds.recv_obs / np.where(ds.sent_obs > 0, ds.sent_obs, np.nan)
    for j in range(len(ds.mc)):
        if ds.zero_flow[j]:
            continue
        e = ds.mc.loc[j, "通道编号"]
        eng = ds.net.loc[e, "工程参考线损率"]
        if implied[j] < 0:
            add("受端>送端", f"{ds.mc.loc[j, '月份']}/{e}", "隐含损耗率",
                f"隐含 {implied[j]:.3f} < 0", abs(implied[j]))
        elif implied[j] > 3 * eng:
            add("损耗率偏高", f"{ds.mc.loc[j, '月份']}/{e}", "隐含损耗率",
                f"隐含 {implied[j]:.3f} vs 工程 {eng:.3f}", implied[j] / eng)
        if ds.sent_obs[j] > ds.cap[j] + 1e-6:
            add("超容量", f"{ds.mc.loc[j, '月份']}/{e}", "送端电量",
                f"{ds.sent_obs[j]:.1f} > 上限 {ds.cap[j]:.0f}",
                ds.sent_obs[j] / ds.cap[j])

    # 5) 附件1B 年度累加 vs 附件2B 通道年度汇总;E10 受端>送端
    for _, row in ds.aux_ch.iterrows():
        e = row["通道编号"]
        js = ds.ch_rows[e]
        s_m, r_m = ds.sent_obs[js].sum(), ds.recv_obs[js].sum()
        for lab, mv, av in [("送端", s_m, row["年度送端汇总"]),
                            ("受端", r_m, row["年度受端汇总"])]:
            if max(av, mv) < 1e-6:
                continue
            rel = abs(av - mv) / max(av, 1e-9)
            if rel > 0.005:
                add("两套系统矛盾", e, f"{lab}年度汇总",
                    f"月度Σ={mv:.1f}, 2B={av:.1f}, 偏差 {rel:.2%}", rel)
        if row["年度受端汇总"] > row["年度送端汇总"] > 0:
            add("受端>送端", e, "2B年度汇总",
                f"送 {row['年度送端汇总']:.1f} < 受 {row['年度受端汇总']:.1f}",
                row["年度受端汇总"] / row["年度送端汇总"] - 1)

    # 6) 原始平衡残差(标准化)
    res, sig = _raw_balance_residual(ds)
    z = res / sig
    for k in np.where(np.abs(z) > 3)[0]:
        add("平衡残差超限", f"{ds.row_month[k]}/{ds.row_region[k]}", "能量平衡",
            f"残差 {res[k]:.1f} GWh, z={z[k]:.1f}", abs(z[k]))

    df = pd.DataFrame(rows).sort_values("严重度", ascending=False)
    df.to_csv(OUT / "q1_anomalies.csv", index=False, encoding="utf-8-sig")
    return df


def _raw_balance_residual(ds: Dataset) -> tuple[np.ndarray, np.ndarray]:
    """原始数据的能量平衡残差与其近似标准差(缺失按 0 计并放大σ)。"""
    res = np.zeros(96)
    sig2 = np.zeros(96)
    for k in range(96):
        r, m = ds.row_region[k], ds.row_month[k]
        gen = np.nansum(ds.gen_obs[k])
        imp = np.nan_to_num(ds.imp_obs[k])
        dem = np.nansum(ds.dem_obs[k])
        fin = ds.recv_obs[ds.in_rows[(r, m)]].sum()
        fout = ds.sent_obs[ds.out_rows[(r, m)]].sum()
        res[k] = gen + imp + fin - fout - dem - LOSS_PRIOR_RATE * dem
        sig2[k] = (np.nansum(_sigma(ds.gen_obs[k], "gen") ** 2)
                   + _sigma(np.array([imp]), "imp")[0] ** 2
                   + np.nansum(_sigma(ds.dem_obs[k], "dem") ** 2)
                   + (LOSS_PRIOR_REL * LOSS_PRIOR_RATE * dem) ** 2
                   + np.sum(_sigma(ds.recv_obs[ds.in_rows[(r, m)]], "flow") ** 2)
                   + np.sum(_sigma(ds.sent_obs[ds.out_rows[(r, m)]], "flow") ** 2))
    return res, np.sqrt(sig2)


class ReconcileResult:
    def __init__(self, gen, imp, dem, loss, sent, recv, eta_hat, obj, n_obs,
                 *, eta_identifiable, method, huber_delta, n_prior,
                 data_residuals, prior_residuals, status):
        self.gen, self.imp, self.dem, self.loss = gen, imp, dem, loss
        self.sent, self.recv = sent, recv
        self.eta_hat, self.obj, self.n_obs = eta_hat, obj, n_obs
        self.eta_identifiable = np.asarray(eta_identifiable, dtype=bool)
        self.method = method
        self.huber_delta = float(huber_delta)
        self.n_prior = int(n_prior)
        self.data_residuals = np.asarray(data_residuals, dtype=float)
        self.prior_residuals = np.asarray(prior_residuals, dtype=float)
        self.standardized_data_rss = float(self.data_residuals @ self.data_residuals)
        self.standardized_prior_rss = float(
            self.prior_residuals @ self.prior_residuals)
        self.robust_data_objective = _huber_value(
            self.data_residuals, self.huber_delta)
        self.status = status


def _huber_value(residual: np.ndarray, delta: float) -> float:
    """与 cvxpy.huber 一致的数值目标:小残差 r²,大残差线性。"""
    a = np.abs(np.asarray(residual, dtype=float))
    return float(np.where(a <= delta, a ** 2,
                          2 * delta * a - delta ** 2).sum())


def reconcile(ds: Dataset, override: dict | None = None,
              method: str = DEFAULT_METHOD,
              huber_delta: float = HUBER_DELTA,
              n_iter: int | None = None) -> ReconcileResult:
    """单次凸数据调和。

    ``override`` 形如 ``{(table, key): new_obs}``，供有限差分与污染试验使用。
    ``n_iter`` 仅为旧调用兼容参数，已不参与计算；当前模型不再回灌 eta。
    """
    del n_iter
    method = method.lower()
    if method not in {"huber", "wls"}:
        raise ValueError(f"unknown reconciliation method: {method}")
    if huber_delta <= 0:
        raise ValueError("huber_delta must be positive")
    gen_o, imp_o = ds.gen_obs.copy(), ds.imp_obs.copy()
    dem_o, tot_o = ds.dem_obs.copy(), ds.tot_obs.copy()
    sent_o, recv_o = ds.sent_obs.copy(), ds.recv_obs.copy()
    ann = ds.ann.copy()
    aux_ch = ds.aux_ch.copy().set_index("通道编号")
    if override:
        for (tab, key), val in override.items():
            if tab == "ann":
                ann.loc[key[0], key[1]] = val
            elif tab == "aux_ch":
                aux_ch.loc[key[0], key[1]] = val
            elif tab == "gen":
                gen_o[key[0], key[1]] = val
            elif tab == "dem":
                dem_o[key[0], key[1]] = val
            elif tab == "imp":
                imp_o[key[0]] = val
            elif tab == "flow_sent":
                sent_o[key[0]] = val
            elif tab == "flow_recv":
                recv_o[key[0]] = val

    return _solve_once(ds, gen_o, imp_o, dem_o, tot_o, sent_o, recv_o,
                       ann, aux_ch, method, huber_delta)


def _solve_once(ds, gen_o, imp_o, dem_o, tot_o, sent_o, recv_o,
                ann, aux_ch, method, huber_delta) -> ReconcileResult:
    gen = cp.Variable((96, 4), nonneg=True)
    imp = cp.Variable(96, nonneg=True)
    dem = cp.Variable((96, 4), nonneg=True)
    loss = cp.Variable(96, nonneg=True)
    sent = cp.Variable(132, nonneg=True)
    recv = cp.Variable(132, nonneg=True)

    data_terms, prior_terms = [], []
    data_residual_exprs, prior_residual_exprs = [], []
    n_obs = 0

    def data_term(standardized_residual):
        data_residual_exprs.append(standardized_residual)
        if method == "huber":
            data_terms.append(cp.sum(cp.huber(
                standardized_residual, M=huber_delta)))
        else:
            data_terms.append(cp.sum_squares(standardized_residual))

    def prior_term(standardized_residual):
        prior_residual_exprs.append(standardized_residual)
        prior_terms.append(cp.sum_squares(standardized_residual))

    # ---- 月度观测项(缺失掩码)----
    for arr_o, var, key in [(gen_o, gen, "gen"), (dem_o, dem, "dem")]:
        mask = ~np.isnan(arr_o)
        sig = _sigma(arr_o, key)
        data_term(cp.multiply(1 / sig[mask], var[mask] - arr_o[mask]))
        n_obs += int(mask.sum())
    m_imp = ~np.isnan(imp_o)
    data_term(cp.multiply(1 / _sigma(imp_o, "imp")[m_imp],
                          imp[m_imp] - imp_o[m_imp]))
    n_obs += int(m_imp.sum())
    m_tot = ~np.isnan(tot_o)
    tot_expr = cp.sum(dem, axis=1)
    data_term(cp.multiply(1 / _sigma(tot_o, "demtot")[m_tot],
                          tot_expr[m_tot] - tot_o[m_tot]))
    n_obs += int(m_tot.sum())
    data_term(cp.multiply(1 / _sigma(sent_o, "flow"), sent - sent_o))
    data_term(cp.multiply(1 / _sigma(recv_o, "flow"), recv - recv_o))
    n_obs += 2 * 132

    # ---- 年度观测项(附件2A / 2B)----
    reg_rows = {r: np.where(ds.row_region == r)[0] for r in REGIONS}
    for r in REGIONS:
        ks = reg_rows[r]
        for expr, acol in [(cp.sum(gen[ks]), "本地发电量"),
                           (cp.sum(imp[ks]), "省外输入电量"),
                           (cp.sum(tot_expr[ks]), "终端用电量"),
                           (cp.sum(dem[ks, 0]), "工业用电量")]:
            a = float(ann.loc[r, acol])
            data_term((expr - a) / _sigma(np.array([a]), "ann")[0])
            n_obs += 1
    for e in CHANNELS:
        js = ds.ch_rows[e]
        for expr, acol in [(cp.sum(sent[js]), "年度送端汇总"),
                           (cp.sum(recv[js]), "年度受端汇总")]:
            a = float(aux_ch.loc[e, acol])
            data_term((expr - a) / _sigma(np.array([a]), "ann_ch")[0])
            n_obs += 1

    # ---- 先验正则:年度聚合通道损耗、区内损耗 ----
    # 工程 eta 只锚定年度总送/受端关系。它不被更新后回灌，故目标始终固定。
    # 无正流量通道不提供 eta 信息，跳过该先验并在输出中保留工程值。
    for e, ei in zip(CHANNELS, range(11)):
        js = ds.ch_rows[e]
        annual_sent_ref = float(np.nansum(ds.sent_obs[js]))
        if annual_sent_ref <= 1.0:
            continue
        # 把月度关系误差聚合成年尺度：独立月误差按平方和传播，避免把
        # ``1%×年度电量`` 误当成年度标准差而使工程先验弱化约 sqrt(12) 倍。
        n_active = max(int((ds.sent_obs[js] > 1e-9).sum()), 1)
        sig_eta = max(ETA_PRIOR_REL * annual_sent_ref / np.sqrt(n_active),
                      ETA_PRIOR_FLOOR * np.sqrt(n_active))
        prior_term((cp.sum(recv[js])
                    - (1 - ds.eta_eng[ei]) * cp.sum(sent[js])) / sig_eta)
    loss_prior = LOSS_PRIOR_RATE * np.nan_to_num(tot_o)
    loss_prior[np.isnan(tot_o)] = LOSS_PRIOR_RATE * np.nanmean(tot_o)
    sig_l = np.maximum(LOSS_PRIOR_REL * loss_prior, 1.0)
    prior_term(cp.multiply(1 / sig_l, loss - loss_prior))

    # ---- 硬约束 ----
    cons = [recv <= sent, sent <= ds.cap,
            sent[ds.zero_flow] == 0, recv[ds.zero_flow] == 0]
    for k in range(96):
        r, m = ds.row_region[k], ds.row_month[k]
        fin = (cp.sum(recv[ds.in_rows[(r, m)]])
               if ds.in_rows[(r, m)] else 0)
        fout = (cp.sum(sent[ds.out_rows[(r, m)]])
                if ds.out_rows[(r, m)] else 0)
        cons.append(cp.sum(gen[k]) + imp[k] + fin
                    == cp.sum(dem[k]) + fout + loss[k])

    prob = cp.Problem(cp.Minimize(sum(data_terms + prior_terms)), cons)
    prob.solve(solver=cp.CLARABEL)
    if prob.status not in {"optimal", "optimal_inaccurate"}:
        raise RuntimeError(f"QP status: {prob.status}")

    sent_v, recv_v = sent.value, recv.value
    eta_hat = np.empty(11)
    eta_identifiable = np.zeros(11, dtype=bool)
    for ei, e in enumerate(CHANNELS):
        js = ds.ch_rows[e]
        s = sent_v[js].sum()
        eta_identifiable[ei] = float(np.nansum(ds.sent_obs[js])) > 1.0
        eta_hat[ei] = (1 - recv_v[js].sum() / s
                       if eta_identifiable[ei] and s > 1.0
                       else ds.eta_eng[ei])

    def residual_values(expressions):
        arrays = [np.asarray(expr.value, dtype=float).reshape(-1)
                  for expr in expressions]
        return np.concatenate(arrays) if arrays else np.empty(0)

    data_residuals = residual_values(data_residual_exprs)
    prior_residuals = residual_values(prior_residual_exprs)
    if len(data_residuals) != n_obs:
        raise RuntimeError(
            f"standardized residual count {len(data_residuals)} != n_obs {n_obs}")
    return ReconcileResult(gen.value, imp.value, dem.value, loss.value,
                           sent_v, recv_v, eta_hat, prob.value, n_obs,
                           eta_identifiable=eta_identifiable, method=method,
                           huber_delta=huber_delta,
                           n_prior=len(prior_residuals),
                           data_residuals=data_residuals,
                           prior_residuals=prior_residuals,
                           status=prob.status)


def adjustments_table(ds: Dataset, res: ReconcileResult) -> pd.DataFrame:
    """全部观测的标准化调整量 z=(x̂−x)/σ,按 |z| 排序。"""
    rows = []

    def add(table, loc, field, obs, hat, sig):
        if np.isnan(obs):
            return
        rows.append(dict(表=table, 位置=loc, 字段=field, 观测值=round(obs, 3),
                         校正值=round(float(hat), 3),
                         标准化调整=round(float((hat - obs) / sig), 3)))

    sg, si = _sigma(ds.gen_obs, "gen"), _sigma(ds.imp_obs, "imp")
    sd, st = _sigma(ds.dem_obs, "dem"), _sigma(ds.tot_obs, "demtot")
    ss, sr = _sigma(ds.sent_obs, "flow"), _sigma(ds.recv_obs, "flow")
    for k in range(96):
        loc = f"{ds.row_month[k]}/{ds.row_region[k]}"
        for s in range(4):
            add("1A", loc, GEN_COLS[s], ds.gen_obs[k, s], res.gen[k, s],
                sg[k, s])
            add("1A", loc, SECTORS[s], ds.dem_obs[k, s], res.dem[k, s],
                sd[k, s])
        add("1A", loc, IMP_COL, ds.imp_obs[k], res.imp[k], si[k])
        add("1A", loc, TOT_COL, ds.tot_obs[k], res.dem[k].sum(), st[k])
    for j in range(132):
        loc = f"{ds.mc.loc[j, '月份']}/{ds.mc.loc[j, '通道编号']}"
        add("1B", loc, "送端电量", ds.sent_obs[j], res.sent[j], ss[j])
        add("1B", loc, "受端电量", ds.recv_obs[j], res.recv[j], sr[j])
    reg_rows = {r: np.where(ds.row_region == r)[0] for r in REGIONS}
    for r in REGIONS:
        ks = reg_rows[r]
        hat = {"本地发电量": res.gen[ks].sum(), "省外输入电量": res.imp[ks].sum(),
               "终端用电量": res.dem[ks].sum(), "工业用电量": res.dem[ks, 0].sum()}
        for acol, h in hat.items():
            a = float(ds.ann.loc[r, acol])
            add("2A", r, acol, a, h, _sigma(np.array([a]), "ann")[0])
    aux = ds.aux_ch.set_index("通道编号")
    for e in CHANNELS:
        js = ds.ch_rows[e]
        for acol, h in [("年度送端汇总", res.sent[js].sum()),
                        ("年度受端汇总", res.recv[js].sum())]:
            a = float(aux.loc[e, acol])
            add("2B", e, acol, a, h, _sigma(np.array([a]), "ann_ch")[0])

    df = pd.DataFrame(rows)
    df = df.reindex(df["标准化调整"].abs().sort_values(ascending=False).index)
    df.to_csv(OUT / "q1_adjustments.csv", index=False, encoding="utf-8-sig")
    return df


def influence_analysis(ds: Dataset, base: ReconcileResult,
                       adj: pd.DataFrame) -> pd.DataFrame:
    """同一算法下做对称 ±5% 有限差分，并报告无量纲弹性。

    区域年度用电与通道线损的量纲、数值尺度差异很大，不能直接加权相加。
    因此先分别除以基准年度用电和工程线损率，再除以输入相对扰动幅度，
    最后用二范数组合两类弹性。
    """
    aux = ds.aux_ch.set_index("通道编号")
    cands: list[tuple[str, str, tuple, float]] = [
        ("2B", "E10/年度受端汇总", ("aux_ch", ("E10", "年度受端汇总")),
         float(aux.loc["E10", "年度受端汇总"])),
        ("2B", "E10/年度送端汇总", ("aux_ch", ("E10", "年度送端汇总")),
         float(aux.loc["E10", "年度送端汇总"])),
    ]
    seen = {c[1] for c in cands}
    for _, row in adj.head(30).iterrows():
        if len(cands) >= 8:
            break
        tab, loc, field = row["表"], row["位置"], row["字段"]
        name = f"{loc}/{field}"
        if name in seen or tab not in ("1A", "2A"):
            continue
        seen.add(name)
        if tab == "2A":
            obs = float(ds.ann.loc[loc, field])
            cands.append(("2A", name, ("ann", (loc, field)), obs))
        else:
            mth, reg = loc.split("/")
            k = int(np.where((ds.row_month == mth)
                             & (ds.row_region == reg))[0][0])
            if field in GEN_COLS:
                key = ("gen", (k, GEN_COLS.index(field)))
                obs = float(ds.gen_obs[key[1]])
            elif field in SECTORS:
                key = ("dem", (k, SECTORS.index(field)))
                obs = float(ds.dem_obs[key[1]])
            elif field == IMP_COL:
                key = ("imp", (k,))
                obs = float(ds.imp_obs[k])
            else:
                continue
            cands.append(("1A", name, key, obs))

    base_ann = _annual_demand(ds, base)
    rows = []
    for tab, name, key, obs in cands:
        if not np.isfinite(obs) or abs(obs) <= 1e-12:
            continue
        lower, upper = obs * (1 - INFLUENCE_REL_STEP), obs * (
            1 + INFLUENCE_REL_STEP)
        common = dict(method=base.method, huber_delta=base.huber_delta)
        low_res = reconcile(ds, override={key: lower}, **common)
        high_res = reconcile(ds, override={key: upper}, **common)

        low_ann = _annual_demand(ds, low_res)
        high_ann = _annual_demand(ds, high_res)
        demand_half_range = 0.5 * np.abs(high_ann - low_ann)
        eta_half_range = 0.5 * np.abs(high_res.eta_hat - low_res.eta_hat)
        demand_elasticity = float(np.max(
            demand_half_range / np.maximum(np.abs(base_ann), 1.0)
            / INFLUENCE_REL_STEP))
        # E07 无流量且 eta 不可识别；其固定工程值的零响应不参与最大值。
        eta_mask = base.eta_identifiable & (ds.eta_eng > 1e-12)
        eta_elasticity = float(np.max(
            eta_half_range[eta_mask] / ds.eta_eng[eta_mask]
            / INFLUENCE_REL_STEP))
        score = float(np.hypot(demand_elasticity, eta_elasticity))
        rows.append(dict(观测=name, 来源表=tab, 原值=round(obs, 2),
                         下扰动值=round(lower, 2), 上扰动值=round(upper, 2),
                         相对扰动=INFLUENCE_REL_STEP,
                         区域年度用电最大变化GWh=round(
                             float(demand_half_range.max()), 6),
                         线损率估计最大变化=round(
                             float(eta_half_range.max()), 8),
                         用电无量纲弹性=round(demand_elasticity, 8),
                         线损无量纲弹性=round(eta_elasticity, 8),
                         综合影响分数=round(score, 8),
                         方法=base.method.upper()))
    df = pd.DataFrame(rows).sort_values("综合影响分数", ascending=False)
    df.to_csv(OUT / "q1_influence.csv", index=False, encoding="utf-8-sig")
    return df


def _annual_demand(ds: Dataset, res: ReconcileResult) -> np.ndarray:
    """按 ``REGIONS`` 顺序返回调和后的区域年度终端用电。"""
    return np.array([
        res.dem[np.where(ds.row_region == region)[0]].sum()
        for region in REGIONS
    ])


def _relative_state_rmse(clean: ReconcileResult,
                         changed: ReconcileResult) -> float:
    """六类状态逐元素相对 clean 标准化后的整体 RMSE。"""
    terms = []
    for name in ("gen", "imp", "dem", "loss", "sent", "recv"):
        ref = np.asarray(getattr(clean, name), dtype=float)
        value = np.asarray(getattr(changed, name), dtype=float)
        terms.append(((value - ref) / np.maximum(np.abs(ref), 1.0)).ravel())
    delta = np.concatenate(terms)
    return float(np.sqrt(np.mean(delta ** 2)))


def method_comparison(ds: Dataset, huber: ReconcileResult,
                      wls: ReconcileResult) -> pd.DataFrame:
    """导出清洁数据上的 Huber/WLS 拟合与结果差异。"""
    base_ann = _annual_demand(ds, huber)
    rows = []
    for res in (huber, wls):
        ann = _annual_demand(ds, res)
        rows.append({
            "方法": res.method.upper(),
            "实际优化目标值": round(float(res.obj), 8),
            "Huber观测目标值": round(float(res.robust_data_objective), 8),
            "标准化观测平方和": round(float(res.standardized_data_rss), 8),
            "标准化先验平方和": round(float(res.standardized_prior_rss), 8),
            "描述性观测平方和/观测项": round(
                float(res.standardized_data_rss / res.n_obs), 8),
            "最大绝对标准化观测残差": round(
                float(np.max(np.abs(res.data_residuals))), 8),
            f"绝对标准化观测残差>{res.huber_delta:g}项数": int(
                (np.abs(res.data_residuals) > res.huber_delta).sum()),
            "相对Huber状态归一化RMSE": round(
                _relative_state_rmse(huber, res), 10),
            "相对Huber区域年度用电最大相对差": round(float(np.max(
                np.abs(ann - base_ann) / np.maximum(np.abs(base_ann), 1.0))),
                10),
            "相对Huber线损率最大绝对差": round(float(np.max(
                np.abs(res.eta_hat - huber.eta_hat))), 10),
            "求解状态": res.status,
        })
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "q1_method_comparison.csv", index=False,
              encoding="utf-8-sig")
    return df


def _contamination_cases(ds: Dataset) -> list[dict]:
    """六个预先固定的代表性粗差，不根据求解结果挑选。"""

    def region_row(month: str, region: str) -> int:
        matches = np.where((ds.row_month == month)
                           & (ds.row_region == region))[0]
        if len(matches) != 1:
            raise RuntimeError(f"cannot locate {month}/{region}")
        return int(matches[0])

    def channel_row(month: str, channel: str) -> int:
        matches = ds.mc.index[(ds.mc["月份"] == month)
                              & (ds.mc["通道编号"] == channel)].to_numpy()
        if len(matches) != 1:
            raise RuntimeError(f"cannot locate {month}/{channel}")
        return int(matches[0])

    k_a1 = region_row("2025-01", "A1")
    k_a4 = region_row("2025-11", "A4")
    k_a5 = region_row("2025-06", "A5")
    j_e10 = channel_row("2025-09", "E10")
    j_e03 = channel_row("2025-08", "E03")
    ann = ds.ann
    specs = [
        ("月度火电+20%", "1A", "2025-01/A1/火电发电量",
         ("gen", (k_a1, GEN_COLS.index("火电发电量"))),
         float(ds.gen_obs[k_a1, GEN_COLS.index("火电发电量")]), 1.20),
        ("月度省外输入+20%", "1A", "2025-11/A4/省外输入电量",
         ("imp", (k_a4,)), float(ds.imp_obs[k_a4]), 1.20),
        ("月度建筑服务用电-20%", "1A", "2025-06/A5/建筑服务用电",
         ("dem", (k_a5, SECTORS.index("建筑服务用电"))),
         float(ds.dem_obs[k_a5, SECTORS.index("建筑服务用电")]), 0.80),
        ("月度送端计量+20%", "1B", "2025-09/E10/送端计量电量",
         ("flow_sent", (j_e10,)), float(ds.sent_obs[j_e10]), 1.20),
        ("月度受端计量-20%", "1B", "2025-08/E03/受端计量电量",
         ("flow_recv", (j_e03,)), float(ds.recv_obs[j_e03]), 0.80),
        ("年度终端用电+15%", "2A", "A5/年度终端用电量",
         ("ann", ("A5", "终端用电量")),
         float(ann.loc["A5", "终端用电量"]), 1.15),
    ]
    return [dict(污染场景=label, 来源表=table, 观测=name, key=key,
                 原值=obs, 污染倍数=factor)
            for label, table, name, key, obs, factor in specs]


def contamination_experiment(ds: Dataset,
                             clean_results: dict[str, ReconcileResult]
                             ) -> pd.DataFrame:
    """固定粗差下比较 Huber 与 WLS 相对各自清洁基线的偏移。"""
    rows = []
    for case in _contamination_cases(ds):
        case_rows = []
        contaminated = case["原值"] * case["污染倍数"]
        for method in ("huber", "wls"):
            clean = clean_results[method]
            changed = reconcile(
                ds, override={case["key"]: contaminated}, method=method,
                huber_delta=clean.huber_delta)
            clean_ann = _annual_demand(ds, clean)
            changed_ann = _annual_demand(ds, changed)
            row = {
                "污染场景": case["污染场景"],
                "来源表": case["来源表"],
                "观测": case["观测"],
                "原值": round(float(case["原值"]), 6),
                "污染值": round(float(contaminated), 6),
                "相对污染幅度": round(float(case["污染倍数"] - 1), 4),
                "方法": method.upper(),
                "状态归一化RMSE": _relative_state_rmse(clean, changed),
                "区域年度用电最大相对变化": float(np.max(
                    np.abs(changed_ann - clean_ann)
                    / np.maximum(np.abs(clean_ann), 1.0))),
                "线损率最大绝对变化": float(np.max(
                    np.abs(changed.eta_hat - clean.eta_hat))),
            }
            rows.append(row)
            case_rows.append(row)
        rmse = {r["方法"]: r["状态归一化RMSE"] for r in case_rows}
        ratio = (rmse["WLS"] / rmse["HUBER"]
                 if rmse["HUBER"] > 1e-15 else np.nan)
        for row in case_rows:
            row["WLS相对Huber状态RMSE倍数"] = ratio

    df = pd.DataFrame(rows)
    numeric = ["状态归一化RMSE", "区域年度用电最大相对变化",
               "线损率最大绝对变化", "WLS相对Huber状态RMSE倍数"]
    df[numeric] = df[numeric].round(10)
    df.to_csv(OUT / "q1_robustness.csv", index=False, encoding="utf-8-sig")
    return df


def export(ds: Dataset, res: ReconcileResult, anomalies: pd.DataFrame,
           adj: pd.DataFrame, comparison: pd.DataFrame,
           robustness: pd.DataFrame) -> dict:
    rm = pd.DataFrame({"月份": ds.row_month, "区域": ds.row_region})
    for s, col in enumerate(GEN_COLS):
        rm[col] = res.gen[:, s]
    rm[IMP_COL] = res.imp
    for d, col in enumerate(SECTORS):
        rm[col] = res.dem[:, d]
    rm[TOT_COL] = res.dem.sum(axis=1)
    rm["区内损耗"] = res.loss
    rm.to_csv(OUT / "q1_reconciled_region_month.csv", index=False,
              encoding="utf-8-sig")

    cm = ds.mc[["月份", "通道编号", "送端区域", "受端区域"]].copy()
    cm["送端电量"] = res.sent
    cm["受端电量"] = res.recv
    cm.to_csv(OUT / "q1_reconciled_channel_month.csv", index=False,
              encoding="utf-8-sig")

    with np.errstate(divide="ignore", invalid="ignore"):
        s_by = np.array([ds.sent_obs[ds.ch_rows[e]].sum() for e in CHANNELS])
        r_by = np.array([ds.recv_obs[ds.ch_rows[e]].sum() for e in CHANNELS])
        raw_eta = np.where(s_by > 1, 1 - r_by / np.where(s_by > 0, s_by, np.nan),
                           np.nan)
    eta_df = pd.DataFrame({
        "通道": CHANNELS, "工程线损率": ds.eta_eng,
        "原始隐含损耗率": np.round(raw_eta, 5),
        "调和后估计": np.round(res.eta_hat, 5),
        "有效流量月份": [int((ds.sent_obs[ds.ch_rows[e]] > 1e-9).sum())
                         for e in CHANNELS],
        "线损可识别": res.eta_identifiable,
        "估计状态": np.where(res.eta_identifiable, "数据估计",
                              "无流量，采用工程值"),
    })
    eta_df.to_csv(OUT / "q1_eta.csv", index=False, encoding="utf-8-sig")

    comp = comparison.set_index("方法")
    robust_mean = robustness.groupby("方法")["状态归一化RMSE"].mean()
    robust_max_demand = robustness.groupby("方法")[
        "区域年度用电最大相对变化"].max()
    robust_max_eta = robustness.groupby("方法")["线损率最大绝对变化"].max()
    improvement = float(robust_mean["WLS"] / robust_mean["HUBER"])
    summary = {
        "方法": "守恒约束标准化Huber数据调和",
        "Huber阈值delta": res.huber_delta,
        "求解状态": res.status,
        "稳健目标值": round(float(res.obj), 6),
        "稳健观测目标值": round(float(res.robust_data_objective), 6),
        "标准化观测加权平方和": round(float(res.standardized_data_rss), 6),
        "标准化观测加权残差/观测项": round(
            float(res.standardized_data_rss / res.n_obs), 8),
        "标准化先验平方和": round(float(res.standardized_prior_rss), 6),
        "观测项数": res.n_obs,
        "先验残差项数": res.n_prior,
        "统计量口径说明": (
            "标准化观测平方和/观测项仅是描述性拟合指标；模型含先验、"
            "硬约束、相关观测与估计状态，不将其解释为标准约化卡方。"),
        "异常条目数": int(len(anomalies)),
        "|z|>2 的调整数": int((adj["标准化调整"].abs() > 2).sum()),
        "区内损耗率(全省)": round(float(res.loss.sum() / res.dem.sum()), 5),
        "缺失值校正插补": {
            f"{ds.row_month[k]}/{ds.row_region[k]}/{col}": round(float(v), 2)
            for k, col, v in _imputed(ds, res)
        },
        "eta": {e: round(float(v), 5)
                for e, v in zip(CHANNELS, res.eta_hat)},
        "eta可识别性": {
            e: ("数据可识别" if identifiable else "无流量，采用工程值")
            for e, identifiable in zip(CHANNELS, res.eta_identifiable)
        },
        "Huber-WLS清洁数据对照": {
            "Huber描述性观测平方和/项": round(float(
                comp.loc["HUBER", "描述性观测平方和/观测项"]), 8),
            "WLS描述性观测平方和/项": round(float(
                comp.loc["WLS", "描述性观测平方和/观测项"]), 8),
            "两法状态归一化RMSE": round(float(
                comp.loc["WLS", "相对Huber状态归一化RMSE"]), 10),
            "区域年度用电最大相对差": round(float(
                comp.loc["WLS", "相对Huber区域年度用电最大相对差"]), 10),
            "线损率最大绝对差": round(float(
                comp.loc["WLS", "相对Huber线损率最大绝对差"]), 10),
        },
        "确定性污染稳健性": {
            "污染场景数": int(robustness["污染场景"].nunique()),
            "Huber平均状态归一化RMSE": round(float(robust_mean["HUBER"]), 10),
            "WLS平均状态归一化RMSE": round(float(robust_mean["WLS"]), 10),
            "WLS相对Huber平均RMSE倍数": round(improvement, 6),
            "Huber区域年度用电最大相对变化": round(float(
                robust_max_demand["HUBER"]), 10),
            "WLS区域年度用电最大相对变化": round(float(
                robust_max_demand["WLS"]), 10),
            "Huber线损率最大绝对变化": round(float(
                robust_max_eta["HUBER"]), 10),
            "WLS线损率最大绝对变化": round(float(
                robust_max_eta["WLS"]), 10),
        },
    }
    with open(OUT / "q1_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary


def _imputed(ds: Dataset, res: ReconcileResult):
    out = []
    for k, s in np.argwhere(np.isnan(ds.gen_obs)):
        out.append((k, GEN_COLS[s], res.gen[k, s]))
    for k, d in np.argwhere(np.isnan(ds.dem_obs)):
        out.append((k, SECTORS[d], res.dem[k, d]))
    for k in np.where(np.isnan(ds.tot_obs))[0]:
        out.append((k, TOT_COL, res.dem[k].sum()))
    return out


def make_plots(ds: Dataset, res: ReconcileResult | None, adj: pd.DataFrame,
               infl: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from ..common.advanced_plots import (dumbbell, heatmap_with_marginals,
                                         lollipop_h, treemap)

    plot_setup()
    raw_res, raw_sig = _raw_balance_residual(ds)
    z = (raw_res / raw_sig).reshape(12, 8)
    fig = plt.figure(figsize=(7.2, 4.5))
    ax, _ = heatmap_with_marginals(
        fig, z, [m[-2:] for m in MONTHS], REGIONS,
        cbar_label=r"标准化残差 $z$（色标截断于 $\pm 6$）")
    ax.set_xlabel("月份(2025)")
    save_fig(fig, OUT / "fig_q1_raw_residual_heatmap.png")
    plt.close(fig)

    eta_df = pd.read_csv(OUT / "q1_eta.csv")
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    implied = pd.to_numeric(eta_df["原始隐含损耗率"], errors="coerce")
    dumbbell(ax, eta_df["通道"], eta_df["工程线损率"], eta_df["调和后估计"],
             "工程记录", "调和后估计", mid=implied, mid_label="原始数据隐含")
    identifiable = eta_df["线损可识别"].astype(bool)
    for ei, ok in enumerate(identifiable):
        if ok:
            continue
        ax.scatter(eta_df.loc[ei, "调和后估计"], ei, s=70, marker="x",
                   color="#7f4f00", zorder=4)
        ax.text(eta_df.loc[ei, "调和后估计"] + 0.0012, ei,
                "不可识别,工程值回填", va="center", fontsize=6.5)
    ax.set_xlabel("线损率")
    ax.set_xlim(0, 0.05)
    save_fig(fig, OUT / "fig_q1_eta_compare.png")
    plt.close(fig)

    top = adj.head(20).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    labels = top["表"] + " " + top["位置"] + " " + top["字段"]
    lollipop_h(ax, labels, top["标准化调整"], diverging=True)
    ax.set_xlabel(r"标准化调整 $z$（校正值与观测值之差 / $\sigma$）")
    save_fig(fig, OUT / "fig_q1_adjust_top20.png")
    plt.close(fig)

    ranked = infl.sort_values("综合影响分数", ascending=False)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    short = [str(s).replace("年度", "").replace("电量", "")
             for s in ranked["观测"]]
    cmap = plt.cm.YlOrRd
    n = len(ranked)
    colors = [cmap(0.35 + 0.6 * (n - 1 - i) / max(n - 1, 1)) for i in range(n)]
    treemap(ax, ranked["综合影响分数"].to_numpy(float), short, colors=colors)
    save_fig(fig, OUT / "fig_q1_influence.png")
    plt.close(fig)


def main() -> None:
    ds = Dataset()
    anomalies = detect_anomalies(ds)
    print(f"[Q1] 异常/不一致条目: {len(anomalies)}")
    res = reconcile(ds, method="huber")
    wls = reconcile(ds, method="wls")
    print(f"[Q1] Huber 凸调和最优, 稳健目标={res.obj:.3f}, "
          f"描述性观测平方和/项={res.standardized_data_rss / res.n_obs:.5f}")
    print(f"[Q1] WLS 对照最优, 目标={wls.obj:.3f}, "
          f"描述性观测平方和/项={wls.standardized_data_rss / wls.n_obs:.5f}")
    adj = adjustments_table(ds, res)
    infl = influence_analysis(ds, res, adj)
    comparison = method_comparison(ds, res, wls)
    robustness = contamination_experiment(ds, {"huber": res, "wls": wls})
    summary = export(ds, res, anomalies, adj, comparison, robustness)
    make_plots(ds, res, adj, infl)
    print("[Q1] 线损率估计:", summary["eta"])
    print("[Q1] 综合影响分数 Top3:\n", infl.head(3).to_string(index=False))
    robust_summary = summary["确定性污染稳健性"]
    print("[Q1] 污染试验 WLS/Huber 平均状态RMSE倍数:",
          robust_summary["WLS相对Huber平均RMSE倍数"])
    print(f"[Q1] 输出目录: {OUT}")


if __name__ == "__main__":
    main()
