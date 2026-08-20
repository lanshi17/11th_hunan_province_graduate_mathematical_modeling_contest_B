"""问题一:多源能源数据一致性校正与可信性评价。

方法:守恒约束下的加权最小二乘数据调和(Crowe 1996; Narasimhan & Jordache
1999),即面向能量平衡的广义 WLS 状态估计(Schweppe 1970; Abur 2004)。
异常识别用标准化残差;通道损耗率由调和后送/受端电量估计,并与工程值
迭代一致;观测影响度用 KKT 灵敏度的数值近似(留一扰动重解)。

平衡口径:入流按受端计量(过网损耗已扣),出流按送端计量,通道损耗
"落在线上";区内输配损耗 L_{i,t} 为非负自由变量,先验 5% × 终端用电。
"""
from __future__ import annotations

import json

import cvxpy as cp
import numpy as np
import pandas as pd

from ..common import data_io
from ..common.paths import CHANNELS, MONTHS, REGIONS, SECTORS, SOURCES, out_dir
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
    def __init__(self, gen, imp, dem, loss, sent, recv, eta_hat, obj, n_obs):
        self.gen, self.imp, self.dem, self.loss = gen, imp, dem, loss
        self.sent, self.recv = sent, recv
        self.eta_hat, self.obj, self.n_obs = eta_hat, obj, n_obs


def reconcile(ds: Dataset, override: dict | None = None,
              n_iter: int = 2) -> ReconcileResult:
    """WLS 数据调和。override: {(table, key): new_obs} 用于影响度扰动。"""
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

    eta = ds.eta_eng.copy()
    result = None
    for _ in range(n_iter):
        result = _solve_once(ds, gen_o, imp_o, dem_o, tot_o, sent_o, recv_o,
                             ann, aux_ch, eta)
        eta = result.eta_hat
    return result


def _solve_once(ds, gen_o, imp_o, dem_o, tot_o, sent_o, recv_o,
                ann, aux_ch, eta) -> ReconcileResult:
    gen = cp.Variable((96, 4), nonneg=True)
    imp = cp.Variable(96, nonneg=True)
    dem = cp.Variable((96, 4), nonneg=True)
    loss = cp.Variable(96, nonneg=True)
    sent = cp.Variable(132, nonneg=True)
    recv = cp.Variable(132, nonneg=True)

    terms, n_obs = [], 0

    def sq(expr_minus_obs_over_sigma):
        terms.append(cp.sum_squares(expr_minus_obs_over_sigma))

    # ---- 月度观测项(缺失掩码)----
    for arr_o, var, key in [(gen_o, gen, "gen"), (dem_o, dem, "dem")]:
        mask = ~np.isnan(arr_o)
        sig = _sigma(arr_o, key)
        sq(cp.multiply(1 / sig[mask], var[mask] - arr_o[mask]))
        n_obs += int(mask.sum())
    m_imp = ~np.isnan(imp_o)
    sq(cp.multiply(1 / _sigma(imp_o, "imp")[m_imp], imp[m_imp] - imp_o[m_imp]))
    n_obs += int(m_imp.sum())
    m_tot = ~np.isnan(tot_o)
    tot_expr = cp.sum(dem, axis=1)
    sq(cp.multiply(1 / _sigma(tot_o, "demtot")[m_tot],
                   tot_expr[m_tot] - tot_o[m_tot]))
    n_obs += int(m_tot.sum())
    sq(cp.multiply(1 / _sigma(sent_o, "flow"), sent - sent_o))
    sq(cp.multiply(1 / _sigma(recv_o, "flow"), recv - recv_o))
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
            sq((expr - a) / _sigma(np.array([a]), "ann")[0])
            n_obs += 1
    for e in CHANNELS:
        js = ds.ch_rows[e]
        for expr, acol in [(cp.sum(sent[js]), "年度送端汇总"),
                           (cp.sum(recv[js]), "年度受端汇总")]:
            a = float(aux_ch.loc[e, acol])
            sq((expr - a) / _sigma(np.array([a]), "ann_ch")[0])
            n_obs += 1

    # ---- 先验正则:通道损耗、区内损耗 ----
    for e, ei in zip(CHANNELS, range(11)):
        js = ds.ch_rows[e]
        sig = np.maximum(ETA_PRIOR_REL * np.nan_to_num(sent_o[js]),
                         ETA_PRIOR_FLOOR)
        terms.append(cp.sum_squares(
            cp.multiply(1 / sig, recv[js] - (1 - eta[ei]) * sent[js])))
    loss_prior = LOSS_PRIOR_RATE * np.nan_to_num(tot_o)
    loss_prior[np.isnan(tot_o)] = LOSS_PRIOR_RATE * np.nanmean(tot_o)
    sig_l = np.maximum(LOSS_PRIOR_REL * loss_prior, 1.0)
    terms.append(cp.sum_squares(cp.multiply(1 / sig_l, loss - loss_prior)))

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

    prob = cp.Problem(cp.Minimize(cp.sum(terms)), cons)
    prob.solve(solver=cp.CLARABEL)
    if prob.status != "optimal":
        raise RuntimeError(f"QP status: {prob.status}")

    sent_v, recv_v = sent.value, recv.value
    eta_hat = np.empty(11)
    for ei, e in enumerate(CHANNELS):
        js = ds.ch_rows[e]
        s = sent_v[js].sum()
        eta_hat[ei] = 1 - recv_v[js].sum() / s if s > 1.0 else ds.eta_eng[ei]
    return ReconcileResult(gen.value, imp.value, dem.value, loss.value,
                           sent_v, recv_v, eta_hat, prob.value, n_obs)


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
    """对高调整观测做 +5% 留一扰动重解,量化其对校正结果的传播影响。"""
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
            cands.append(("2A", name, ("ann", (loc, field)), row["观测值"]))
        else:
            mth, reg = loc.split("/")
            k = int(np.where((ds.row_month == mth)
                             & (ds.row_region == reg))[0][0])
            if field in GEN_COLS:
                key = ("gen", (k, GEN_COLS.index(field)))
            elif field in SECTORS:
                key = ("dem", (k, SECTORS.index(field)))
            elif field == IMP_COL:
                key = ("imp", (k,))
            else:
                continue
            cands.append(("1A", name, key, row["观测值"]))

    base_ann = {r: base.dem[np.where(ds.row_region == r)[0]].sum()
                for r in REGIONS}
    rows = []
    for tab, name, key, obs in cands:
        pert = obs * 1.05 if abs(obs) > 1 else obs + 10.0
        res = reconcile(ds, override={key: pert}, n_iter=1)
        d_ann = max(abs(res.dem[np.where(ds.row_region == r)[0]].sum()
                        - base_ann[r]) for r in REGIONS)
        d_eta = float(np.max(np.abs(res.eta_hat - base.eta_hat)))
        rows.append(dict(观测=name, 来源表=tab, 原值=round(obs, 2),
                         扰动值=round(pert, 2),
                         区域年度用电最大变化GWh=round(d_ann, 3),
                         线损率估计最大变化=round(d_eta, 5),
                         影响度=round(d_ann + 1e4 * d_eta, 3)))
    df = pd.DataFrame(rows).sort_values("影响度", ascending=False)
    df.to_csv(OUT / "q1_influence.csv", index=False, encoding="utf-8-sig")
    return df


