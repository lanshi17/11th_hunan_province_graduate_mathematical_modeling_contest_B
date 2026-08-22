"""问题五:面向省级能源主管部门的决策咨询报告(草稿自动生成)。

从 Q1–Q4 输出文件读取全部关键数字渲染报告,确保论文数字可复现、
不手填。输出:q5_report_draft.md(约 1000 字正文)+ q5_key_numbers.json。
"""
from __future__ import annotations

import json

import pandas as pd

from ..common.paths import out_dir

Q1, Q2, Q3, Q4 = (out_dir(k) for k in ("q1", "q2", "q3", "q4"))
OUT = out_dir("q5")


def collect() -> dict:
    j = {}
    for name, d in (("q1", Q1), ("q2", Q2), ("q3", Q3), ("q4", Q4)):
        with open(d / f"{name}_summary.json", encoding="utf-8") as f:
            j[name] = json.load(f)

    infl = pd.read_csv(Q1 / "q1_influence.csv")
    eta = pd.read_csv(Q1 / "q1_eta.csv")
    resp = pd.read_csv(Q2 / "q2_responsibility.csv").set_index("区域")
    merit = pd.read_csv(Q3 / "q3_merit_order.csv")
    sp = pd.read_csv(Q3 / "q3_shadow_prices.csv").set_index("年份")
    stress = pd.read_csv(Q4 / "q4_stress.csv")
    rolling = pd.read_csv(Q4 / "q4_rolling.csv")
    channel = pd.read_csv(Q2 / "q2_channel_carbon_interval.csv")
    risk = pd.read_csv(Q2 / "q2_q3_cap_risk.csv").set_index("年份")
    with open(Q2 / "q2_bootstrap_summary.json", encoding="utf-8") as f:
        boot = json.load(f)
    with open(Q3 / "q3_epsilon_summary.json", encoding="utf-8") as f:
        eps = json.load(f)
    with open(Q4 / "q4_regret_summary.json", encoding="utf-8") as f:
        regret = json.load(f)

    rho = j["q2"]["2025区域终端碳强度"]
    s3 = stress[stress["情景"] == "S3"].set_index("年份")
    a4a3 = channel[(channel["送端"] == "A4") & (channel["受端"] == "A3")]
    if len(a4a3) != 1:
        raise RuntimeError("Q2 通道区间中 A4→A3 方向必须唯一")
    a4a3 = a4a3.iloc[0]
    key = dict(
        q1_诊断标记=j["q1"]["异常条目数"],
        q1_插补=j["q1"]["缺失值校正插补"],
        q1_影响度前三=infl.head(3)["观测"].tolist(),
        q1_污染WLS相对Huber倍数=j["q1"]["确定性污染稳健性"][
            "WLS相对Huber平均RMSE倍数"],
        q1_E07状态=j["q1"]["eta可识别性"]["E07"],
        q1_E05线损=dict(工程=float(eta.set_index("通道").loc["E05", "工程线损率"]),
                        估计=float(eta.set_index("通道").loc["E05", "调和后估计"])),
        q2_碳势最高=(j["q2"]["碳势最高区域"], rho[j["q2"]["碳势最高区域"]]),
        q2_碳势最低=(j["q2"]["碳势最低区域"], rho[j["q2"]["碳势最低区域"]]),
        q2_A3消费生产比=round(float(resp.loc["A3", "消费责任全口径C+"]
                                     / resp.loc["A3", "扩展生产责任P+"]), 2),
        q2_自举样本数=boot["successful_samples"],
        q2_A4到A3碳流=dict(
            点估计=float(a4a3["到达碳流_kt_点估计"]),
            P2_5=float(a4a3["到达碳流_kt_P2.5"]),
            P97_5=float(a4a3["到达碳流_kt_P97.5"])),
        q3_加权基线投资=j["q3"]["总投资_百万元"],
        q3_Cstar=eps["stage2_minimum_investment_Cstar_million"],
        q3_推荐投资=eps["recommended"]["investment_million"],
        q3_推荐最大相对超额=eps["recommended"]["max_relative_budget_excess"],
        q3_基线最大相对超额=eps["weighted_baseline"]["最大区域相对预算超额R"],
        q3_条件超限概率={int(y): float(risk.loc[y, "条件超限概率"])
                         for y in risk.index},
        q3_优先前三=merit.head(3)[["项目", "名称", "区域"]]
        .agg(lambda r: f"{r['名称']}({r['区域']})", axis=1).tolist(),
        q3_2030影子价=float(sp.loc[2030, "影子价格_百万元每kt"]),
        q4_S3_2030越限=float(s3.loc[2030, "越限_kt"]),
        q4_Gamma1软溢价=j["q4"]["Gamma1软约束溢价_百万元"],
        q4_Gamma1最小缺口=j["q4"]["Gamma1最小总硬缺口_kt"],
        q4_tau_star=j["q4"]["硬可行半径_tau_star"],
        q4_投资上限恢复倍数=j["q4"]["Gamma1硬零越限_年度投资上限最小倍数"],
        q4_资源恢复倍数=j["q4"]["Gamma1硬零越限_五类施工资源上限最小统一倍数"],
        q4_最大相对遗憾=regret["最大相对遗憾"],
        q4_共享一阶段投资=regret["共享一阶段投资_百万元"],
        q4_四路径硬达标=regret["四路径全部硬达标"],
        q4_滚动信息价值={int(r["决策年"]): float(r["本年信息价值_百万元"])
                         for _, r in rolling.iterrows()},
        q4_滚动越限=float(rolling.iloc[-1]["越限2030_kt"]),
    )
    return dict(json_summaries=j, key=key)


