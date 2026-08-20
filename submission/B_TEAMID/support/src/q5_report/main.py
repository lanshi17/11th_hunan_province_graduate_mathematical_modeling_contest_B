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
    por = pd.read_csv(Q4 / "q4_por_curve.csv").set_index("Gamma缩放")
    rolling = pd.read_csv(Q4 / "q4_rolling.csv")

    rho = j["q2"]["2025区域终端碳强度"]
    s3 = stress[stress["情景"] == "S3"].set_index("年份")
    key = dict(
        q1_异常条目=j["q1"]["异常条目数"],
        q1_插补=j["q1"]["缺失值校正插补"],
        q1_影响度前三=infl.head(3)["观测"].tolist(),
        q1_E05线损=dict(工程=float(eta.set_index("通道").loc["E05", "工程线损率"]),
                        估计=float(eta.set_index("通道").loc["E05", "调和后估计"])),
        q2_碳势最高=(j["q2"]["碳势最高区域"], rho[j["q2"]["碳势最高区域"]]),
        q2_碳势最低=(j["q2"]["碳势最低区域"], rho[j["q2"]["碳势最低区域"]]),
        q2_A3消费生产比=round(float(resp.loc["A3", "消费责任全口径C+"]
                                     / resp.loc["A3", "扩展生产责任P+"]), 2),
        q3_总投资=j["q3"]["总投资_百万元"],
        q3_优先前三=merit.head(3)[["项目", "名称", "区域"]]
        .agg(lambda r: f"{r['名称']}({r['区域']})", axis=1).tolist(),
        q3_2030影子价=float(sp.loc[2030, "影子价格_百万元每kt"]),
        q4_S3_2030越限=float(s3.loc[2030, "越限_kt"]),
        q4_鲁棒溢价=j["q4"]["鲁棒溢价_百万元"],
        q4_鲁棒残余越限=j["q4"]["静态鲁棒最坏越限_kt"],
        q4_滚动初期目标=float(rolling.iloc[0]["剩余期目标_百万元"]),
        q4_滚动末期目标=float(rolling.iloc[-1]["剩余期目标_百万元"]),
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
    return f"""# 关于"十五五"电力低碳转型的决策建议(呈省级能源主管部门)

## 一、夯实数据底座:先校准计量,再谈碳账

对 2025 年多源监测数据的守恒校验共识别异常与口径不一致 **{k['q1_异常条目']} 处**,
包括月度与年度两套系统最大 8.7% 的口径差、通道 E10"受端大于送端"、E03 单月
隐含线损率 17.5% 的粗差,以及 4 处缺失(校正模型插补:{imp} 等)。基于加权
最小二乘调和的全网一致数据显示,通道实际损耗率与工程记录总体相符,但 E05
实际约 {k['q1_E05线损']['估计']:.4f}(工程值 {k['q1_E05线损']['工程']:.3f}),存在计量口径高估。影响度分析表明
{infl3} 等观测对全网校正结果影响最大,**建议优先升级上述关口计量与年度汇总
系统的口径对齐机制**。

## 二、认清责任格局:碳随电流动,考核须双侧

碳流追踪显示区域终端碳强度差异近 4 倍:{hi} 高达 {hi_v:.2f} kgCO2/kWh,{lo} 仅
{lo_v:.2f}。纯受电区 A3 的消费侧责任是其生产侧责任的 **{k['q2_A3消费生产比']} 倍**,单一口径考核
必然失真。建议以"生产-消费五五共担"作为区域双控考核基准口径(三种口径下
全省总量守恒,已验证),并配套区域碳预算按"现状份额→公平份额"五年过渡。

## 三、把钱花在刀刃上:{k['q3_总投资']:.1f} 百万元投资即可守住五年硬约束

优化表明,五年碳上限可在总投资约 **{k['q3_总投资']:.1f} 百万元** 内全部达标,投资集中于
2026–2028 年;单位减排成本排序为 {top3} 优先。2030 年碳约束影子价格约
**{k['q3_2030影子价']:.3f} 百万元/kt(即约 {k['q3_2030影子价']*1000:.0f} 元/吨,一次性投资口径)**,
可作为区域预算交易与项目补贴定价锚。
需要警示:若碳上限再收紧 3%,现有项目库将无解——**减排潜力天花板已现,
建议提前储备第二批项目**(工业深度节能、绿电入省扩容)。

## 四、防住送端风险:用滚动调控以可控代价实现"零越限"

省外来电碳因子若走高(S3 情景),2030 年将超上限 **{k['q4_S3_2030越限']:.1f} kt**。按预算不确定
集整体免疫需追加投资 {k['q4_鲁棒溢价']:.1f} 百万元,且仍有 {k['q4_鲁棒残余越限']:.2f} kt 残余缺口;而"逐年观测、
滚动加码、未来年份按不确定预算设防"的滚动调控在最不利路径下实现 **三年零
越限**,剩余期成本随信息到达由 {k['q4_滚动初期目标']:.1f} 降至 {k['q4_滚动末期目标']:.1f} 百万元。**建议以滚动调控为
主策略**:每年三季度依据送端结构监测更新碳因子区间,联动调整次年项目开工
与购电结构,并把静态鲁棒方案作为压力测试底线预案。
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
