"""核验 Q1--Q5 与深化分析产物的结构和跨文件数值一致性。

只验证模型不变量、回算公式和必需 schema，不把一次运行的浮点快照当作
金标准；各输出目录允许存在额外的合法图表和中间产物。

用法：``uv run python -m src.verify_outputs``
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Sequence

import numpy as np
import pandas as pd

from .common import data_io
from .common.paths import (CHANNELS, MONTHS, OUT_DIR, PLAN_YEARS, REGIONS,
                           SECTORS, SOURCES)


RESULTS: list[tuple[str, str, bool, str]] = []
ATOL = 1e-8


def check(section: str, claim: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((section, claim, bool(ok), detail))


def read_json(relative: str) -> dict:
    with open(OUT_DIR / relative, encoding="utf-8") as file:
        return json.load(file)


def read_csv(relative: str) -> pd.DataFrame:
    return pd.read_csv(OUT_DIR / relative)


def require_columns(section: str, name: str, frame: pd.DataFrame,
                    columns: Iterable[str]) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    check(section, f"{name} 必需字段", not missing,
          "" if not missing else f"缺少 {missing}")
    if missing:
        raise KeyError(f"{name} 缺少字段 {missing}")


def finite(frame: pd.DataFrame, columns: Sequence[str]) -> bool:
    values = frame[list(columns)].apply(pd.to_numeric, errors="coerce")
    return bool(np.isfinite(values.to_numpy(float)).all())


def bool_values(series: pd.Series) -> np.ndarray:
    if pd.api.types.is_bool_dtype(series):
        return series.to_numpy(bool)
    mapped = series.astype(str).str.strip().str.lower().map({
        "true": True, "false": False, "1": True, "0": False,
    })
    if mapped.isna().any():
        raise ValueError(f"无法解析布尔列：{series[mapped.isna()].unique()}")
    return mapped.to_numpy(bool)


def close(a: float, b: float, atol: float = ATOL,
          rtol: float = 1e-8) -> bool:
    return bool(np.isclose(float(a), float(b), atol=atol, rtol=rtol))


def max_abs_difference(a, b) -> float:
    aa, bb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if aa.shape != bb.shape:
        return float("inf")
    return float(np.max(np.abs(aa - bb))) if aa.size else 0.0


def quantile_order(frame: pd.DataFrame,
                   triples: Sequence[tuple[str, str, str]],
                   tol: float = 1e-12) -> tuple[bool, float]:
    ok, worst = True, 0.0
    for lo_col, mid_col, hi_col in triples:
        lo = frame[lo_col].to_numpy(float)
        mid = frame[mid_col].to_numpy(float)
        hi = frame[hi_col].to_numpy(float)
        worst = max(worst, float(np.max(lo - mid)), float(np.max(mid - hi)))
        ok &= bool((lo <= mid + tol).all() and (mid <= hi + tol).all())
    return ok, max(0.0, worst)


def wilson_interval(successes: np.ndarray | int, n: int,
                    z: float = 1.959963984540054) -> tuple[np.ndarray, np.ndarray]:
    successes = np.asarray(successes, dtype=float)
    probability = successes / n
    denominator = 1.0 + z ** 2 / n
    center = (probability + z ** 2 / (2 * n)) / denominator
    half = z * np.sqrt(probability * (1 - probability) / n
                       + z ** 2 / (4 * n ** 2)) / denominator
    lower = np.maximum(0.0, center - half)
    upper = np.minimum(1.0, center + half)
    lower = np.where(np.isclose(lower, 0.0, atol=1e-15), 0.0, lower)
    upper = np.where(np.isclose(upper, 1.0, atol=1e-15), 1.0, upper)
    return lower, upper


def nested_mismatches(actual, expected, path: str = "root",
                      atol: float = 1e-8) -> list[str]:
    errors: list[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: 类型 {type(actual).__name__} != dict"]
        if set(actual) != set(expected):
            errors.append(
                f"{path}: keys 缺少{sorted(set(expected) - set(actual))} "
                f"多出{sorted(set(actual) - set(expected))}")
        for key in set(actual) & set(expected):
            errors.extend(nested_mismatches(
                actual[key], expected[key], f"{path}.{key}", atol))
        return errors
    if isinstance(expected, (list, tuple)):
        if not isinstance(actual, (list, tuple)) or len(actual) != len(expected):
            return [f"{path}: 序列长度/类型不一致"]
        for index, (aa, ee) in enumerate(zip(actual, expected)):
            errors.extend(nested_mismatches(aa, ee, f"{path}[{index}]", atol))
        return errors
    if isinstance(expected, (bool, np.bool_)):
        if bool(actual) != bool(expected):
            errors.append(f"{path}: {actual!r} != {expected!r}")
        return errors
    if isinstance(expected, (int, float, np.number)):
        try:
            actual_float, expected_float = float(actual), float(expected)
            same = ((np.isnan(actual_float) and np.isnan(expected_float))
                    or np.isclose(actual_float, expected_float,
                                  atol=atol, rtol=1e-8))
        except (TypeError, ValueError):
            same = False
        if not same:
            errors.append(f"{path}: {actual!r} != {expected!r}")
        return errors
    if actual != expected:
        errors.append(f"{path}: {actual!r} != {expected!r}")
    return errors


REQUIRED_FILES: dict[str, set[str]] = {
    "q1": {
        "q1_summary.json", "q1_anomalies.csv", "q1_eta.csv",
        "q1_influence.csv", "q1_method_comparison.csv", "q1_robustness.csv",
        "q1_reconciled_channel_month.csv", "q1_reconciled_region_month.csv",
    },
    "q2": {
        "q2_summary.json", "q2_bootstrap_summary.json", "q2_rho_annual.csv",
        "q2_rho_monthly.csv", "q2_responsibility.csv",
        "q2_origin_mix_annual.csv", "q2_rho_annual_interval.csv",
        "q2_rho_monthly_interval.csv", "q2_responsibility_interval.csv",
        "q2_origin_mix_interval.csv", "q2_channel_carbon_interval.csv",
        "q2_rank_probability.csv", "q2_bootstrap_rho_annual_draws.csv",
        "q2_bootstrap_origin_mix_draws.csv", "q2_bootstrap_channel_draws.csv",
        "q2_bootstrap_diagnostics.csv", "q2_bootstrap_convergence.csv",
        "q2_bootstrap_failures.csv", "q2_q3_cap_risk.csv",
    },
    "q3": {
        "q3_summary.json", "q3_regional.csv", "q3_yearly.csv",
        "q3_schedule.csv", "q3_epsilon_summary.json", "q3_epsilon_pareto.csv",
        "q3_epsilon_validation.csv", "q3_epsilon_recommended_regional.csv",
        "q3_epsilon_recommended_schedule.csv",
        "q3_epsilon_recommended_yearly.csv",
    },
    "q4": {
        "q4_summary.json", "q4_por_curve.csv", "q4_stress.csv",
        "q4_hard_feasibility_trace.csv", "q4_hard_gap_by_year.csv",
        "q4_hard_restoration.csv", "q4_regret_summary.json",
        "q4_regret_paths.csv", "q4_regret_schedule.csv", "q4_rolling.csv",
        "q4_ccg_log.csv",
    },
    "q5": {"q5_key_numbers.json", "q5_report_draft.md"},
    "deepen": {
        "deepen_summary.json", "q1_param_sensitivity.csv",
        "q2_responsibility_shapley.csv", "q3_baselines.csv",
        "q4_gamma_sensitivity.csv", "q4_three_schemes.csv",
    },
}


def verify_files() -> None:
    for module, required in REQUIRED_FILES.items():
        directory = OUT_DIR / module
        present = ({path.name for path in directory.iterdir() if path.is_file()}
                   if directory.is_dir() else set())
        missing = sorted(required - present)
        check("文件", f"{module} 必需产物子集存在", not missing,
              "" if not missing else f"缺失 {missing}")


def verify_q1() -> None:
    rm = read_csv("q1/q1_reconciled_region_month.csv")
    cm = read_csv("q1/q1_reconciled_channel_month.csv")
    eta = read_csv("q1/q1_eta.csv")
    comparison = read_csv("q1/q1_method_comparison.csv")
    robustness = read_csv("q1/q1_robustness.csv")
    summary = read_json("q1/q1_summary.json")

    region_numeric = [f"{source}发电量" for source in SOURCES] + [
        "省外输入电量", *SECTORS, "终端用电合计", "区内损耗"]
    require_columns("Q1", "区域月调和表", rm, ["月份", "区域", *region_numeric])
    require_columns("Q1", "通道月调和表", cm, [
        "月份", "通道编号", "送端区域", "受端区域", "送端电量", "受端电量"])
    require_columns("Q1", "eta 表", eta, [
        "通道", "工程线损率", "调和后估计", "有效流量月份", "线损可识别", "估计状态"])

    expected_rm = {(month, region) for month in MONTHS for region in REGIONS}
    actual_rm = list(zip(rm["月份"], rm["区域"]))
    check("Q1", "区域月键完整且唯一",
          len(actual_rm) == len(expected_rm) and set(actual_rm) == expected_rm,
          f"行数={len(actual_rm)}, 唯一键={len(set(actual_rm))}")
    expected_cm = {(month, channel) for month in MONTHS for channel in CHANNELS}
    actual_cm = list(zip(cm["月份"], cm["通道编号"]))
    check("Q1", "通道月键完整且唯一",
          len(actual_cm) == len(expected_cm) and set(actual_cm) == expected_cm,
          f"行数={len(actual_cm)}, 唯一键={len(set(actual_cm))}")

    rm_min = float(rm[region_numeric].min().min())
    cm_min = float(cm[["送端电量", "受端电量"]].min().min())
    check("Q1", "调和变量非负且有限",
          finite(rm, region_numeric) and finite(cm, ["送端电量", "受端电量"])
          and rm_min >= -ATOL and cm_min >= -ATOL,
          f"区域最小={rm_min:.3e}, 通道最小={cm_min:.3e}")
    sector_error = max_abs_difference(
        rm["终端用电合计"], rm[list(SECTORS)].sum(axis=1))
    check("Q1", "终端合计等于四部门之和", sector_error <= 1e-7,
          f"最大误差={sector_error:.3e} GWh")

    inflow = (cm.groupby(["月份", "受端区域"], as_index=False)["受端电量"]
              .sum().rename(columns={"受端区域": "区域", "受端电量": "流入"}))
    outflow = (cm.groupby(["月份", "送端区域"], as_index=False)["送端电量"]
               .sum().rename(columns={"送端区域": "区域", "送端电量": "流出"}))
    audit = (rm.merge(inflow, on=["月份", "区域"], how="left")
             .merge(outflow, on=["月份", "区域"], how="left"))
    audit[["流入", "流出"]] = audit[["流入", "流出"]].fillna(0.0)
    balance = (audit[[f"{source}发电量" for source in SOURCES]].sum(axis=1)
               + audit["省外输入电量"] + audit["流入"]
               - audit["终端用电合计"] - audit["流出"] - audit["区内损耗"])
    balance_max = float(balance.abs().max())
    check("Q1", "逐区域逐月能量守恒", balance_max <= 1e-6,
          f"最大残差={balance_max:.3e} GWh")

    raw = data_io.load_monthly_channel()[[
        "月份", "通道编号", "送端区域", "受端区域", "送端计量电量",
        "受端计量电量", "通道月度容量上限"]]
    joined = cm.merge(raw, on=["月份", "通道编号"], validate="one_to_one",
                      suffixes=("", "_原始"))
    endpoint_ok = bool(
        (joined["送端区域"] == joined["送端区域_原始"]).all()
        and (joined["受端区域"] == joined["受端区域_原始"]).all())
    check("Q1", "调和通道方向与附件逐月一致", endpoint_ok)
    cap_excess = float((joined["送端电量"] - joined["通道月度容量上限"]).max())
    loss_min = float((joined["送端电量"] - joined["受端电量"]).min())
    check("Q1", "送端容量上限与非负通道损耗均满足",
          cap_excess <= 1e-6 and loss_min >= -1e-7,
          f"最大超容量={max(0.0, cap_excess):.3e}, 最小损耗={loss_min:.3e} GWh")
    zero_mask = ((joined["送端计量电量"] <= 1e-9)
                 & (joined["受端计量电量"] <= 1e-9))
    zero_values = joined.loc[zero_mask, ["送端电量", "受端电量"]].abs().to_numpy()
    zero_max = float(zero_values.max()) if zero_values.size else 0.0
    check("Q1", "结构性零流量保持为零", zero_max <= 1e-7,
          f"最大绝对流量={zero_max:.3e} GWh")

    eta = eta.set_index("通道").reindex(CHANNELS)
    identifiable = bool_values(eta["线损可识别"])
    raw_identifiable = (raw.groupby("通道编号")["送端计量电量"].sum()
                        .reindex(CHANNELS).to_numpy(float) > 1.0)
    check("Q1", "线损可识别性由有效流量决定",
          np.array_equal(identifiable, raw_identifiable),
          f"不可识别={list(np.asarray(CHANNELS)[~identifiable])}")
    engineering_error = max_abs_difference(
        eta.loc[~identifiable, "调和后估计"],
        eta.loc[~identifiable, "工程线损率"])
    e07_flow = float(joined.loc[joined["通道编号"] == "E07",
                                  ["送端电量", "受端电量"]].abs().max().max())
    e07_ok = (not identifiable[CHANNELS.index("E07")]
              and int(eta.loc["E07", "有效流量月份"]) == 0
              and close(eta.loc["E07", "调和后估计"],
                        eta.loc["E07", "工程线损率"], atol=5e-6)
              and "工程值" in str(eta.loc["E07", "估计状态"])
              and e07_flow <= 1e-7)
    check("Q1", "E07 不可识别并回填工程值", e07_ok,
          f"eta={eta.loc['E07', '调和后估计']}, 流量最大={e07_flow:.3e}")
    check("Q1", "所有不可识别通道均采用工程值", engineering_error <= 5e-6,
          f"最大误差={engineering_error:.3e}")

    summary_eta = summary.get("eta", {})
    eta_summary_error = max(abs(float(summary_eta.get(channel, np.nan))
                                - float(eta.loc[channel, "调和后估计"]))
                            for channel in CHANNELS)
    ident_summary = summary.get("eta可识别性", {})
    ident_summary_ok = all(
        ("工程值" in str(ident_summary.get(channel, ""))) == (not identifiable[index])
        for index, channel in enumerate(CHANNELS))
    check("Q1", "summary 的 eta 与可识别性和 CSV 一致",
          eta_summary_error <= 5e-6 and ident_summary_ok,
          f"eta最大误差={eta_summary_error:.3e}")

    require_columns("Q1", "Huber/WLS 对照", comparison,
                    ["方法", "求解状态", "描述性观测平方和/观测项"])
    require_columns("Q1", "污染稳健性表", robustness,
                    ["污染场景", "方法", "状态归一化RMSE"])
    methods_ok = (set(comparison["方法"]) == {"HUBER", "WLS"}
                  and comparison["求解状态"].astype(str).str.startswith("optimal").all())
    paired = robustness.groupby("污染场景")["方法"].agg(set)
    robust_mean = robustness.groupby("方法")["状态归一化RMSE"].mean()
    robust_ratio = float(robust_mean["WLS"] / robust_mean["HUBER"])
    claimed_ratio = float(summary["确定性污染稳健性"]["WLS相对Huber平均RMSE倍数"])
    check("Q1", "Huber/WLS 对照与成对污染实验完整",
          methods_ok and bool((paired == {"HUBER", "WLS"}).all())
          and np.isfinite(robustness["状态归一化RMSE"]).all(),
          f"污染场景数={len(paired)}")
    check("Q1", "污染实验均值比由逐场景结果回算",
          close(robust_ratio, claimed_ratio, atol=1e-6) and robust_ratio > 1.0,
          f"回算={robust_ratio:.6f}, summary={claimed_ratio:.6f}")
    obsolete = [key for key in summary if "χ" in key or "chi" in key.lower()]
    wording = str(summary.get("统计量口径说明", ""))
    check("Q1", "描述性拟合指标未冒充约化卡方",
          not obsolete and "不将其解释" in wording, f"旧字段={obsolete}")


def panel_check(section: str, label: str, frame: pd.DataFrame,
                sample_count: int, key_columns: Sequence[str],
                expected_keys: set[tuple]) -> None:
    samples = set(pd.to_numeric(frame["样本"]).astype(int))
    counts = frame.groupby("样本").size()
    keys = set(map(tuple, frame[list(key_columns)].drop_duplicates()
                   .itertuples(index=False, name=None)))
    ok = (samples == set(range(1, sample_count + 1))
          and not frame.duplicated(["样本", *key_columns]).any()
          and bool((counts == len(expected_keys)).all())
          and keys == expected_keys
          and len(frame) == sample_count * len(expected_keys))
    check(section, f"{label} 样本面板完整", ok,
          f"行数={len(frame)}, 样本={len(samples)}, 每样本键数范围="
          f"[{counts.min() if len(counts) else 0},{counts.max() if len(counts) else 0}]")


def compare_group_quantiles(interval: pd.DataFrame, draws: pd.DataFrame,
                            keys: Sequence[str], specs: Sequence[
                                tuple[str, str, str, str]]) -> float:
    worst = 0.0
    for draw_col, lo_col, mid_col, hi_col in specs:
        grouped = (draws.groupby(list(keys), sort=False)[draw_col]
                   .quantile([0.025, 0.5, 0.975]).unstack())
        grouped.columns = ["_lo", "_mid", "_hi"]
        merged = interval.merge(grouped.reset_index(), on=list(keys),
                                how="outer", validate="one_to_one", indicator=True)
        if not (merged["_merge"] == "both").all():
            return float("inf")
        for actual, expected in ((lo_col, "_lo"), (mid_col, "_mid"),
                                 (hi_col, "_hi")):
            worst = max(worst, max_abs_difference(merged[actual], merged[expected]))
    return worst


def verify_q2() -> None:
    summary = read_json("q2/q2_summary.json")
    boot = read_json("q2/q2_bootstrap_summary.json")
    rho = read_csv("q2/q2_rho_annual.csv")
    responsibility = read_csv("q2/q2_responsibility.csv")
    mix = read_csv("q2/q2_origin_mix_annual.csv")
    annual_interval = read_csv("q2/q2_rho_annual_interval.csv")
    monthly_interval = read_csv("q2/q2_rho_monthly_interval.csv")
    responsibility_interval = read_csv("q2/q2_responsibility_interval.csv")
    mix_interval = read_csv("q2/q2_origin_mix_interval.csv")
    channel_interval = read_csv("q2/q2_channel_carbon_interval.csv")
    rank = read_csv("q2/q2_rank_probability.csv")
    rho_draws = read_csv("q2/q2_bootstrap_rho_annual_draws.csv")
    mix_draws = read_csv("q2/q2_bootstrap_origin_mix_draws.csv")
    channel_draws = read_csv("q2/q2_bootstrap_channel_draws.csv")
    diagnostics = read_csv("q2/q2_bootstrap_diagnostics.csv")
    convergence = read_csv("q2/q2_bootstrap_convergence.csv")
    failures = read_csv("q2/q2_bootstrap_failures.csv")
    risk = read_csv("q2/q2_q3_cap_risk.csv")

    sample_count = int(boot.get("successful_samples", -1))
    count_ok = (int(boot.get("requested_samples", -1)) == 500
                and sample_count == 500
                and int(boot.get("attempts", -1)) == sample_count + len(failures)
                and int(boot.get("failed_attempts", -1)) == len(failures))
    check("Q2", "条件参数自举成功样本为 500 且失败记录闭合", count_ok,
          f"requested={boot.get('requested_samples')}, success={sample_count}, "
          f"attempts={boot.get('attempts')}, failures={len(failures)}")

    require_columns("Q2", "年度碳强度 draws", rho_draws,
                    ["样本", "区域", "年度终端碳强度", "扩展生产责任P+_kt",
                     "消费责任全口径C+_kt"])
    require_columns("Q2", "来源份额 draws", mix_draws,
                    ["样本", "区域", *SOURCES, "省外输入"])
    channel_metrics = ["到达碳流_kt", "通道线损碳_kt", "到达电量_GWh", "送端电量_GWh"]
    require_columns("Q2", "通道方向 draws", channel_draws,
                    ["样本", "通道", "送端", "受端", *channel_metrics])
    require_columns("Q2", "通道方向区间", channel_interval,
                    ["通道", "送端", "受端", *[
                        f"{metric}_{suffix}" for metric in channel_metrics
                        for suffix in ("点估计", "P2.5", "P50", "P97.5")]])

    region_keys = {(region,) for region in REGIONS}
    channel_keys = set(map(tuple, channel_interval[["通道", "送端", "受端"]]
                           .itertuples(index=False, name=None)))
    panel_check("Q2", "年度碳强度/责任 draws", rho_draws, sample_count,
                ["区域"], region_keys)
    panel_check("Q2", "来源份额 draws", mix_draws, sample_count,
                ["区域"], region_keys)
    panel_check("Q2", "通道方向 draws", channel_draws, sample_count,
                ["通道", "送端", "受端"], channel_keys)
    q1_directions = set(map(tuple, read_csv(
        "q1/q1_reconciled_channel_month.csv")[[
            "通道编号", "送端区域", "受端区域"]]
        .drop_duplicates().itertuples(index=False, name=None)))
    check("Q2", "通道方向区间键唯一且属于 Q1 调和方向",
          not channel_interval.duplicated(["通道", "送端", "受端"]).any()
          and channel_keys.issubset(q1_directions), f"方向数={len(channel_keys)}")

    interval_specs = [
        ("年度碳强度", annual_interval, [("P2.5", "P50", "P97.5")]),
        ("月度碳强度", monthly_interval, [("P2.5", "P50", "P97.5")]),
        ("责任", responsibility_interval,
         [("P2.5_kt", "P50_kt", "P97.5_kt")]),
        ("来源份额", mix_interval, [("P2.5", "P50", "P97.5")]),
        ("Q3 排放风险", risk,
         [("排放P2.5_kt", "排放P50_kt", "排放P97.5_kt")]),
    ]
    all_ordered, details = True, []
    for label, frame, triples in interval_specs:
        ordered, violation = quantile_order(frame, triples)
        all_ordered &= ordered
        details.append(f"{label}:{violation:.2e}")
    channel_triples = [(f"{metric}_P2.5", f"{metric}_P50", f"{metric}_P97.5")
                       for metric in channel_metrics]
    ordered, violation = quantile_order(channel_interval, channel_triples)
    all_ordered &= ordered
    details.append(f"通道:{violation:.2e}")
    check("Q2", "所有条件区间满足 P2.5≤P50≤P97.5", all_ordered,
          ", ".join(details))

    annual_error = compare_group_quantiles(
        annual_interval, rho_draws, ["区域"],
        [("年度终端碳强度", "P2.5", "P50", "P97.5")])
    mix_draws_long = mix_draws.melt(
        id_vars=["样本", "区域"], value_vars=[*SOURCES, "省外输入"],
        var_name="来源", value_name="值")
    mix_error = compare_group_quantiles(
        mix_interval, mix_draws_long, ["区域", "来源"],
        [("值", "P2.5", "P50", "P97.5")])
    responsibility_subset = responsibility_interval[
        responsibility_interval["指标"].isin(["扩展生产责任P+", "消费责任全口径C+"])]
    responsibility_draws = rho_draws.melt(
        id_vars=["样本", "区域"],
        value_vars=["扩展生产责任P+_kt", "消费责任全口径C+_kt"],
        var_name="指标", value_name="值")
    responsibility_draws["指标"] = responsibility_draws["指标"].str.removesuffix("_kt")
    responsibility_error = compare_group_quantiles(
        responsibility_subset, responsibility_draws, ["区域", "指标"],
        [("值", "P2.5_kt", "P50_kt", "P97.5_kt")])
    channel_error = compare_group_quantiles(
        channel_interval, channel_draws, ["通道", "送端", "受端"],
        [(metric, f"{metric}_P2.5", f"{metric}_P50", f"{metric}_P97.5")
         for metric in channel_metrics])
    check("Q2", "导出区间由 500 次原始 draws 回算一致",
          max(annual_error, mix_error, responsibility_error, channel_error) <= 1e-9,
          f"annual={annual_error:.2e}, mix={mix_error:.2e}, "
          f"resp={responsibility_error:.2e}, channel={channel_error:.2e}")

    annual_point = annual_interval.set_index("区域")["点估计"].reindex(REGIONS)
    rho_point = rho.set_index("区域")["2025终端碳强度"].reindex(REGIONS)
    mix_sum = mix[[*SOURCES, "省外输入"]].sum(axis=1)
    draw_mix_sum = mix_draws[[*SOURCES, "省外输入"]].sum(axis=1)
    responsibility_sum_error = abs(float(responsibility["扩展生产责任P+"].sum())
                                   - float(responsibility["消费责任全口径C+"].sum()))
    check("Q2", "点估计碳强度、来源份额与责任守恒一致",
          # q2_rho_annual.csv 按 5 位小数发布，区间表保留全精度。
          max_abs_difference(annual_point, rho_point) <= 5.1e-6
          and np.allclose(mix_sum, 1.0, atol=1e-6)
          and np.allclose(draw_mix_sum, 1.0, atol=1e-7)
          and responsibility_sum_error <= 0.02
          and float(summary["责任守恒相对误差"]) <= 1e-8,
          f"责任CSV合计差={responsibility_sum_error:.3e} kt")

    require_columns("Q2", "bootstrap 数值诊断", diagnostics, [
        "样本", "最大区域月能量平衡残差_GWh", "最小节点总入流Q_GWh",
        "碳流线性系统最大条件数", "来源份额行和最大偏差", "碳势全部有限",
        "调和通道非负损耗最小值_GWh", "责任守恒相对误差"])
    diagnostic_ids = set(diagnostics["样本"].astype(int))
    diagnostics_ok = (len(diagnostics) == sample_count
                      and diagnostic_ids == set(range(1, sample_count + 1))
                      and not diagnostics["样本"].duplicated().any()
                      and bool_values(diagnostics["碳势全部有限"]).all()
                      and diagnostics["最大区域月能量平衡残差_GWh"].max() <= 1e-6
                      and diagnostics["最小节点总入流Q_GWh"].min() > 0.0
                      and np.isfinite(diagnostics["碳流线性系统最大条件数"]).all()
                      and diagnostics["碳流线性系统最大条件数"].max() < 1e8
                      and diagnostics["来源份额行和最大偏差"].max() <= 1e-7
                      and diagnostics["调和通道非负损耗最小值_GWh"].min() >= -1e-7
                      and diagnostics["责任守恒相对误差"].max() <= 1e-8)
    check("Q2", "500 个自举样本全部通过数值诊断", diagnostics_ok,
          f"balance={diagnostics['最大区域月能量平衡残差_GWh'].max():.2e}, "
          f"cond={diagnostics['碳流线性系统最大条件数'].max():.3g}, "
          f"responsibility={diagnostics['责任守恒相对误差'].max():.2e}")
    summary_diagnostics_ok = all([
        close(boot["maximum_energy_balance_residual_GWh"],
              diagnostics["最大区域月能量平衡残差_GWh"].max(), atol=1e-14),
        close(boot["minimum_node_total_inflow_Q_GWh"],
              diagnostics["最小节点总入流Q_GWh"].min(), atol=1e-10),
        close(boot["maximum_carbon_system_condition_number"],
              diagnostics["碳流线性系统最大条件数"].max(), atol=1e-10),
        close(boot["maximum_origin_share_row_sum_error"],
              diagnostics["来源份额行和最大偏差"].max(), atol=1e-14),
        close(boot["maximum_carbon_conservation_relative_error"],
              diagnostics["责任守恒相对误差"].max(), atol=1e-14),
    ])
    final_convergence = convergence.sort_values("样本数").iloc[-1]
    convergence_ok = (int(final_convergence["样本数"]) == sample_count
                      and abs(float(final_convergence[
                          "分位端点相对最终最大差_kg每kWh"])) <= 1e-15
                      and np.isfinite(float(final_convergence[
                          "批次法分位端点最大MCSE_kg每kWh"]))
                      and close(boot["final_batch_quantile_endpoint_max_mcse_kg_per_kWh"],
                                final_convergence[
                                    "批次法分位端点最大MCSE_kg每kWh"], atol=1e-12))
    check("Q2", "bootstrap summary 与诊断/收敛表闭合",
          summary_diagnostics_ok and convergence_ok,
          f"final_MCSE={final_convergence['批次法分位端点最大MCSE_kg每kWh']:.3e}")

    require_columns("Q2", "排序概率", rank, [
        "区域", "成为最高碳强度概率", "最高概率Wilson95%下界",
        "最高概率Wilson95%上界", "成为最低碳强度概率",
        "最低概率Wilson95%下界", "最低概率Wilson95%上界", "进入高碳前三概率",
        "前三概率Wilson95%下界", "前三概率Wilson95%上界", "平均秩_1为最高",
        "秩P2.5", "秩P97.5"])
    pivot = (rho_draws.pivot(index="样本", columns="区域",
                             values="年度终端碳强度")
             .reindex(columns=REGIONS).sort_index())
    array = pivot.to_numpy(float)
    highest = np.argmax(array, axis=1)
    lowest = np.argmin(array, axis=1)
    order = np.argsort(-array, axis=1)
    ranks = np.empty_like(order)
    ranks[np.arange(sample_count)[:, None], order] = np.arange(1, len(REGIONS) + 1)
    high_count = np.array([(highest == index).sum() for index in range(len(REGIONS))])
    low_count = np.array([(lowest == index).sum() for index in range(len(REGIONS))])
    top_count = np.array([(ranks[:, index] <= 3).sum()
                          for index in range(len(REGIONS))])
    high_lo, high_hi = wilson_interval(high_count, sample_count)
    low_lo, low_hi = wilson_interval(low_count, sample_count)
    top_lo, top_hi = wilson_interval(top_count, sample_count)
    expected_rank = pd.DataFrame({
        "区域": REGIONS,
        "成为最高碳强度概率": high_count / sample_count,
        "最高概率Wilson95%下界": high_lo,
        "最高概率Wilson95%上界": high_hi,
        "成为最低碳强度概率": low_count / sample_count,
        "最低概率Wilson95%下界": low_lo,
        "最低概率Wilson95%上界": low_hi,
        "进入高碳前三概率": top_count / sample_count,
        "前三概率Wilson95%下界": top_lo,
        "前三概率Wilson95%上界": top_hi,
        "平均秩_1为最高": ranks.mean(axis=0),
        "秩P2.5": np.quantile(ranks, 0.025, axis=0),
        "秩P97.5": np.quantile(ranks, 0.975, axis=0),
    }).set_index("区域")
    actual_rank = rank.set_index("区域").reindex(REGIONS)
    rank_error = max_abs_difference(actual_rank[expected_rank.columns], expected_rank)
    probability_sums_ok = (
        close(rank["成为最高碳强度概率"].sum(), 1.0)
        and close(rank["成为最低碳强度概率"].sum(), 1.0)
        and close(rank["进入高碳前三概率"].sum(), 3.0))
    check("Q2", "排序概率、Wilson 区间与 500 次 draws 回算一致",
          rank_error <= 1e-12 and probability_sums_ok,
          f"最大误差={rank_error:.2e}, 概率和="
          f"({rank['成为最高碳强度概率'].sum():.3f},"
          f"{rank['成为最低碳强度概率'].sum():.3f},"
          f"{rank['进入高碳前三概率'].sum():.3f})")
    high_summary = boot.get("highest_region_probabilities", {})
    low_summary = boot.get("lowest_region_probabilities", {})
    summary_rank_ok = all(
        close(high_summary.get(region, np.nan),
              actual_rank.loc[region, "成为最高碳强度概率"])
        and close(low_summary.get(region, np.nan),
                  actual_rank.loc[region, "成为最低碳强度概率"])
        for region in REGIONS)
    check("Q2", "排序概率 summary 与表格一致", summary_rank_ok)

    require_columns("Q2", "Q3 固定方案风险", risk, [
        "年份", "碳上限_kt", "方案点估计排放_kt", "点估计重构误差_kt",
        "排放P2.5_kt", "排放P50_kt", "排放P97.5_kt", "条件超限概率",
        "超限概率Wilson95%下界", "超限概率Wilson95%上界", "期望超限量_kt",
        "最差5%平均超限量_kt"])
    plan = read_csv("q3/q3_epsilon_recommended_regional.csv")
    require_columns("Q2", "Q3 推荐区域表的风险传播字段", plan, [
        "区域", "年份", "碳强度作用电量_GWh", "与碳强度无关排放项_kt",
        "消费碳_精确kt"])
    constraints = data_io.load_annual_constraints().set_index("年份")
    point_rho = rho.set_index("区域")["2025终端碳强度"].reindex(REGIONS)
    risk = risk.set_index("年份").reindex(PLAN_YEARS)
    risk_worst_error = 0.0
    risk_ok = set(plan["年份"].astype(int)) == set(PLAN_YEARS)
    for year in PLAN_YEARS:
        rows = plan[plan["年份"] == year].set_index("区域").reindex(REGIONS)
        exposure = rows["碳强度作用电量_GWh"].to_numpy(float)
        fixed = float(rows["与碳强度无关排放项_kt"].sum())
        kappa = float(constraints.loc[year,
                          "基准供电碳强度调整系数(相对2025)"])
        values = kappa * array.dot(exposure) + fixed
        cap = float(constraints.loc[year, "消费侧碳排放上限(ktCO2)"])
        point = kappa * point_rho.to_numpy(float).dot(exposure) + fixed
        excess = np.maximum(values - cap, 0.0)
        count = int((values > cap).sum())
        probability_lo, probability_hi = wilson_interval(count, sample_count)
        expected = {
            "碳上限_kt": cap,
            "方案点估计排放_kt": point,
            "点估计重构误差_kt": point - float(rows["消费碳_精确kt"].sum()),
            "排放P2.5_kt": np.quantile(values, 0.025),
            "排放P50_kt": np.quantile(values, 0.5),
            "排放P97.5_kt": np.quantile(values, 0.975),
            "条件超限概率": count / sample_count,
            "超限概率Wilson95%下界": float(probability_lo),
            "超限概率Wilson95%上界": float(probability_hi),
            "期望超限量_kt": float(np.mean(excess)),
            "最差5%平均超限量_kt": float(np.mean(
                np.sort(excess)[-max(1, sample_count // 20):])),
        }
        for column, expected_value in expected.items():
            risk_worst_error = max(
                risk_worst_error,
                abs(float(risk.loc[year, column]) - expected_value))
        risk_ok &= abs(expected["点估计重构误差_kt"]) <= 1e-5
    risk_summary = boot.get("q3_fixed_recommended_plan_cap_risk", {})
    risk_summary_ok = all(
        close(risk_summary.get(str(year), np.nan),
              risk.loc[year, "条件超限概率"], atol=1e-12)
        for year in PLAN_YEARS)
    check("Q2", "Q3 固定推荐方案风险由年度 rho draws 独立重构",
          risk_ok and risk_worst_error <= 1e-8 and risk_summary_ok,
          f"最大字段误差={risk_worst_error:.2e}")


def verify_q3() -> None:
    summary = read_json("q3/q3_summary.json")
    epsilon_summary = read_json("q3/q3_epsilon_summary.json")
    pareto = read_csv("q3/q3_epsilon_pareto.csv").sort_values("epsilon")
    validation = read_csv("q3/q3_epsilon_validation.csv").sort_values("epsilon")
    recommended_regional = read_csv("q3/q3_epsilon_recommended_regional.csv")
    recommended_schedule = read_csv("q3/q3_epsilon_recommended_schedule.csv")
    recommended_yearly = read_csv("q3/q3_epsilon_recommended_yearly.csv")

    require_columns("Q3", "epsilon-Pareto", pareto, [
        "epsilon", "最优缺供_GWh", "最小投资Cstar_百万元", "投资容许上限_百万元",
        "实际投资_百万元", "相对Cstar增投_百分比", "最大区域相对预算超额R",
        "MILP状态", "MILP_gap", "约束回代通过"])
    epsilon = pareto["epsilon"].to_numpy(float)
    cstar = pareto["最小投资Cstar_百万元"].to_numpy(float)
    investment_cap = pareto["投资容许上限_百万元"].to_numpy(float)
    investment = pareto["实际投资_百万元"].to_numpy(float)
    fairness = pareto["最大区域相对预算超额R"].to_numpy(float)
    expected_cap = (1.0 + epsilon) * cstar
    expected_increase = 100.0 * (investment / cstar - 1.0)
    structure_ok = (len(epsilon) >= 2 and np.all(np.diff(epsilon) > 0)
                    and np.allclose(cstar, cstar[0], atol=1e-7)
                    and np.allclose(investment_cap, expected_cap, atol=1e-7)
                    and bool((investment >= cstar - 1e-6).all())
                    and bool((investment <= investment_cap + 1e-5).all())
                    and np.allclose(pareto["相对Cstar增投_百分比"],
                                    expected_increase, atol=1e-7)
                    and bool((pareto["最优缺供_GWh"].abs() <= 1e-7).all()))
    check("Q3", "词典序 Pareto 的 C*、epsilon 投资上界与零缺供闭合",
          structure_ok,
          f"C*范围=[{cstar.min():.6f},{cstar.max():.6f}], "
          f"最大上界误差={max_abs_difference(investment_cap, expected_cap):.2e}")
    monotone_ok = (bool((np.diff(investment) >= -1e-6).all())
                   and bool((np.diff(fairness) <= 1e-8).all()))
    check("Q3", "epsilon 增大时投资不降且最大相对超额不升", monotone_ok,
          f"最小投资增量={np.diff(investment).min():.3e}, "
          f"最大公平性增量={np.diff(fairness).max():.3e}")

    require_columns("Q3", "epsilon 独立约束回代", validation, [
        "epsilon", "solver_status", "termination", "relative_gap",
        "max_constraint_violation", "max_variable_bound_violation",
        "max_integrality_violation", "passed"])
    audit_ok = (np.allclose(validation["epsilon"], epsilon, atol=1e-12)
                and (validation["solver_status"].astype(str).str.lower() == "ok").all()
                and (validation["termination"].astype(str).str.lower() == "optimal").all()
                and bool_values(validation["passed"]).all()
                and validation["relative_gap"].fillna(np.inf).max() <= 1e-7
                and validation["max_constraint_violation"].max() <= 1e-6
                and validation["max_variable_bound_violation"].max() <= 1e-6
                and validation["max_integrality_violation"].max() <= 1e-6)
    check("Q3", "全部 epsilon 方案最优且独立约束回代通过", audit_ok,
          f"rows={len(validation)}, max_gap={validation['relative_gap'].max():.2e}, "
          f"max_violation={validation['max_constraint_violation'].max():.2e}")

    recommended_epsilon = float(epsilon_summary["recommended_epsilon"])
    recommended_rows = pareto[np.isclose(pareto["epsilon"], recommended_epsilon)]
    recommended_exists = len(recommended_rows) == 1
    recommended_row = recommended_rows.iloc[0] if recommended_exists else None
    recommended_json = epsilon_summary["recommended"]
    summary_ok = (close(epsilon_summary["stage2_minimum_investment_Cstar_million"],
                        cstar[0], atol=1e-7)
                  and bool(epsilon_summary["all_epsilon_constraints_pass"])
                  and recommended_exists
                  and close(recommended_json["investment_million"],
                            recommended_row["实际投资_百万元"], atol=1e-7)
                  and close(recommended_json["max_relative_budget_excess"],
                            recommended_row["最大区域相对预算超额R"], atol=1e-9)
                  and bool(recommended_json["constraint_audit"]["passed"])
                  and close(summary["总投资_百万元"],
                            epsilon_summary["weighted_baseline"]["总投资_百万元"],
                            atol=0.05))
    check("Q3", "epsilon summary、推荐行与加权基线相互一致", summary_ok,
          f"recommended epsilon={recommended_epsilon:g}")

    require_columns("Q3", "推荐年度表", recommended_yearly,
                    ["年份", "投资_百万元", "消费侧碳排放_kt", "碳上限_kt",
                     "碳裕度_kt", "缺供_GWh"])
    require_columns("Q3", "推荐区域表", recommended_regional,
                    ["区域", "年份", "消费碳_精确kt", "预算超额_kt", "相对预算超额"])
    require_columns("Q3", "推荐开工表", recommended_schedule,
                    ["项目", "开工年", "开工规模", "投资_百万元"])
    region_year_keys = list(zip(recommended_regional["区域"],
                                recommended_regional["年份"].astype(int)))
    exact_by_year = recommended_regional.groupby("年份")["消费碳_精确kt"].sum()
    yearly = recommended_yearly.set_index("年份").reindex(PLAN_YEARS)
    schedule_investment = float(recommended_schedule["投资_百万元"].sum())
    yearly_investment = float(recommended_yearly["投资_百万元"].sum())
    exported_investment = float(recommended_json["investment_million"])
    recommendation_ok = (
        len(region_year_keys) == len(REGIONS) * len(PLAN_YEARS)
        and len(set(region_year_keys)) == len(region_year_keys)
        and set(region_year_keys) == {(region, year) for region in REGIONS
                                      for year in PLAN_YEARS}
        and set(recommended_yearly["年份"].astype(int)) == set(PLAN_YEARS)
        and (recommended_yearly["缺供_GWh"].abs() <= 1e-6).all()
        and (recommended_yearly["碳裕度_kt"] >= -1e-6).all()
        and max_abs_difference(exact_by_year.reindex(PLAN_YEARS),
                               yearly["消费侧碳排放_kt"]) <= 0.06
        and abs(schedule_investment - exported_investment) <= 0.02
        and abs(yearly_investment - exported_investment) <= 0.02
        and close(recommended_regional["相对预算超额"].max(),
                  recommended_json["max_relative_budget_excess"], atol=5e-7))
    check("Q3", "推荐方案区域/年度/开工表闭合且零缺供达标", recommendation_ok,
          f"schedule投资={schedule_investment:.6f}, yearly投资={yearly_investment:.3f}, "
          f"summary投资={exported_investment:.6f}")


def verify_q4() -> None:
    summary = read_json("q4/q4_summary.json")
    por = read_csv("q4/q4_por_curve.csv").sort_values("Gamma缩放")
    trace = read_csv("q4/q4_hard_feasibility_trace.csv").sort_values("迭代")
    gaps = (read_csv("q4/q4_hard_gap_by_year.csv").set_index("年份")
            .reindex(PLAN_YEARS))
    restoration = read_csv("q4/q4_hard_restoration.csv")
    regret_summary = read_json("q4/q4_regret_summary.json")
    regret = (read_csv("q4/q4_regret_paths.csv").set_index("情景")
              .reindex(["S0", "S1", "S2", "S3"]))
    regret_schedule = read_csv("q4/q4_regret_schedule.csv")
    rolling = read_csv("q4/q4_rolling.csv").sort_values("决策年")
    stress = read_csv("q4/q4_stress.csv")
    scenario_log = read_csv("q4/q4_ccg_log.csv")

    require_columns("Q4", "硬可行半径二分轨迹", trace,
                    ["迭代", "试探tau", "硬零越限可行", "可行下界tau", "不可行上界tau"])
    feasible = bool_values(trace["硬零越限可行"])
    trial = trace["试探tau"].to_numpy(float)
    lower = trace["可行下界tau"].to_numpy(float)
    upper = trace["不可行上界tau"].to_numpy(float)
    trace_logic = (len(trace) > 0 and bool((lower <= upper + 1e-12).all())
                   and bool((np.diff(lower) >= -1e-12).all())
                   and bool((np.diff(upper) <= 1e-12).all())
                   and np.allclose(trial[feasible], lower[feasible], atol=1e-12)
                   and np.allclose(trial[~feasible], upper[~feasible], atol=1e-12)
                   and feasible.any() and (~feasible).any())
    tau_star = float(summary["硬可行半径_tau_star"])
    final_width = float(upper[-1] - lower[-1])
    tau_ok = (trace_logic and close(tau_star, lower[-1], atol=1e-12)
              and final_width <= 1e-4 and tau_star < 1.0)
    check("Q4", "tau* 由可行下界/不可行上界二分括住", tau_ok,
          f"tau*={tau_star:.9f}, bracket=[{lower[-1]:.9f},{upper[-1]:.9f}], "
          f"width={final_width:.2e}")

    require_columns("Q4", "Gamma=1 分年最小硬缺口", gaps.reset_index(),
                    ["年份", "最小硬缺口_kt"])
    gap_total = float(gaps["最小硬缺口_kt"].sum())
    gap_summary = summary["Gamma1分年最小硬缺口_kt"]
    gap_year_error = max(
        abs(float(gaps.loc[year, "最小硬缺口_kt"])
            - float(gap_summary[str(year)])) for year in PLAN_YEARS)
    gap_ok = (gaps["最小硬缺口_kt"].notna().all()
              and (gaps["最小硬缺口_kt"] >= -ATOL).all()
              and close(gap_total, summary["Gamma1最小总硬缺口_kt"], atol=1e-7)
              and gap_year_error <= 1e-8
              and ((gap_total <= 1e-7)
                   == bool(summary["Gamma1是否完整硬可行"])))
    check("Q4", "Gamma=1 最小硬缺口总量与分年值闭合", gap_ok,
          f"sum={gap_total:.9f}, year_max_error={gap_year_error:.2e}, "
          f"hard_feasible={summary['Gamma1是否完整硬可行']}")

    require_columns("Q4", "POR 双口径", por, [
        "Gamma缩放", "目标值_百万元", "投资_百万元", "设计集tauGamma违约_kt",
        "统一Gamma回测违约_kt", "最坏情景总越限_kt"])
    gamma_values = por["Gamma缩放"].to_numpy(float)
    gamma1_rows = por[np.isclose(por["Gamma缩放"], 1.0)]
    nominal_rows = por[np.isclose(por["Gamma缩放"], 0.0)]
    dual_ok = (len(gamma1_rows) == 1 and len(nominal_rows) == 1
               and np.all(np.diff(gamma_values) > 0)
               and np.allclose(por["最坏情景总越限_kt"],
                               por["统一Gamma回测违约_kt"], atol=1e-10)
               and (por[["设计集tauGamma违约_kt", "统一Gamma回测违约_kt"]]
                    >= -ATOL).all().all())
    gamma1, nominal = gamma1_rows.iloc[0], nominal_rows.iloc[0]
    por_summary_ok = all([
        close(nominal["投资_百万元"], summary["确定性方案投资_百万元"], atol=0.05),
        close(nominal["统一Gamma回测违约_kt"],
              summary["确定性方案统一Gamma回测违约_kt"], atol=0.01),
        close(gamma1["投资_百万元"], summary["Gamma1软约束方案投资_百万元"],
              atol=0.05),
        close(gamma1["设计集tauGamma违约_kt"],
              summary["Gamma1软约束方案设计集违约_kt"], atol=0.01),
        close(gamma1["统一Gamma回测违约_kt"],
              summary["Gamma1软约束方案统一Gamma回测违约_kt"], atol=0.01),
        close(gamma1["统一Gamma回测违约_kt"], gap_total, atol=0.01),
        close(float(gamma1["投资_百万元"] - nominal["投资_百万元"]),
              summary["Gamma1软约束溢价_百万元"], atol=0.11),
    ])
    check("Q4", "POR 同时报设计集与统一 Gamma 回测且与 summary 闭合",
          dual_ok and por_summary_ok,
          f"Gamma1 design={gamma1['设计集tauGamma违约_kt']:.2f}, "
          f"common={gamma1['统一Gamma回测违约_kt']:.2f} kt")

    require_columns("Q4", "Gamma=1 硬可行恢复", restoration, [
        "放宽对象", "鲁棒预算Gamma缩放", "基准倍数", "基准硬零越限可行",
        "最大不可行倍数_下界", "最小可行倍数_上界", "二分区间宽度", "二分容差",
        "临界倍数硬零越限可行", "略低倍数", "略低倍数硬零越限可行",
        "临界方案独立Gamma回测总越限_kt"])
    relaxation_names = {
        "年度投资上限": ("年度投资上限",
                         "Gamma1硬零越限_年度投资上限最小倍数"),
        "C1--C5施工资源上限": ("五类施工资源上限",
                              "Gamma1硬零越限_五类施工资源上限最小统一倍数"),
    }
    restore_summary = summary["Gamma1硬零越限_恢复验证"]
    restore_ok = (set(restoration["放宽对象"]) == set(relaxation_names)
                  and not bool(restore_summary["原约束可行"]))
    restore_details = []
    for object_name, (nested_name, top_key) in relaxation_names.items():
        row = restoration[restoration["放宽对象"] == object_name].iloc[0]
        lower_scale = float(row["最大不可行倍数_下界"])
        upper_scale = float(row["最小可行倍数_上界"])
        nested = restore_summary[nested_name]
        row_ok = all([
            close(row["鲁棒预算Gamma缩放"], 1.0),
            close(row["基准倍数"], 1.0),
            not bool(row["基准硬零越限可行"]),
            1.0 < lower_scale < upper_scale,
            close(row["二分区间宽度"], upper_scale - lower_scale, atol=1e-10),
            upper_scale - lower_scale <= float(row["二分容差"]) + 1e-12,
            bool(row["临界倍数硬零越限可行"]),
            not bool(row["略低倍数硬零越限可行"]),
            close(row["略低倍数"], lower_scale, atol=1e-10),
            float(row["临界方案独立Gamma回测总越限_kt"]) <= 1e-6,
            close(summary[top_key], upper_scale, atol=1e-12),
            close(nested["最大不可行倍数_下界"], lower_scale, atol=1e-12),
            close(nested["最小可行倍数_上界"], upper_scale, atol=1e-12),
            bool(nested["临界倍数可行"]),
            not bool(nested["略低倍数可行"]),
            float(nested["独立Gamma回测总越限_kt"]) <= 1e-6,
        ])
        restore_ok &= row_ok
        restore_details.append(f"{object_name}:[{lower_scale:.7f},{upper_scale:.7f}]")
    check("Q4", "两类硬可行恢复均给出不可行/可行二分括界", restore_ok,
          "; ".join(restore_details))

    require_columns("Q4", "四路径相对遗憾", regret.reset_index(), [
        "情景", "PI目标_百万元", "PI投资_百万元", "非预见方案目标_百万元",
        "非预见方案投资_百万元", "共享一阶段投资_百万元", "绝对遗憾_百万元",
        "相对遗憾", "相对遗憾_百分比", "总越限_kt", "最大年度越限_kt",
        "硬碳约束满足"])
    absolute_expected = regret["非预见方案目标_百万元"] - regret["PI目标_百万元"]
    relative_expected = absolute_expected / regret["PI目标_百万元"]
    formula_error = max(
        max_abs_difference(regret["绝对遗憾_百万元"], absolute_expected),
        max_abs_difference(regret["相对遗憾"], relative_expected),
        max_abs_difference(regret["相对遗憾_百分比"], 100.0 * relative_expected))
    hard_cap_ok = (bool_values(regret["硬碳约束满足"]).all()
                   and regret["总越限_kt"].max() <= 1e-6
                   and regret["最大年度越限_kt"].max() <= 1e-6
                   and (absolute_expected >= -1e-5).all())
    regret_summary_ok = all([
        close(regret_summary["最大相对遗憾"], regret["相对遗憾"].max(), atol=1e-10),
        close(regret_summary["最大相对遗憾_百分比"],
              regret["相对遗憾_百分比"].max(), atol=1e-8),
        close(regret_summary["共享一阶段投资_百万元"],
              regret["共享一阶段投资_百万元"].iloc[0], atol=1e-8),
        bool(regret_summary["四路径全部硬达标"]),
        not bool(regret_summary["路径是否赋概率"]),
    ])
    for scenario in regret.index:
        regret_summary_ok &= all([
            close(regret_summary["PI目标_百万元"][scenario],
                  regret.loc[scenario, "PI目标_百万元"], atol=1e-8),
            close(regret_summary["路径目标_百万元"][scenario],
                  regret.loc[scenario, "非预见方案目标_百万元"], atol=1e-8),
            close(regret_summary["路径投资_百万元"][scenario],
                  regret.loc[scenario, "非预见方案投资_百万元"], atol=1e-8),
        ])
    check("Q4", "四路径遗憾公式、硬 cap 与 summary 一致",
          formula_error <= 1e-8 and hard_cap_ok and regret_summary_ok,
          f"公式最大误差={formula_error:.2e}, "
          f"max regret={regret['相对遗憾'].max():.6f}, "
          f"max violation={regret['总越限_kt'].max():.2e}")

    require_columns("Q4", "四路径开工表", regret_schedule,
                    ["情景", "项目", "开工年", "规模", "阶段", "投资_百万元"])
    first_stage = regret_schedule[regret_schedule["开工年"].isin([2026, 2027])]
    recourse = regret_schedule[~regret_schedule["开工年"].isin([2026, 2027])]
    union_keys = sorted(set(zip(first_stage["项目"], first_stage["开工年"])))
    vectors = []
    for scenario in ["S0", "S1", "S2", "S3"]:
        series = (first_stage[first_stage["情景"] == scenario]
                  .set_index(["项目", "开工年"])["规模"])
        vectors.append(np.array([float(series.get(key, 0.0)) for key in union_keys]))
    nonanticipative = all(np.allclose(vectors[0], vector, atol=1e-8)
                          for vector in vectors[1:])
    schedule_investment = regret_schedule.groupby("情景")["投资_百万元"].sum()
    first_investment = first_stage.groupby("情景")["投资_百万元"].sum()
    schedule_ok = (nonanticipative
                   and set(regret_schedule["情景"]) == {"S0", "S1", "S2", "S3"}
                   and (first_stage["阶段"] == "共享一阶段").all()
                   and (recourse["阶段"] == "路径追索").all()
                   and max_abs_difference(
                       schedule_investment.reindex(regret.index),
                       regret["非预见方案投资_百万元"]) <= 1e-7
                   and max_abs_difference(
                       first_investment.reindex(regret.index),
                       regret["共享一阶段投资_百万元"]) <= 1e-7)
    check("Q4", "2026--2027 开工严格非预见共享，后续按路径追索", schedule_ok,
          f"共享决策键={len(union_keys)}, first-stage投资误差="
          f"{max_abs_difference(first_investment.reindex(regret.index), regret['共享一阶段投资_百万元']):.2e}")

    require_columns("Q4", "滚动 objective-to-go", rolling, [
        "决策年", "全周期条件目标_百万元", "历史已发生目标项_百万元",
        "剩余期目标_百万元", "不使用本年信息剩余期目标_百万元", "本年信息价值_百万元",
        "不使用本年信息全周期目标_百万元", "越限2028_kt", "越限2029_kt", "越限2030_kt"])
    split_error = max_abs_difference(
        rolling["全周期条件目标_百万元"],
        rolling["历史已发生目标项_百万元"] + rolling["剩余期目标_百万元"])
    no_info_split_error = max_abs_difference(
        rolling["不使用本年信息全周期目标_百万元"],
        rolling["历史已发生目标项_百万元"]
        + rolling["不使用本年信息剩余期目标_百万元"])
    information_error = max_abs_difference(
        rolling["本年信息价值_百万元"],
        rolling["不使用本年信息剩余期目标_百万元"] - rolling["剩余期目标_百万元"])
    violation_columns = ["越限2028_kt", "越限2029_kt", "越限2030_kt"]
    rolling_ok = (set(rolling["决策年"].astype(int)) == {2028, 2029, 2030}
                  and split_error <= 0.002 and no_info_split_error <= 0.002
                  and information_error <= 0.002
                  and rolling["本年信息价值_百万元"].min() >= -1e-8
                  and rolling[violation_columns].max().max() <= 1e-6)
    check("Q4", "滚动目标按 sunk/to-go 正确拆分且 S3 硬达标", rolling_ok,
          f"split={split_error:.3e}, no-info split={no_info_split_error:.3e}, "
          f"info={information_error:.3e}")

    require_columns("Q4", "压力情景", stress,
                    ["情景", "年份", "碳排放_kt", "上限_kt", "越限_kt"])
    expected_stress = np.maximum(stress["碳排放_kt"] - stress["上限_kt"], 0.0)
    stress_error = max_abs_difference(stress["越限_kt"], expected_stress)
    require_columns("Q4", "可行性场景生成日志", scenario_log,
                    ["方法", "迭代", "情景数", "目标值_百万元"])
    heuristic_ok = (scenario_log["方法"].eq("可行性场景生成启发式").all()
                    and close(scenario_log.iloc[-1]["目标值_百万元"],
                              summary["可行性场景生成启发式目标_百万元"], atol=0.05)
                    and int(scenario_log.iloc[-1]["情景数"])
                    == int(summary["可行性场景生成启发式情景数"]))
    check("Q4", "压力越限算式与启发式方法标签正确",
          stress_error <= 0.11 and heuristic_ok,
          f"压力表舍入误差={stress_error:.3f} kt, "
          f"method={scenario_log['方法'].unique().tolist()}")


def verify_deepen() -> None:
    summary = read_json("deepen/deepen_summary.json")
    q1_sensitivity = read_csv("deepen/q1_param_sensitivity.csv")
    shapley = read_csv("deepen/q2_responsibility_shapley.csv")
    q3_baselines = read_csv("deepen/q3_baselines.csv")
    q4_gamma = read_csv("deepen/q4_gamma_sensitivity.csv")
    q4_three = read_csv("deepen/q4_three_schemes.csv")

    require_columns("深化", "Shapley 责任", shapley,
                    ["区域", "扩展生产责任P+", "消费责任全口径C+", "Shapley责任"])
    structural_identity = 0.5 * (shapley["扩展生产责任P+"]
                                 + shapley["消费责任全口径C+"])
    identity_error = max_abs_difference(shapley["Shapley责任"], structural_identity)
    shapley_sum = float(shapley["Shapley责任"].sum())
    shapley_summary = summary["shapley"]
    conservation_ok = (set(shapley["区域"]) == set(REGIONS)
                       and identity_error <= 0.011
                       and close(shapley_sum, shapley_summary["Shapley合计"], atol=0.02)
                       and close(shapley_summary["vN"],
                                 shapley_summary["Pplus合计"], atol=1e-4)
                       and close(shapley_summary["vN"],
                                 shapley_summary["Shapley合计"], atol=1e-4)
                       and float(shapley_summary["守恒相对误差"]) <= 1e-10)
    check("深化", "Shapley 守恒及其与五五共担的结构恒等式", conservation_ok,
          f"identity最大舍入误差={identity_error:.3f} kt, sum={shapley_sum:.2f}")

    require_columns("深化", "Q1 参数敏感性", q1_sensitivity,
                    ["类型", "参数值", "稳健目标值", "描述性观测RSS每项",
                     "区内损耗率", "E05线损估计"])
    q1_summary = read_json("q1/q1_summary.json")
    base_rows = q1_sensitivity[
        ((q1_sensitivity["类型"] == "损耗先验")
         & np.isclose(q1_sensitivity["参数值"], 0.05))
        | ((q1_sensitivity["类型"] == "σ缩放")
           & np.isclose(q1_sensitivity["参数值"], 1.0))]
    sensitivity_ok = (
        len(base_rows) == 2
        and np.allclose(base_rows["稳健目标值"], q1_summary["稳健目标值"], atol=1e-6)
        and np.allclose(base_rows["描述性观测RSS每项"],
                        q1_summary["标准化观测加权残差/观测项"], atol=1e-8)
        and np.allclose(base_rows["区内损耗率"],
                        q1_summary["区内损耗率(全省)"], atol=5e-6)
        and np.allclose(base_rows["E05线损估计"],
                        q1_summary["eta"]["E05"], atol=5e-6))
    check("深化", "Q1 敏感性的两个基准设定回到主结果", sensitivity_ok,
          f"基准行数={len(base_rows)}")

    require_columns("深化", "Q3 基线比较", q3_baselines,
                    ["方案", "投资_百万元", "五年总越限_kt", "碳约束可行"])
    q3_summary = read_json("q3/q3_summary.json")
    milp = q3_baselines[q3_baselines["方案"].astype(str).str.contains("MILP")]
    q3_ok = (len(milp) == 1
             and close(milp.iloc[0]["投资_百万元"], q3_summary["总投资_百万元"],
                       atol=0.05)
             and bool(milp.iloc[0]["碳约束可行"])
             and float(milp.iloc[0]["五年总越限_kt"]) <= 1e-6)
    check("深化", "Q3 深化基线中的 MILP 行与主结果一致", q3_ok)

    require_columns("深化", "Q4 Gamma 敏感性", q4_gamma,
                    ["tau", "投资_百万元", "设计集tauGamma违约_kt",
                     "统一Gamma回测违约_kt"])
    por = read_csv("q4/q4_por_curve.csv")
    merged = q4_gamma.merge(
        por[["Gamma缩放", "投资_百万元", "设计集tauGamma违约_kt",
             "统一Gamma回测违约_kt"]], left_on="tau", right_on="Gamma缩放",
        suffixes=("_深化", "_Q4"), validate="one_to_one")
    gamma_error = max(max_abs_difference(
        merged[f"{column}_深化"], merged[f"{column}_Q4"])
        for column in ["投资_百万元", "设计集tauGamma违约_kt", "统一Gamma回测违约_kt"])
    check("深化", "Q4 Gamma 敏感性保留双口径并与 POR 一致",
          len(merged) == len(q4_gamma) == len(por) and gamma_error <= 1e-10,
          f"最大误差={gamma_error:.2e}")

    require_columns("深化", "Q4 三方案", q4_three,
                    ["方案", "总投资_百万元", "预算集最坏总越限_kt", "推荐"])
    q4_summary = read_json("q4/q4_summary.json")
    gamma1 = q4_three[q4_three["方案"].astype(str).str.contains("Γ=1")]
    narrative_ok = False
    if len(gamma1) == 1:
        numbers = [float(value) for value in re.findall(
            r"(?<![A-Za-z0-9])([0-9]+(?:\.[0-9]+)?)\s*kt",
            str(gamma1.iloc[0]["推荐"]))]
        narrative_ok = (
            close(gamma1.iloc[0]["预算集最坏总越限_kt"],
                  q4_summary["Gamma1最小总硬缺口_kt"], atol=0.01)
            and any(close(number, q4_summary["Gamma1最小总硬缺口_kt"], atol=0.01)
                    for number in numbers)
            and "不可称完整硬鲁棒" in str(gamma1.iloc[0]["推荐"]))
    check("深化", "Q4 三方案的 Gamma=1 缺口数值与叙述同步", narrative_ok,
          "" if len(gamma1) != 1 else str(gamma1.iloc[0]["推荐"]))


def verify_q5() -> None:
    """调用生成器从当前上游重算，避免复制一份会过时的固定数字。"""
    from .q5_report.main import collect, render

    actual_key = read_json("q5/q5_key_numbers.json")
    # JSON 对象键必为字符串；collect 中按年份组织的 dict 使用整数键，先按
    # 实际序列化规则规范化后再递归比较。
    expected_raw = collect()["key"]
    expected_key = json.loads(json.dumps(
        expected_raw, ensure_ascii=False, default=str))
    mismatches = nested_mismatches(actual_key, expected_key, atol=1e-8)
    check("Q5", "关键数字 JSON 由当前 Q1--Q4 产物生成", not mismatches,
          "" if not mismatches else "; ".join(mismatches[:5]))

    actual_report = (OUT_DIR / "q5/q5_report_draft.md").read_text(encoding="utf-8")
    expected_report = render(expected_raw)
    headings = re.findall(r"^##\s+", actual_report, flags=re.MULTILINE)
    check("Q5", "咨询报告正文与当前关键数字渲染结果完全一致",
          actual_report == expected_report and len(headings) == 4,
          f"非空白字符={sum(not char.isspace() for char in actual_report)}, "
          f"二级标题={len(headings)}")


def run_section(name: str, function: Callable[[], None]) -> None:
    try:
        function()
    except Exception as exception:  # 首错不阻止其他模块继续提供诊断。
        check(name, "验证过程无异常", False,
              f"{type(exception).__name__}: {exception}")


def main() -> None:
    RESULTS.clear()
    run_section("文件", verify_files)
    run_section("Q1", verify_q1)
    run_section("Q2", verify_q2)
    run_section("Q3", verify_q3)
    run_section("Q4", verify_q4)
    run_section("深化", verify_deepen)
    run_section("Q5", verify_q5)

    result = pd.DataFrame(RESULTS, columns=["模块", "声明", "通过", "备注"])
    result["通过"] = result["通过"].map({True: "PASS", False: "FAIL"})
    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", 95)
    print(result.to_string(index=False))
    failure_count = int((result["通过"] == "FAIL").sum())
    print(f"\n共 {len(result)} 项核查，FAIL {failure_count} 项")
    if failure_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
