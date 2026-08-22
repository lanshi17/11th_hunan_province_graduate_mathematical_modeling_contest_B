"""Q2 条件参数自举：把原始观测误差经 Q1 调和传播至碳流与 Q3。

这里估计的是在题设排放因子、网络拓扑和测量精度假设给定时的条件不确定性。
每个样本都从 Q1 拟合状态生成月度/年度伪观测，再完整重做约束调和；不在
调和结果上独立加噪，也不把附件 6 的 2028--2030 因子区间用于 2025。
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from ..common import data_io
from ..common.paths import CHANNELS, MONTHS, REGIONS, SECTORS, SOURCES, out_dir
from ..common.plotting import savefig as save_fig
from ..common.plotting import setup as plot_setup

Q1 = out_dir("q1")
Q2 = out_dir("q2")
Q3 = out_dir("q3")

GEN_COLS = [f"{s}发电量" for s in SOURCES]
IMP_COL = "省外输入电量"
TOT_COL = "终端用电合计"
DEFAULT_SAMPLES = 500
DEFAULT_SEED = 20250822
QUANTILES = (0.025, 0.5, 0.975)
ORIGIN_CLASSES = SOURCES + ["省外输入"]
CHANNEL_METRICS = ["到达碳流_kt", "通道线损碳_kt", "到达电量_GWh", "送端电量_GWh"]


def _fitted_result_from_q1(ds):
    """从 Q1 高精度 CSV 恢复拟合状态，避免为自举中心重复求解一次。"""
    rm = pd.read_csv(Q1 / "q1_reconciled_region_month.csv")
    cm = pd.read_csv(Q1 / "q1_reconciled_channel_month.csv")
    expected_rm = pd.MultiIndex.from_arrays(
        [ds.row_month, ds.row_region], names=["月份", "区域"])
    got_rm = pd.MultiIndex.from_frame(rm[["月份", "区域"]])
    if not expected_rm.equals(got_rm):
        raise ValueError("Q1 区域月表顺序与 Dataset 不一致，请先重跑 Q1")
    expected_cm = pd.MultiIndex.from_frame(ds.mc[["月份", "通道编号"]])
    got_cm = pd.MultiIndex.from_frame(cm[["月份", "通道编号"]])
    if not expected_cm.equals(got_cm):
        raise ValueError("Q1 通道月表顺序与 Dataset 不一致，请先重跑 Q1")
    eta = (pd.read_csv(Q1 / "q1_eta.csv").set_index("通道")
           .reindex(CHANNELS)["调和后估计"].to_numpy(float))
    return SimpleNamespace(
        gen=rm[GEN_COLS].to_numpy(float),
        imp=rm[IMP_COL].to_numpy(float),
        dem=rm[SECTORS].to_numpy(float),
        loss=rm["区内损耗"].to_numpy(float),
        sent=cm["送端电量"].to_numpy(float),
        recv=cm["受端电量"].to_numpy(float),
        eta_hat=eta,
    )


def _draw_observation(center: np.ndarray, sigma: np.ndarray,
                      observed_mask: np.ndarray, rng: np.random.Generator,
                      nonnegative: bool = True) -> np.ndarray:
    out = np.full(np.shape(center), np.nan, dtype=float)
    draw = np.asarray(center, dtype=float) + rng.normal(
        0.0, np.asarray(sigma, dtype=float), size=np.shape(center))
    if nonnegative:
        draw = np.maximum(draw, 0.0)
    out[observed_mask] = draw[observed_mask]
    return out


def _annual_centers(ds, fit) -> tuple[pd.DataFrame, pd.DataFrame]:
    ann = ds.ann.copy()
    for r in REGIONS:
        ks = np.where(ds.row_region == r)[0]
        ann.loc[r, "本地发电量"] = fit.gen[ks].sum()
        ann.loc[r, "省外输入电量"] = fit.imp[ks].sum()
        ann.loc[r, "终端用电量"] = fit.dem[ks].sum()
        ann.loc[r, "工业用电量"] = fit.dem[ks, 0].sum()
    aux = ds.aux_ch.copy().set_index("通道编号")
    for e in CHANNELS:
        js = ds.ch_rows[e]
        aux.loc[e, "年度送端汇总"] = fit.sent[js].sum()
        aux.loc[e, "年度受端汇总"] = fit.recv[js].sum()
    return ann, aux.reset_index()


def _sample_dataset(ds, fit, rng: np.random.Generator):
    """按 Q1 的测量精度生成一套完整伪观测，保留原始缺失模式。"""
    # 延迟导入可避免 q2.main -> uncertainty -> q2.main 的循环导入。
    from ..q1_reconcile.main import _sigma

    boot = copy.deepcopy(ds)
    boot.gen_obs = _draw_observation(
        fit.gen, _sigma(fit.gen, "gen"), ~np.isnan(ds.gen_obs), rng)
    boot.imp_obs = _draw_observation(
        fit.imp, _sigma(fit.imp, "imp"), ~np.isnan(ds.imp_obs), rng)
    boot.dem_obs = _draw_observation(
        fit.dem, _sigma(fit.dem, "dem"), ~np.isnan(ds.dem_obs), rng)
    total = fit.dem.sum(axis=1)
    boot.tot_obs = _draw_observation(
        total, _sigma(total, "demtot"), ~np.isnan(ds.tot_obs), rng)
    boot.sent_obs = _draw_observation(
        fit.sent, _sigma(fit.sent, "flow"), ~np.isnan(ds.sent_obs), rng)
    boot.recv_obs = _draw_observation(
        fit.recv, _sigma(fit.recv, "flow"), ~np.isnan(ds.recv_obs), rng)

    # 原数据中送、受端同时为零表示结构性停运，不把它随机变成一条新通道。
    boot.sent_obs[ds.zero_flow] = 0.0
    boot.recv_obs[ds.zero_flow] = 0.0
    boot.zero_flow = ds.zero_flow.copy()

    ann_center, aux_center = _annual_centers(ds, fit)
    boot.ann = ds.ann.copy()
    for col in ("本地发电量", "省外输入电量", "终端用电量", "工业用电量"):
        center = ann_center[col].to_numpy(float)
        boot.ann[col] = _draw_observation(
            center, _sigma(center, "ann"), np.ones(len(center), bool), rng)
    boot.aux_ch = ds.aux_ch.copy()
    aux_center = aux_center.set_index("通道编号")
    aux_boot = boot.aux_ch.set_index("通道编号")
    for col in ("年度送端汇总", "年度受端汇总"):
        center = aux_center.loc[CHANNELS, col].to_numpy(float)
        aux_boot.loc[CHANNELS, col] = _draw_observation(
            center, _sigma(center, "ann_ch"), np.ones(len(center), bool), rng)
    boot.aux_ch = aux_boot.reset_index()

    # 同步 DataFrame 视图，兼容 Q1 中可能基于原表读取观测的诊断代码。
    boot.mr = ds.mr.copy()
    boot.mr[GEN_COLS] = boot.gen_obs
    boot.mr[IMP_COL] = boot.imp_obs
    boot.mr[SECTORS] = boot.dem_obs
    boot.mr[TOT_COL] = boot.tot_obs
    boot.mc = ds.mc.copy()
    boot.mc["送端计量电量"] = boot.sent_obs
    boot.mc["受端计量电量"] = boot.recv_obs
    return boot


def _frames_from_result(ds, fit) -> tuple[pd.DataFrame, pd.DataFrame]:
    rm = pd.DataFrame({"月份": ds.row_month, "区域": ds.row_region})
    for j, col in enumerate(GEN_COLS):
        rm[col] = fit.gen[:, j]
    rm[IMP_COL] = fit.imp
    for j, col in enumerate(SECTORS):
        rm[col] = fit.dem[:, j]
    rm[TOT_COL] = fit.dem.sum(axis=1)
    rm["区内损耗"] = fit.loss

    cm = ds.mc[["月份", "通道编号", "送端区域", "受端区域"]].copy()
    cm["送端电量"] = fit.sent
    cm["受端电量"] = fit.recv
    return rm, cm


def _annual_rho(rm: pd.DataFrame, rho_monthly: np.ndarray) -> np.ndarray:
    demand = _demand_matrix(rm)
    return (rho_monthly * demand).sum(axis=0) / demand.sum(axis=0)


def _demand_matrix(rm: pd.DataFrame) -> np.ndarray:
    demand = np.zeros((len(MONTHS), len(REGIONS)))
    for t, month in enumerate(MONTHS):
        demand[t] = (rm[rm["月份"] == month].set_index("区域")[TOT_COL]
                     .reindex(REGIONS).to_numpy(float))
    return demand


def _annual_mix(rm: pd.DataFrame, mix_monthly: np.ndarray) -> np.ndarray:
    demand = _demand_matrix(rm)
    weights = demand / demand.sum(axis=0, keepdims=True)
    return np.einsum("tio,ti->io", mix_monthly, weights)


def _channel_direction_keys(cm: pd.DataFrame) -> list[tuple[str, str, str]]:
    return sorted({(str(row["通道编号"]), str(row["送端区域"]),
                    str(row["受端区域"])) for _, row in cm.iterrows()})


def _channel_carbon_metrics(
        cm: pd.DataFrame, rho_monthly: np.ndarray,
        keys: list[tuple[str, str, str]]) -> np.ndarray:
    """年度通道方向指标：[到达碳流, 线损碳, 到达电量, 送端电量]。"""
    key_index = {key: k for k, key in enumerate(keys)}
    region_index = {region: i for i, region in enumerate(REGIONS)}
    month_index = {month: t for t, month in enumerate(MONTHS)}
    out = np.zeros((len(keys), 4))
    for _, row in cm.iterrows():
        key = (str(row["通道编号"]), str(row["送端区域"]),
               str(row["受端区域"]))
        k = key_index[key]
        t = month_index[str(row["月份"])]
        j = region_index[str(row["送端区域"])]
        sent = float(row["送端电量"])
        recv = float(row["受端电量"])
        rho_sender = float(rho_monthly[t, j])
        out[k, 0] += recv * rho_sender
        out[k, 1] += max(0.0, sent - recv) * rho_sender
        out[k, 2] += recv
        out[k, 3] += sent
    return out


def _sample_diagnostics(ds, fit, rm: pd.DataFrame, cm: pd.DataFrame,
                        rho: np.ndarray, mix: np.ndarray) -> dict:
    balance_max = 0.0
    for k in range(len(ds.row_region)):
        region, month = ds.row_region[k], ds.row_month[k]
        fin = fit.recv[ds.in_rows[(region, month)]].sum()
        fout = fit.sent[ds.out_rows[(region, month)]].sum()
        residual = (fit.gen[k].sum() + fit.imp[k] + fin
                    - fit.dem[k].sum() - fout - fit.loss[k])
        balance_max = max(balance_max, abs(float(residual)))

    min_q = float("inf")
    max_condition = 0.0
    region_index = {r: i for i, r in enumerate(REGIONS)}
    for month in MONTHS:
        g = (rm[rm["月份"] == month].set_index("区域")
             .reindex(REGIONS))
        inflow = np.zeros((8, 8))
        for _, row in cm[cm["月份"] == month].iterrows():
            i = region_index[row["受端区域"]]
            j = region_index[row["送端区域"]]
            inflow[i, j] += float(row["受端电量"])
        q = (g[GEN_COLS].to_numpy(float).sum(axis=1)
             + g[IMP_COL].to_numpy(float) + inflow.sum(axis=1))
        min_q = min(min_q, float(q.min()))
        max_condition = max(max_condition,
                            float(np.linalg.cond(np.diag(q) - inflow)))
    return {
        "最大区域月能量平衡残差_GWh": balance_max,
        "最小节点总入流Q_GWh": min_q,
        "碳流线性系统最大条件数": max_condition,
        "来源份额行和最大偏差": float(np.max(np.abs(mix.sum(axis=2) - 1.0))),
        "碳势全部有限": bool(np.isfinite(rho).all()),
        "调和通道非负损耗最小值_GWh": float(np.min(fit.sent - fit.recv)),
    }


def _wilson_interval(successes: np.ndarray | int, n: int,
                     z: float = 1.959963984540054) -> tuple[np.ndarray, np.ndarray]:
    successes = np.asarray(successes, dtype=float)
    p = successes / n
    denom = 1.0 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    lower = np.maximum(0.0, center - half)
    upper = np.minimum(1.0, center + half)
    lower = np.where(np.isclose(lower, 0.0, atol=1e-15), 0.0, lower)
    upper = np.where(np.isclose(upper, 1.0, atol=1e-15), 1.0, upper)
    return lower, upper


def _point_arrays(rm: pd.DataFrame, cm: pd.DataFrame,
                  ef_local: dict, ef_ext: dict):
    from .main import responsibility, run_tracing

    rho, mix, _ = run_tracing(rm, cm, ef_local, ef_ext, "sender")
    resp = responsibility(rm, cm, ef_local, ef_ext, rho)
    channel_keys = _channel_direction_keys(cm)
    return (rho, _annual_rho(rm, rho), resp, _annual_mix(rm, mix),
            channel_keys, _channel_carbon_metrics(cm, rho, channel_keys))


def _quantile(values: np.ndarray) -> np.ndarray:
    return np.quantile(values, QUANTILES, axis=0)


def _rank_statistics(rho_annual: np.ndarray) -> pd.DataFrame:
    n = len(rho_annual)
    highest = np.argmax(rho_annual, axis=1)
    lowest = np.argmin(rho_annual, axis=1)
    order = np.argsort(-rho_annual, axis=1)
    ranks = np.empty_like(order)
    ranks[np.arange(n)[:, None], order] = np.arange(1, len(REGIONS) + 1)
    high_count = np.array([(highest == i).sum() for i in range(8)])
    low_count = np.array([(lowest == i).sum() for i in range(8)])
    top3_count = np.array([(ranks[:, i] <= 3).sum() for i in range(8)])
    high_lo, high_hi = _wilson_interval(high_count, n)
    low_lo, low_hi = _wilson_interval(low_count, n)
    top3_lo, top3_hi = _wilson_interval(top3_count, n)
    return pd.DataFrame({
        "区域": REGIONS,
        "成为最高碳强度概率": high_count / n,
        "最高概率Wilson95%下界": high_lo,
        "最高概率Wilson95%上界": high_hi,
        "成为最低碳强度概率": low_count / n,
        "最低概率Wilson95%下界": low_lo,
        "最低概率Wilson95%上界": low_hi,
        "进入高碳前三概率": top3_count / n,
        "前三概率Wilson95%下界": top3_lo,
        "前三概率Wilson95%上界": top3_hi,
        "平均秩_1为最高": ranks.mean(axis=0),
        "秩P2.5": np.quantile(ranks, 0.025, axis=0),
        "秩P97.5": np.quantile(ranks, 0.975, axis=0),
    })


def _batch_endpoint_mcse(values: np.ndarray) -> float:
    """用不重叠批次估计分位点端点的最大 Monte Carlo 标准误。"""
    n = len(values)
    batches = min(10, n // 20)
    if batches < 2:
        return float("nan")
    usable = (n // batches) * batches
    estimates = [_quantile(x) for x in np.array_split(values[:usable], batches)]
    return float(np.std(estimates, axis=0, ddof=1).max() / np.sqrt(batches))


def _convergence_table(rho_annual: np.ndarray) -> pd.DataFrame:
    n = len(rho_annual)
    candidates = [25, 50, 100, 150, 200, 300, 500, max(10, n // 2), n]
    checkpoints = sorted({min(n, k) for k in candidates if min(n, k) >= 10})
    final_q = _quantile(rho_annual)
    final_rank = _rank_statistics(rho_annual).set_index("区域")
    rows = []
    for k in checkpoints:
        q = _quantile(rho_annual[:k])
        rank = _rank_statistics(rho_annual[:k]).set_index("区域")
        rank_cols = ["成为最高碳强度概率", "成为最低碳强度概率"]
        rows.append({
            "样本数": k,
            "分位端点相对最终最大差_kg每kWh": float(np.max(np.abs(q - final_q))),
            "排序概率相对最终最大差": float(
                np.max(np.abs(rank[rank_cols].to_numpy()
                              - final_rank[rank_cols].to_numpy()))),
            "平均95%区间宽度_kg每kWh": float(np.mean(q[2] - q[0])),
            "批次法分位端点最大MCSE_kg每kWh": _batch_endpoint_mcse(
                rho_annual[:k]),
        })
    return pd.DataFrame(rows)


def _export_intervals(
        point_monthly: np.ndarray, point_annual: np.ndarray,
        point_resp: pd.DataFrame, point_mix: np.ndarray,
        channel_keys: list[tuple[str, str, str]], point_channel: np.ndarray,
        rho_monthly: np.ndarray, rho_annual: np.ndarray,
        resp_draws: np.ndarray, mix_draws: np.ndarray,
        channel_draws: np.ndarray, resp_cols: list[str]
        ) -> dict[str, pd.DataFrame]:
    q_month = _quantile(rho_monthly)
    monthly_rows = []
    for t, month in enumerate(MONTHS):
        for i, region in enumerate(REGIONS):
            monthly_rows.append({
                "月份": month, "区域": region,
                "点估计": point_monthly[t, i],
                "P2.5": q_month[0, t, i], "P50": q_month[1, t, i],
                "P97.5": q_month[2, t, i],
                "95%区间宽度": q_month[2, t, i] - q_month[0, t, i],
            })
    monthly = pd.DataFrame(monthly_rows)
    monthly.to_csv(Q2 / "q2_rho_monthly_interval.csv", index=False,
                   encoding="utf-8-sig")

    q_ann = _quantile(rho_annual)
    annual = pd.DataFrame({
        "区域": REGIONS, "点估计": point_annual,
        "P2.5": q_ann[0], "P50": q_ann[1], "P97.5": q_ann[2],
        "95%区间宽度": q_ann[2] - q_ann[0],
        "P50相对点估计偏差": q_ann[1] - point_annual,
    })
    annual.to_csv(Q2 / "q2_rho_annual_interval.csv", index=False,
                  encoding="utf-8-sig")

    q_resp = _quantile(resp_draws)
    resp_rows = []
    point_by_region = point_resp.set_index("区域")
    for i, region in enumerate(REGIONS):
        for j, metric in enumerate(resp_cols):
            resp_rows.append({
                "区域": region, "指标": metric,
                "点估计_kt": float(point_by_region.loc[region, metric]),
                "P2.5_kt": q_resp[0, i, j], "P50_kt": q_resp[1, i, j],
                "P97.5_kt": q_resp[2, i, j],
            })
    resp_interval = pd.DataFrame(resp_rows)
    resp_interval.to_csv(Q2 / "q2_responsibility_interval.csv", index=False,
                         encoding="utf-8-sig")

    q_mix = _quantile(mix_draws)
    mix_rows = []
    for i, region in enumerate(REGIONS):
        for j, source in enumerate(ORIGIN_CLASSES):
            mix_rows.append({
                "区域": region, "来源": source, "点估计份额": point_mix[i, j],
                "P2.5": q_mix[0, i, j], "P50": q_mix[1, i, j],
                "P97.5": q_mix[2, i, j],
            })
    mix_interval = pd.DataFrame(mix_rows)
    mix_interval.to_csv(Q2 / "q2_origin_mix_interval.csv", index=False,
                        encoding="utf-8-sig")

    q_channel = _quantile(channel_draws)
    channel_rows = []
    for k, (channel, sender, receiver) in enumerate(channel_keys):
        row = {"通道": channel, "送端": sender, "受端": receiver}
        for j, metric in enumerate(CHANNEL_METRICS):
            row[f"{metric}_点估计"] = point_channel[k, j]
            row[f"{metric}_P2.5"] = q_channel[0, k, j]
            row[f"{metric}_P50"] = q_channel[1, k, j]
            row[f"{metric}_P97.5"] = q_channel[2, k, j]
        channel_rows.append(row)
    channel_interval = pd.DataFrame(channel_rows).sort_values(
        "到达碳流_kt_点估计", ascending=False)
    channel_interval.to_csv(Q2 / "q2_channel_carbon_interval.csv", index=False,
                            encoding="utf-8-sig")
    return {"monthly": monthly, "annual": annual,
            "responsibility": resp_interval, "mix": mix_interval,
            "channel": channel_interval}


def _plot_uncertainty(annual: pd.DataFrame, convergence: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    plot_setup()
    from ..common.advanced_plots import level_deviation_forest

    annual = annual.set_index("区域").reindex(REGIONS).reset_index()
    fig = plt.figure(figsize=(7.4, 3.8))
    level_deviation_forest(
        fig, annual["区域"], annual["点估计"], annual["P50"],
        annual["P2.5"], annual["P97.5"],
        level_label=r"点估计 kgCO$_2$/kWh",
        dev_label=r"相对点估计 (kgCO$_2$/kWh)",
        level_fmt=".3f", mid_label=r"P50 相对点估计",
        point_label="点估计（零线）")
    save_fig(fig, Q2 / "fig_q2_uncertainty.png")
    plt.close(fig)


def _plot_channel_uncertainty(channel: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    plot_setup()
    from ..common.advanced_plots import level_deviation_forest

    top = channel.nlargest(10, "到达碳流_kt_点估计").copy()
    labels = top["通道"] + " " + top["送端"] + r"$\to$" + top["受端"]
    fig = plt.figure(figsize=(7.4, 4.8))
    level_deviation_forest(
        fig, labels, top["到达碳流_kt_点估计"], top["到达碳流_kt_P50"],
        top["到达碳流_kt_P2.5"], top["到达碳流_kt_P97.5"],
        level_label=r"点估计 ktCO$_2$",
        dev_label=r"相对点估计 (ktCO$_2$)",
        level_fmt=".0f", mid_label=r"P50 相对点估计",
        point_label="点估计（零线）")
    save_fig(fig, Q2 / "fig_q2_channel_carbon_uncertainty.png")
    plt.close(fig)


def run_conditional_bootstrap(rm_point: pd.DataFrame, cm_point: pd.DataFrame,
                              ef_local: dict, ef_ext: dict,
                              n_samples: int = DEFAULT_SAMPLES,
                              seed: int = DEFAULT_SEED) -> dict:
    """运行测量层条件参数自举并写出区间、排序和收敛诊断。"""
    if n_samples < 40:
        raise ValueError("条件自举至少需要 40 个成功样本")
    from cvxpy.error import SolverError
    from ..q1_reconcile.main import Dataset, reconcile
    from .main import responsibility, run_tracing

    ds = Dataset()
    fitted = _fitted_result_from_q1(ds)
    rng = np.random.default_rng(seed)
    (point_monthly, point_annual, point_resp, point_mix,
     channel_keys, point_channel) = _point_arrays(
         rm_point, cm_point, ef_local, ef_ext)
    resp_cols = [
        "生产责任(本地发电)", "省外输入碳", "扩展生产责任P+",
        "消费责任(终端)", "区内损耗碳", "通道损耗碳(送端)",
        "消费责任全口径C+", "共担责任(λ=0.5)",
    ]
    rho_monthly_draws: list[np.ndarray] = []
    rho_annual_draws: list[np.ndarray] = []
    resp_values: list[np.ndarray] = []
    mix_values: list[np.ndarray] = []
    channel_values: list[np.ndarray] = []
    diagnostic_rows: list[dict] = []
    conservation_errors: list[float] = []
    failures: list[dict] = []
    attempts = 0
    max_attempts = n_samples + max(10, n_samples // 10)
    while len(rho_annual_draws) < n_samples and attempts < max_attempts:
        attempts += 1
        try:
            boot = _sample_dataset(ds, fitted, rng)
            fit = reconcile(boot)
            rm, cm = _frames_from_result(boot, fit)
            rho, mix, _ = run_tracing(rm, cm, ef_local, ef_ext, "sender")
            resp = responsibility(rm, cm, ef_local, ef_ext, rho)
            arr = resp.set_index("区域").reindex(REGIONS)[resp_cols].to_numpy(float)
            p_total = float(resp["扩展生产责任P+"].sum())
            c_total = float(resp["消费责任全口径C+"].sum())
            conservation = abs(p_total - c_total) / max(abs(p_total), 1e-12)
            diagnostics = _sample_diagnostics(ds, fit, rm, cm, rho, mix)
            diagnostics["责任守恒相对误差"] = conservation
            if (not diagnostics["碳势全部有限"]
                    or diagnostics["最小节点总入流Q_GWh"] <= 0
                    or not np.isfinite(diagnostics["碳流线性系统最大条件数"])
                    or diagnostics["来源份额行和最大偏差"] > 1e-7
                    or diagnostics["最大区域月能量平衡残差_GWh"] > 1e-6
                    or diagnostics["调和通道非负损耗最小值_GWh"] < -1e-7
                    or conservation > 1e-8):
                raise FloatingPointError(f"自举样本数值诊断未通过: {diagnostics}")
            conservation_errors.append(conservation)
            rho_monthly_draws.append(rho)
            rho_annual_draws.append(_annual_rho(rm, rho))
            resp_values.append(arr)
            mix_values.append(_annual_mix(rm, mix))
            channel_values.append(_channel_carbon_metrics(
                cm, rho, channel_keys))
            diagnostic_rows.append({"样本": len(rho_annual_draws), **diagnostics})
        except (SolverError, np.linalg.LinAlgError, RuntimeError,
                FloatingPointError) as exc:
            failures.append({"尝试序号": attempts,
                             "异常类型": type(exc).__name__,
                             "异常信息": str(exc)[:300]})
        if attempts % 25 == 0 or len(rho_annual_draws) == n_samples:
            print(f"[Q2-bootstrap] {len(rho_annual_draws)}/{n_samples} "
                  f"successful ({attempts} attempts)", flush=True)
    if len(rho_annual_draws) < n_samples:
        pd.DataFrame(failures, columns=["尝试序号", "异常类型", "异常信息"]).to_csv(
            Q2 / "q2_bootstrap_failures.csv", index=False,
            encoding="utf-8-sig")
        raise RuntimeError(
            f"条件自举仅成功 {len(rho_annual_draws)}/{n_samples} 次；"
            f"失败记录见 {Q2 / 'q2_bootstrap_failures.csv'}")

    rho_monthly_arr = np.asarray(rho_monthly_draws)
    rho_annual_arr = np.asarray(rho_annual_draws)
    resp_arr = np.asarray(resp_values)
    mix_arr = np.asarray(mix_values)
    channel_arr = np.asarray(channel_values)
    intervals = _export_intervals(
        point_monthly, point_annual, point_resp, point_mix,
        channel_keys, point_channel, rho_monthly_arr, rho_annual_arr,
        resp_arr, mix_arr, channel_arr, resp_cols)

    rank = _rank_statistics(rho_annual_arr)
    rank.to_csv(Q2 / "q2_rank_probability.csv", index=False,
                encoding="utf-8-sig")
    convergence = _convergence_table(rho_annual_arr)
    convergence.to_csv(Q2 / "q2_bootstrap_convergence.csv", index=False,
                       encoding="utf-8-sig")

    draw_rows = []
    for b in range(n_samples):
        for i, region in enumerate(REGIONS):
            draw_rows.append({
                "样本": b + 1, "区域": region,
                "年度终端碳强度": rho_annual_arr[b, i],
                "扩展生产责任P+_kt": resp_arr[b, i, resp_cols.index(
                    "扩展生产责任P+")],
                "消费责任全口径C+_kt": resp_arr[b, i, resp_cols.index(
                    "消费责任全口径C+")],
            })
    pd.DataFrame(draw_rows).to_csv(
        Q2 / "q2_bootstrap_rho_annual_draws.csv", index=False,
        encoding="utf-8-sig")

    mix_draw_rows = []
    for b in range(n_samples):
        for i, region in enumerate(REGIONS):
            mix_draw_rows.append({
                "样本": b + 1, "区域": region,
                **{source: mix_arr[b, i, j]
                   for j, source in enumerate(ORIGIN_CLASSES)},
            })
    pd.DataFrame(mix_draw_rows).to_csv(
        Q2 / "q2_bootstrap_origin_mix_draws.csv", index=False,
        encoding="utf-8-sig")

    channel_draw_rows = []
    for b in range(n_samples):
        for k, (channel, sender, receiver) in enumerate(channel_keys):
            channel_draw_rows.append({
                "样本": b + 1, "通道": channel, "送端": sender,
                "受端": receiver,
                **{metric: channel_arr[b, k, j]
                   for j, metric in enumerate(CHANNEL_METRICS)},
            })
    pd.DataFrame(channel_draw_rows).to_csv(
        Q2 / "q2_bootstrap_channel_draws.csv", index=False,
        encoding="utf-8-sig")
    diagnostics_df = pd.DataFrame(diagnostic_rows)
    diagnostics_df.to_csv(Q2 / "q2_bootstrap_diagnostics.csv", index=False,
                          encoding="utf-8-sig")
    pd.DataFrame(failures, columns=["尝试序号", "异常类型", "异常信息"]).to_csv(
        Q2 / "q2_bootstrap_failures.csv", index=False, encoding="utf-8-sig")

    half = convergence[convergence["样本数"] >= n_samples // 2].iloc[0]
    final = convergence.iloc[-1]
    final_mcse = float(final["批次法分位端点最大MCSE_kg每kWh"])
    summary = {
        "method": "conditional parametric bootstrap through full Q1 reconciliation",
        "seed": seed,
        "requested_samples": n_samples,
        "successful_samples": len(rho_annual_arr),
        "attempts": attempts,
        "failed_attempts": len(failures),
        "observation_generation_assumption": (
            "conditionally independent Gaussian measurement errors, truncated "
            "at zero, with the original missingness and structural-zero pattern"
        ),
        "fixed_inputs": ["2025 emission factors", "network topology",
                         "engineering-loss prior", "measurement precision model"],
        "not_used_as_2025_distribution": "Attachment 6 future factor intervals",
        "maximum_carbon_conservation_relative_error": float(
            max(conservation_errors, default=0.0)),
        "maximum_energy_balance_residual_GWh": float(
            diagnostics_df["最大区域月能量平衡残差_GWh"].max()),
        "minimum_node_total_inflow_Q_GWh": float(
            diagnostics_df["最小节点总入流Q_GWh"].min()),
        "maximum_carbon_system_condition_number": float(
            diagnostics_df["碳流线性系统最大条件数"].max()),
        "maximum_origin_share_row_sum_error": float(
            diagnostics_df["来源份额行和最大偏差"].max()),
        "maximum_annual_median_shift_vs_point_kg_per_kWh": float(
            np.max(np.abs(np.quantile(rho_annual_arr, 0.5, axis=0)
                          - point_annual))),
        "half_sample_quantile_endpoint_change_vs_final_kg_per_kWh": float(
            half["分位端点相对最终最大差_kg每kWh"]),
        "final_batch_quantile_endpoint_max_mcse_kg_per_kWh": (
            final_mcse if np.isfinite(final_mcse) else None),
        "highest_region_probabilities": dict(zip(
            REGIONS, rank["成为最高碳强度概率"].astype(float))),
        "lowest_region_probabilities": dict(zip(
            REGIONS, rank["成为最低碳强度概率"].astype(float))),
        "interpretation": (
            "intervals are conditional measurement-uncertainty intervals, "
            "not unconditional forecasts or confidence guarantees"
        ),
    }
    with open(Q2 / "q2_bootstrap_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, allow_nan=False)
    _plot_uncertainty(intervals["annual"], convergence)
    _plot_channel_uncertainty(intervals["channel"])
    return summary


def propagate_q3_cap_risk(q3_dir: Path | None = None) -> pd.DataFrame | None:
    """把 Q2 年度碳强度样本传播到 Q3 推荐固定方案的年度省级碳上限。

    此处不对每个样本重新优化，因此回答的是“推荐方案若按原计划执行”的
    条件达标风险；它不会把事后再优化带来的适应性收益算进去。
    """
    q3_dir = Path(q3_dir) if q3_dir is not None else Q3
    draws_path = Q2 / "q2_bootstrap_rho_annual_draws.csv"
    plan_path = q3_dir / "q3_epsilon_recommended_regional.csv"
    if not draws_path.exists() or not plan_path.exists():
        return None
    if plan_path.stat().st_mtime_ns < draws_path.stat().st_mtime_ns:
        raise RuntimeError(
            "Q3 推荐方案早于本次 Q2 自举样本；请先重跑 Q3，避免传播旧方案")
    draws = pd.read_csv(draws_path)
    plan = pd.read_csv(plan_path)
    rho_point = (pd.read_csv(Q2 / "q2_rho_annual.csv").set_index("区域")
                 ["2025终端碳强度"].reindex(REGIONS))
    constraints = data_io.load_annual_constraints().set_index("年份")
    kappa = constraints["基准供电碳强度调整系数(相对2025)"].to_dict()
    caps = constraints["消费侧碳排放上限(ktCO2)"].to_dict()
    pivot = draws.pivot(index="样本", columns="区域",
                        values="年度终端碳强度").reindex(columns=REGIONS)
    years = sorted(plan["年份"].astype(int).unique())
    emissions = np.zeros((len(pivot), len(years)))
    reconstructed_point = np.zeros(len(years))
    for yi, year in enumerate(years):
        for _, row in plan[plan["年份"] == year].iterrows():
            region = row["区域"]
            if {"碳强度作用电量_GWh", "与碳强度无关排放项_kt"}.issubset(
                    plan.columns):
                exposure = float(row["碳强度作用电量_GWh"])
                fixed_component = float(row["与碳强度无关排放项_kt"])
            else:
                net = float(row["净需求_GWh"])
                clean = float(row["光伏供电_GWh"])
                point_emission = float(row["消费碳_kt"])
                exposure = net - clean
                # 兼容旧 Q3 输出：由点估计排放反推固定项。新输出直接给出
                # 未舍入的作用电量和固定项，最终验收走上面的精确分支。
                fixed_component = point_emission - (
                    float(rho_point[region]) * kappa[year] * exposure)
            emissions[:, yi] += (pivot[region].to_numpy(float) * kappa[year]
                                  * exposure + fixed_component)
            reconstructed_point[yi] += (
                float(rho_point[region]) * kappa[year] * exposure
                + fixed_component)
    rows = []
    for yi, year in enumerate(years):
        vals = emissions[:, yi]
        cap = float(caps[year])
        excess = np.maximum(vals - cap, 0.0)
        exceed_count = int((vals > cap).sum())
        prob_lo, prob_hi = _wilson_interval(exceed_count, len(vals))
        plan_point_col = ("消费碳_精确kt" if "消费碳_精确kt" in plan.columns
                          else "消费碳_kt")
        exported_point = float(
            plan.loc[plan["年份"] == year, plan_point_col].sum())
        rows.append({
            "年份": year, "碳上限_kt": cap,
            "方案点估计排放_kt": reconstructed_point[yi],
            "点估计重构误差_kt": reconstructed_point[yi] - exported_point,
            "排放P2.5_kt": np.quantile(vals, 0.025),
            "排放P50_kt": np.quantile(vals, 0.5),
            "排放P97.5_kt": np.quantile(vals, 0.975),
            "条件超限概率": exceed_count / len(vals),
            "超限概率Wilson95%下界": float(prob_lo),
            "超限概率Wilson95%上界": float(prob_hi),
            "期望超限量_kt": np.mean(excess),
            "最差5%平均超限量_kt": (np.mean(np.sort(excess)[-max(1, len(excess)//20):])),
        })
    result = pd.DataFrame(rows)
    if result["点估计重构误差_kt"].abs().max() > 1e-5 \
            and "消费碳_精确kt" in plan.columns:
        raise AssertionError("Q2→Q3 点估计排放重构未通过精度校验")
    result.to_csv(Q2 / "q2_q3_cap_risk.csv", index=False,
                  encoding="utf-8-sig")

    try:
        with open(Q2 / "q2_bootstrap_summary.json", encoding="utf-8") as f:
            summary = json.load(f)
    except FileNotFoundError:
        summary = {}
    summary["q3_fixed_recommended_plan_cap_risk"] = {
        str(int(row["年份"])): float(row["条件超限概率"])
        for _, row in result.iterrows()
    }
    with open(Q2 / "q2_bootstrap_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    _plot_q3_cap_risk(result)
    return result


def _plot_q3_cap_risk(risk: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    plot_setup()
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    x = risk["年份"].to_numpy(int)
    med = risk["排放P50_kt"].to_numpy(float)
    lo = risk["排放P2.5_kt"].to_numpy(float)
    hi = risk["排放P97.5_kt"].to_numpy(float)
    ax.fill_between(x, lo, hi, alpha=0.25, color="#1f77b4",
                    label="条件 95% 区间")
    ax.plot(x, med, "o-", color="#1f77b4", label="条件 P50")
    ax.plot(x, risk["碳上限_kt"], "s--", color="#d62728", label="年度碳上限")
    for _, row in risk.iterrows():
        ax.annotate(f"{100 * row['条件超限概率']:.1f}\\%",
                    (row["年份"], row["排放P97.5_kt"]),
                    xytext=(0, 5), textcoords="offset points", ha="center",
                    fontsize=8)
    ax.set_xticks(x)
    ax.set_ylabel(r"消费侧碳排放 (ktCO$_2$)")
    ax.legend(fontsize=8)
    save_fig(fig, Q2 / "fig_q2_q3_cap_risk.png")
    plt.close(fig)