def export(ds: Dataset, res: ReconcileResult, anomalies: pd.DataFrame,
           adj: pd.DataFrame) -> dict:
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
    })
    eta_df.to_csv(OUT / "q1_eta.csv", index=False, encoding="utf-8-sig")

    chi2 = float(res.obj)
    summary = {
        "目标函数(加权平方和)": round(chi2, 2),
        "观测项数": res.n_obs,
        "chi2/n_obs": round(chi2 / res.n_obs, 4),
        "异常条目数": int(len(anomalies)),
        "|z|>2 的调整数": int((adj["标准化调整"].abs() > 2).sum()),
        "区内损耗率(全省)": round(float(res.loss.sum() / res.dem.sum()), 5),
        "缺失值校正插补": {
            f"{ds.row_month[k]}/{ds.row_region[k]}/{col}": round(float(v), 2)
            for k, col, v in _imputed(ds, res)
        },
        "eta": {e: round(float(v), 5)
                for e, v in zip(CHANNELS, res.eta_hat)},
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


def make_plots(ds: Dataset, res: ReconcileResult, adj: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    plot_setup()
    # 图1:原始平衡残差热力图(标准化)
    raw_res, raw_sig = _raw_balance_residual(ds)
    z = (raw_res / raw_sig).reshape(12, 8)  # 月主序
    fig, ax = plt.subplots(figsize=(7, 4.2))
    im = ax.imshow(z.T, cmap="RdBu_r", vmin=-6, vmax=6, aspect="auto")
    ax.set_xticks(range(12), [m[-2:] for m in MONTHS])
    ax.set_yticks(range(8), REGIONS)
    ax.set_xlabel("月份(2025)")
    ax.set_title("校正前区域能量平衡标准化残差 z")
    fig.colorbar(im, ax=ax, shrink=0.85)
    fig.savefig(OUT / "fig_q1_raw_residual_heatmap.png")
    plt.close(fig)

    # 图2:线损率对比
    eta_df = pd.read_csv(OUT / "q1_eta.csv")
    x = np.arange(11)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.bar(x - 0.27, eta_df["工程线损率"], 0.27, label="工程记录")
    ax.bar(x, eta_df["原始隐含损耗率"], 0.27, label="原始数据隐含")
    ax.bar(x + 0.27, eta_df["调和后估计"], 0.27, label="调和后估计")
    ax.set_xticks(x, CHANNELS)
    ax.set_ylabel("线损率")
    ax.set_title("通道线损率:工程值 vs 隐含值 vs 调和估计")
    ax.legend()
    fig.savefig(OUT / "fig_q1_eta_compare.png")
    plt.close(fig)

    # 图3:标准化调整 Top20
    top = adj.head(20).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 5.2))
    labels = top["表"] + " " + top["位置"] + " " + top["字段"]
    ax.barh(labels, top["标准化调整"],
            color=np.where(top["标准化调整"] > 0, "#d62728", "#1f77b4"))
    ax.set_xlabel(r"标准化调整 $z$（校正值与观测值之差 / $\sigma$）")
    ax.set_title("校正幅度最大的 20 个观测")
    fig.savefig(OUT / "fig_q1_adjust_top20.png")
    plt.close(fig)


def main() -> None:
    ds = Dataset()
    anomalies = detect_anomalies(ds)
    print(f"[Q1] 异常/不一致条目: {len(anomalies)}")
    res = reconcile(ds)
    print(f"[Q1] QP 最优, χ²={res.obj:.1f}, 观测项={res.n_obs}, "
          f"χ²/n={res.obj / res.n_obs:.3f}")
    adj = adjustments_table(ds, res)
    infl = influence_analysis(ds, res, adj)
    summary = export(ds, res, anomalies, adj)
    make_plots(ds, res, adj)
    print("[Q1] 线损率估计:", summary["eta"])
    print("[Q1] 影响度Top3:\n", infl.head(3).to_string(index=False))
    print(f"[Q1] 输出目录: {OUT}")


if __name__ == "__main__":
    main()
