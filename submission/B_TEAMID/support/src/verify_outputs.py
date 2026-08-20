"""对外声明 vs 实际产物 逐项核查 + 独立一致性复算。

用法:.venv/bin/python -m src.verify_outputs
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .common import data_io
from .common.paths import CHANNELS, OUT_DIR, REGIONS

RESULTS: list[tuple[str, str, bool, str]] = []


def check(section: str, claim: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((section, claim, bool(ok), detail))


def jload(q: str) -> dict:
    with open(OUT_DIR / q / f"{q}_summary.json", encoding="utf-8") as f:
        return json.load(f)


def verify_files() -> None:
    expected = {
        "q1": ["fig_q1_adjust_top20.png", "fig_q1_eta_compare.png",
               "fig_q1_raw_residual_heatmap.png", "q1_adjustments.csv",
               "q1_anomalies.csv", "q1_eta.csv", "q1_influence.csv",
               "q1_reconciled_channel_month.csv",
               "q1_reconciled_region_month.csv", "q1_summary.json"],
        "q2": ["fig_q2_loss_convention_diff.png", "fig_q2_origin_mix.png",
               "fig_q2_responsibility.png", "fig_q2_rho_monthly.png",
               "q2_import_share.csv", "q2_origin_mix_annual.csv",
               "q2_responsibility.csv", "q2_rho_annual.csv",
               "q2_rho_monthly.csv", "q2_summary.json"],
        "q3": ["fig_q3_carbon_trajectory.png", "fig_q3_merit_order.png",
               "fig_q3_schedule.png", "q3_merit_order.csv", "q3_regional.csv",
               "q3_schedule.csv", "q3_sensitivity.csv",
               "q3_shadow_prices.csv", "q3_summary.json", "q3_yearly.csv"],
        "q4": ["fig_q4_por.png", "fig_q4_stress.png", "q4_ccg_log.csv",
               "q4_por_curve.csv", "q4_robust_schedule.csv", "q4_rolling.csv",
               "q4_stress.csv", "q4_summary.json"],
        "q5": ["q5_key_numbers.json", "q5_report_draft.md"],
    }
    total = 0
    for q, files in expected.items():
        missing = [f for f in files if not (OUT_DIR / q / f).exists()]
        extra = [p.name for p in (OUT_DIR / q).iterdir()
                 if p.name not in files]
        total += len(list((OUT_DIR / q).iterdir()))
        check("文件", f"{q} 产物齐全且无多余", not missing and not extra,
              f"缺失{missing} 多余{extra}")
    check("文件", "输出文件总数 40", total == 40,
          f"实际 {total} 个")


def verify_q1() -> None:
    an = pd.read_csv(OUT_DIR / "q1/q1_anomalies.csv")
    check("Q1", "异常条目 = 23", len(an) == 23, f"实际 {len(an)}")
    row = an[(an["位置"] == "2025-09/A2") & (an["类型"] == "平衡残差超限")]
    check("Q1", "A2 九月平衡残差 z=32.5", len(row) == 1
          and "z=32.5" in row.iloc[0]["说明"], row.iloc[0]["说明"] if len(row) else "无")
    check("Q1", "E03 八月隐含损耗 0.175",
          any(("2025-08/E03" in str(x)) for x in an["位置"])
          and any("0.175" in str(s) for s in an["说明"]), "")
    check("Q1", "E10 受端>送端 已识别",
          ((an["类型"] == "受端>送端") & (an["位置"] == "E10")).any(), "")
    check("Q1", "A2 两套系统偏差 8.71%",
          any("8.71%" in str(s) for s in an["说明"]), "")

    s = jload("q1")
    check("Q1", "χ²/n = 0.2417", abs(s["chi2/n_obs"] - 0.2417) < 1e-4,
          str(s["chi2/n_obs"]))
    imput = s["缺失值校正插补"]
    want = {"2025-04/A7/风电发电量": 47.89, "2025-05/A4/水电发电量": 64.67,
            "2025-09/A2/工业用电": 493.56, "2025-09/A2/终端用电合计": 881.25}
    check("Q1", "4 处插补值一致", all(
        abs(imput.get(k, -1) - v) < 0.01 for k, v in want.items()),
        json.dumps(imput, ensure_ascii=False))
    eta = pd.read_csv(OUT_DIR / "q1/q1_eta.csv").set_index("通道")
    check("Q1", "E05 线损 0.020→0.01353",
          abs(eta.loc["E05", "工程线损率"] - 0.02) < 1e-9
          and abs(eta.loc["E05", "调和后估计"] - 0.01353) < 1e-4,
          f"{eta.loc['E05', '调和后估计']}")
    infl = pd.read_csv(OUT_DIR / "q1/q1_influence.csv")
    top3 = infl.head(3)["观测"].tolist()
    check("Q1", "影响度Top3 = E10送端/A5终端/A4省外输入",
          top3 == ["E10/年度送端汇总", "A5/终端用电量", "A4/省外输入电量"],
          str(top3))

    # 独立复算:调和后逐(区域,月)能量平衡恒等式
    rm = pd.read_csv(OUT_DIR / "q1/q1_reconciled_region_month.csv")
    cm = pd.read_csv(OUT_DIR / "q1/q1_reconciled_channel_month.csv")
    res_max = 0.0
    for _, r in rm.iterrows():
        i, mth = r["区域"], r["月份"]
        fin = cm[(cm["受端区域"] == i) & (cm["月份"] == mth)]["受端电量"].sum()
        fout = cm[(cm["送端区域"] == i) & (cm["月份"] == mth)]["送端电量"].sum()
        gen = sum(r[f"{s}发电量"] for s in ("火电", "水电", "风电", "光伏"))
        res = (gen + r["省外输入电量"] + fin
               - r["终端用电合计"] - fout - r["区内损耗"])
        res_max = max(res_max, abs(res))
    check("Q1", "调和数据平衡恒等式 |残差|max < 1e-4 GWh", res_max < 1e-4,
          f"{res_max:.2e}")
    check("Q1", "通道 受端≤送端 全部满足",
          bool((cm["受端电量"] <= cm["送端电量"] + 1e-9).all()), "")


def verify_q2() -> None:
    s = jload("q2")
    rho = pd.read_csv(OUT_DIR / "q2/q2_rho_annual.csv").set_index("区域")
    check("Q2", "ρ:A4 最高 0.6241 / A5 最低 0.1521",
          abs(rho.loc["A4", "2025终端碳强度"] - 0.6241) < 1e-4
          and abs(rho.loc["A5", "2025终端碳强度"] - 0.1521) < 1e-4
          and s["碳势最高区域"] == "A4" and s["碳势最低区域"] == "A5",
          f"A4={rho.loc['A4', '2025终端碳强度']}, A5={rho.loc['A5', '2025终端碳强度']}")
    resp = pd.read_csv(OUT_DIR / "q2/q2_responsibility.csv").set_index("区域")
    tP, tC = resp["扩展生产责任P+"].sum(), resp["消费责任全口径C+"].sum()
    check("Q2", "责任守恒 ΣP+ ≈ ΣC+(CSV 两位小数合计差 ≤ 0.02 kt)",
          abs(tP - tC) <= 0.02, f"P+={tP:.3f}, C+={tC:.3f}")
    check("Q2", "summary 未舍入相对误差 < 1e-5",
          float(s["责任守恒相对误差"]) < 1e-5, str(s["责任守恒相对误差"]))
    ratio = resp.loc["A3", "消费责任全口径C+"] / resp.loc["A3", "扩展生产责任P+"]
    check("Q2", "A3 消费/生产责任比 = 5.36", abs(ratio - 5.36) < 0.01,
          f"实际 {ratio:.2f}")
    lam = resp["共担责任(λ=0.5)"]
    expect = (0.5 * (resp["扩展生产责任P+"] + resp["消费责任全口径C+"])).round(2)
    check("Q2", "λ=0.5 共担列 = round(0.5(P+ + C+), 2)",
          np.allclose(lam, expect, atol=1e-9), "")
    ish = pd.read_csv(OUT_DIR / "q2/q2_import_share.csv").set_index("区域")
    tot = ish.sum(axis=1)
    check("Q2", "省外输入份额 A1 69.43%/A6 71.27%/A3 48.47%",
          abs(tot["A1"] - 0.6943) < 1e-3 and abs(tot["A6"] - 0.7127) < 1e-3
          and abs(tot["A3"] - 0.4847) < 1e-3,
          f"A1={tot['A1']:.4f}, A6={tot['A6']:.4f}, A3={tot['A3']:.4f}")
    check("Q2", "A3 经 A4 接入占消费 46.99%",
          abs(ish.loc["A3", "来自A4省外输入"] - 0.4699) < 1e-3,
          f"{ish.loc['A3', '来自A4省外输入']:.4f}")
    mix = pd.read_csv(OUT_DIR / "q2/q2_origin_mix_annual.csv")
    rs = mix[["火电", "水电", "风电", "光伏", "省外输入"]].sum(axis=1)
    check("Q2", "五类来源占比行和 = 1", bool(np.allclose(rs, 1, atol=1e-6)), "")


def verify_q3() -> None:
    s = jload("q3")
    check("Q3", "总投资 985.5 / 预算罚 913.7 / 目标 1923.0",
          abs(s["总投资_百万元"] - 985.5) < 0.1
          and abs(s["区域预算超额罚_百万元"] - 913.7) < 0.1
          and abs(s["目标函数_百万元"] - 1923.0) < 0.1,
          json.dumps({k: s[k] for k in ("总投资_百万元", "区域预算超额罚_百万元",
                                        "目标函数_百万元")}, ensure_ascii=False))
    check("Q3", "入选 7 项目 / 无通道升级 / 全部达标",
          s["入选项目数"] == 7 and s["通道升级"] == [] and s["碳排放全部达标"],
          "")
    y = pd.read_csv(OUT_DIR / "q3/q3_yearly.csv").set_index("年份")
    check("Q3", "碳裕度 {325.4, 56.0, 3.1, 0.0, 0.0}",
          np.allclose(y["碳裕度_kt"], [325.4, 56.0, 3.1, 0.0, 0.0], atol=0.1),
          str(y["碳裕度_kt"].tolist()))
    check("Q3", "全部年份 E ≤ 上限", bool((y["碳裕度_kt"] >= -1e-6).all()), "")
    sp = pd.read_csv(OUT_DIR / "q3/q3_shadow_prices.csv").set_index("年份")
    check("Q3", "影子价格 2029=0.6023, 2030=3.162",
          abs(sp.loc[2029, "影子价格_百万元每kt"] - 0.6023) < 1e-3
          and abs(sp.loc[2030, "影子价格_百万元每kt"] - 3.162) < 1e-3,
          str(sp["影子价格_百万元每kt"].tolist()))
    sen = pd.read_csv(OUT_DIR / "q3/q3_sensitivity.csv")
    tight = sen[sen["碳上限倍数"] == 0.97]
    base = sen[sen["碳上限倍数"] == 1.00]
    loose = sen[sen["碳上限倍数"] == 1.03]
    check("Q3", "碳上限×0.97 全部不可行(NaN)",
          bool(tight["总成本_百万元"].isna().all()), "")
    check("Q3", "碳上限×1.0 各投资档 Jaccard=1 且成本同 1923.0",
          bool((base["Jaccard"] == 1.0).all())
          and np.allclose(base["总成本_百万元"], 1923.0, atol=0.1), "")
    check("Q3", "碳上限×1.03 Jaccard=0(方案重构)",
          bool((loose["Jaccard"] == 0.0).all()), "")
    merit = pd.read_csv(OUT_DIR / "q3/q3_merit_order.csv")
    top3 = merit.head(3)
    check("Q3", "merit Top3 均为交通电气化(A4/A6/A8)",
          set(top3["区域"]) == {"A4", "A6", "A8"}
          and (top3["名称"] == "交通工具电气化").all(), str(top3["项目"].tolist()))
    first_of = merit.drop_duplicates("名称")["名称"].tolist()
    check("Q3", "类别顺序 交通→光伏→节能", first_of[0] == "交通工具电气化"
          and first_of[1] == "分布式光伏建设", str(first_of))
    sched = pd.read_csv(OUT_DIR / "q3/q3_schedule.csv")
    check("Q3", "2026 年投资 537.83",
          abs(sched[sched["开工年"] == 2026]["投资_百万元"].sum() - 537.83) < 0.1,
          f"{sched[sched['开工年'] == 2026]['投资_百万元'].sum():.2f}")


def verify_q4() -> None:
    st = pd.read_csv(OUT_DIR / "q4/q4_stress.csv")
    s3 = st[st["情景"] == "S3"].set_index("年份")
    check("Q4", "S3 越限 {195.4, 338.5, 454.5}",
          np.allclose(s3["越限_kt"], [195.4, 338.5, 454.5], atol=0.1),
          str(s3["越限_kt"].tolist()))
    wc = st[st["情景"] == "预算集最坏"].set_index("年份")
    check("Q4", "预算集最坏 {244.2, 394.2, 487.0}",
          np.allclose(wc["越限_kt"], [244.2, 394.2, 487.0], atol=0.1),
          str(wc["越限_kt"].tolist()))
    s01 = st[st["情景"].isin(["S0", "S1"])]
    check("Q4", "S0/S1 零越限", bool((s01["越限_kt"] == 0).all()), "")

    por = pd.read_csv(OUT_DIR / "q4/q4_por_curve.csv").set_index("Gamma缩放")
    check("Q4", "POR:τ=0 投资985.5/越限1125.46;τ=1 投资4848.8/越限18.17",
          abs(por.loc[0.0, "投资_百万元"] - 985.5) < 0.1
          and abs(por.loc[0.0, "最坏情景总越限_kt"] - 1125.46) < 0.1
          and abs(por.loc[1.0, "投资_百万元"] - 4848.8) < 0.1
          and abs(por.loc[1.0, "最坏情景总越限_kt"] - 18.17) < 0.1, "")
    s4 = jload("q4")
    check("Q4", "鲁棒溢价 3863.3", abs(s4["鲁棒溢价_百万元"] - 3863.3) < 0.1,
          str(s4["鲁棒溢价_百万元"]))
    ccg = pd.read_csv(OUT_DIR / "q4/q4_ccg_log.csv")
    check("Q4", "C&CG 两轮收敛 [5251.5, 6522.4],情景数 2",
          len(ccg) == 2 and abs(ccg.iloc[1]["目标值_百万元"] - 6522.4) < 0.1
          and int(ccg.iloc[-1]["情景数"]) == 2, ccg.to_json())
    roll = pd.read_csv(OUT_DIR / "q4/q4_rolling.csv")
    viol_cols = [c for c in roll.columns if c.startswith("越限")]
    check("Q4", "稳健滚动三年零越限", bool((roll[viol_cols] == 0).all().all()),
          str(roll[viol_cols].to_numpy().tolist()))
    check("Q4", "滚动剩余成本 6130.6→5614.0",
          abs(roll.iloc[0]["剩余期目标_百万元"] - 6130.6) < 0.1
          and abs(roll.iloc[-1]["剩余期目标_百万元"] - 5614.0) < 0.1,
          str(roll["剩余期目标_百万元"].tolist()))

    # 独立复算:S3-2030 压力值(从 Q2/Q3 上游文件 + 附件重算,不经 Q4 代码)
    reg = pd.read_csv(OUT_DIR / "q3/q3_regional.csv")
    reg30 = reg[reg["年份"] == 2030].set_index("区域")
    ish = pd.read_csv(OUT_DIR / "q2/q2_import_share.csv").set_index("区域")
    ps = data_io.load_power_structure().set_index("区域")
    con = data_io.load_annual_constraints().set_index("年份")
    sc = data_io.load_scenarios()
    s3_2030 = sc[(sc["情景编号"] == "S3") & (sc["年份"] == 2030)].iloc[0]
    kappa = float(con.loc[2030, "基准供电碳强度调整系数(相对2025)"])
    dE = 0.0
    for j in REGIONS:
        W_j = sum((reg30.loc[i, "净需求_GWh"] - reg30.loc[i, "光伏供电_GWh"])
                  * ish.loc[i, f"来自{j}省外输入"] for i in REGIONS)
        dE += kappa * float(ps.loc[j, "省外输入排放因子"]) \
            * (float(s3_2030[j]) - 1.0) * W_j
    E = reg30["消费碳_kt"].sum() + dE
    claimed = float(s3.loc[2030, "碳排放_kt"])
    check("Q4", "S3-2030 压力值独立复算一致", abs(E - claimed) < 0.5,
          f"复算 {E:.1f} vs 产物 {claimed:.1f}")


def verify_q5_and_global() -> None:
    txt = (OUT_DIR / "q5/q5_report_draft.md").read_text(encoding="utf-8")
    n = sum(1 for c in txt if not c.isspace())
    check("Q5", "报告字数约 1000(900–1200,不含空白)", 900 <= n <= 1200,
          f"实际 {n}")
    with open(OUT_DIR / "q5/q5_key_numbers.json", encoding="utf-8") as f:
        k = json.load(f)
    needles = (f"{k['q3_总投资']:.1f}", f"{k['q4_S3_2030越限']:.1f}",
               f"{k['q4_鲁棒溢价']:.1f}", f"{k['q4_滚动初期目标']:.1f}")
    check("Q5", "报告引用投资/越限/溢价/滚动成本与上游精确值一致",
          all(x in txt for x in needles)
          and abs(k["q3_总投资"] - 985.5) < 0.1
          and abs(k["q4_S3_2030越限"] - 454.5) < 0.1
          and abs(k["q4_滚动初期目标"] - 6130.6) < 0.1, str(needles))

    import re
    bib = (OUT_DIR.parents[0] / ".." / "references" / "problem-B"
           / "refs.bib").resolve().read_text(encoding="utf-8")
    n_bib = len(re.findall(r"^@", bib, flags=re.M))
    check("全局", "refs.bib 52 条", n_bib == 52, f"实际 {n_bib}")

    eta_ch = {e for e in CHANNELS}
    check("全局", "通道集合完整(E01–E11)", len(eta_ch) == 11, "")


def main() -> None:
    verify_files()
    verify_q1()
    verify_q2()
    verify_q3()
    verify_q4()
    verify_q5_and_global()
    df = pd.DataFrame(RESULTS, columns=["模块", "声明", "通过", "备注"])
    df["通过"] = df["通过"].map({True: "PASS", False: "FAIL"})
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 70)
    print(df.to_string(index=False))
    n_fail = (df["通过"] == "FAIL").sum()
    print(f"\n共 {len(df)} 项核查,FAIL {n_fail} 项")


if __name__ == "__main__":
    main()