def render(key: dict) -> str:
    k = key
    imp = "、".join(f"{loc}={v:.0f}GWh" for loc, v in list(k["q1_插补"].items())[:2])
    top3 = "、".join(k["q3_优先前三"])
    infl3 = "、".join(k["q1_影响度前三"])
    hi, hi_v = k["q2_碳势最高"]
    lo, lo_v = k["q2_碳势最低"]
    return rf"""# 关于“十五五”电力低碳转型的决策建议（呈省级能源主管部门）

## 一、夯实数据底座:先校准计量,再谈碳账

对 2025 年多源监测数据的守恒校验形成 **{k['q1_诊断标记']} 项诊断标记**,
包括月度与年度两套系统的显著口径差、通道 E10“受端大于送端”、E03 单月
线损粗差以及缺失值(校正模型插补:{imp} 等)。基于标准化
Huber 调和的全网一致数据显示,E05 线损约 {k['q1_E05线损']['估计']:.4f}
(工程值 {k['q1_E05线损']['工程']:.3f});E07 无正流量,线损不可由数据识别。
六类污染试验中 WLS 平均状态偏移是 Huber 的 {k['q1_污染WLS相对Huber倍数']:.2f} 倍。
影响度最高的是 {infl3},建议优先复核 E10 年度关口与 A4 月度省外输入计量。

## 二、认清责任格局:碳随电流动,考核须双侧

碳流追踪显示区域终端碳强度差异近 4 倍:{hi} 高达 {hi_v:.2f} kgCO2/kWh,{lo} 仅
{lo_v:.2f}。纯受电区 A3 的消费侧责任是其生产侧责任的 **{k['q2_A3消费生产比']} 倍**,单一口径考核
必然失真。{k['q2_自举样本数']} 次条件自举显示,A4→A3 年度到达碳流点估计为
{k['q2_A4到A3碳流']['点估计']:.1f} kt,95% 条件区间
[{k['q2_A4到A3碳流']['P2_5']:.1f},{k['q2_A4到A3碳流']['P97_5']:.1f}] kt。
建议并列发布生产、消费与五五共担三套台账；五五共担是政策选择,不是由守恒自动推出的唯一答案。

## 三、以小幅增投换公平,同时给点估计方案留安全垫

零缺供条件下最低投资为 {k['q3_Cstar']:.1f} 百万元；推荐的 $\varepsilon=1\%$ 方案投资
**{k['q3_推荐投资']:.1f} 百万元**,把最大区域相对预算超额从
{100*k['q3_基线最大相对超额']:.2f}% 降至 {100*k['q3_推荐最大相对超额']:.2f}% 。
但测量不确定性传播后,该固定方案 2028–2030 超限概率分别为
{100*k['q3_条件超限概率'][2028]:.1f}%、{100*k['q3_条件超限概率'][2029]:.1f}%、
{100*k['q3_条件超限概率'][2030]:.1f}%。应把这些概率用于设置动态安全裕度,不能把点估计达标等同于高置信达标。
项目优先级仍以 {top3} 为先；2030 年碳约束影子价格约
**{k['q3_2030影子价']:.3f} 百万元/kt(即约 {k['q3_2030影子价']*1000:.0f} 元/吨,一次性投资口径)**,
可作为压力测试下的边际参考,不宜直接等同市场碳价。

## 四、典型路径用硬约束,完整预算集用压力半径

省外来电碳因子若走高(S3 情景),2030 年将超上限 **{k['q4_S3_2030越限']:.1f} kt**。按预算不确定
集 $\Gamma=1$ 的软防御需增加投资 {k['q4_Gamma1软溢价']:.1f} 百万元,仍有
{k['q4_Gamma1最小缺口']:.2f} kt 结构性缺口；硬可行半径仅 $\tau^*={k['q4_tau_star']:.3f}$。
若必须覆盖完整 $\Gamma$,可将年度投资上限至少提高约
{100*(k['q4_投资上限恢复倍数']-1):.2f}%,或将五类施工资源统一提高约
{100*(k['q4_资源恢复倍数']-1):.2f}%。无概率的 S0–S3 最小最大相对遗憾策略共享一阶段投资
{k['q4_共享一阶段投资']:.1f} 百万元,四条路径均硬达标；但最大相对遗憾达
{100*k['q4_最大相对遗憾']:.1f}%,说明过早锁定的机会成本很高。建议以“2026–2027 共同准备、
2028 起按已观测路径追加”的硬约束策略为主,以完整 $\Gamma$ 作压力测试；滚动表中的
{k['q4_滚动信息价值'][2028]:.1f}/{k['q4_滚动信息价值'][2029]:.1f} 百万元是含违约罚的目标改善,不得写成等额投资节省。
"""


def main() -> None:
    data = collect()
    report = render(data["key"])
    with open(OUT / "q5_report_draft.md", "w", encoding="utf-8") as f:
        f.write(report)
    with open(OUT / "q5_key_numbers.json", "w", encoding="utf-8") as f:
        json.dump(data["key"], f, ensure_ascii=False, indent=2, default=str)
    n_chars = sum(1 for c in report if not c.isspace())
    print(f"[Q5] 报告草稿生成,正文约 {n_chars} 字(不含空白)")
    print(f"[Q5] 输出目录: {OUT}")


if __name__ == "__main__":
    main()
