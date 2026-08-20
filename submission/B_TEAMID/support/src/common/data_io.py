"""B 题附件数据加载器。

所有 CSV 均为「标题行 + 表头 + 数据 + 尾注」结构,加载时跳过标题、
过滤空行与"说明"尾注。数值列统一转 float,单位 GWh(除注明外)。
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .paths import DATA_DIR, REGIONS

_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _read(name: str, skiprows: int) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, skiprows=skiprows, encoding="utf-8-sig")


def load_monthly_region() -> pd.DataFrame:
    """附件1A:8 区域 × 12 月监测(含缺失)。96 行。"""
    df = _read("附件1_A_区域月度监测.csv", skiprows=1)
    df = df[df["月份"].astype(str).str.match(_MONTH_RE)].copy()
    num_cols = [c for c in df.columns if c not in ("月份", "区域", "区域类型")]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    return df.reset_index(drop=True)


def load_monthly_channel() -> pd.DataFrame:
    """附件1B:通道月度监测。132 行(11 通道 × 12 月,方向随月份可变)。"""
    df = _read("附件1_B_通道月度监测.csv", skiprows=1)
    df = df[df["月份"].astype(str).str.match(_MONTH_RE)].copy()
    for c in ("送端计量电量", "受端计量电量", "通道月度容量上限"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.reset_index(drop=True)


def load_annual_summary() -> pd.DataFrame:
    """附件2A:年度汇总系统。8 行。"""
    df = _read("附件2_A_年度汇总.csv", skiprows=2)
    df = df[df["区域"].isin(REGIONS)].copy()
    num_cols = ["本地发电量", "省外输入电量", "终端用电量", "工业用电量"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    return df.reset_index(drop=True)


def load_aux_monitor() -> tuple[pd.DataFrame, pd.DataFrame]:
    """附件2B:上段变电站/重点企业(32 行),下段通道年度汇总(11 行)。"""
    raw = pd.read_csv(DATA_DIR / "附件2_B_辅助监测.csv", header=None,
                      encoding="utf-8-sig")
    header2 = raw.index[raw[0] == "通道编号"][0]

    top = raw.iloc[3:].copy()
    top = top[top[0].astype(str).str.match(r"^[TK]-A\d")]
    top.columns = ["监测点编号", "区域", "指标", "数值", "单位", "年份"]
    top["数值"] = pd.to_numeric(top["数值"], errors="coerce")

    bot = raw.iloc[header2 + 1:].copy()
    bot = bot[bot[0].astype(str).str.match(r"^E\d{2}$")]
    bot.columns = ["通道编号", "连接区域1", "连接区域2",
                   "年度送端汇总", "年度受端汇总", "工程记录线损率"]
    for c in ("年度送端汇总", "年度受端汇总", "工程记录线损率"):
        bot[c] = pd.to_numeric(bot[c], errors="coerce")
    return top.reset_index(drop=True), bot.reset_index(drop=True)


def load_emission_factors() -> tuple[dict[str, float], dict[str, float]]:
    """附件3A → (本地电源因子 dict, 分区域省外输入因子 dict),kgCO2/kWh。"""
    df = _read("附件3_A_排放因子.csv", skiprows=2)
    df = df[df["类别"].notna()].copy()
    df["排放因子"] = pd.to_numeric(df["排放因子"], errors="coerce")
    local = df[df["类别"] == "本地电源"].set_index("对象")["排放因子"].to_dict()
    ext = df[df["类别"] == "省外输入"].set_index("对象")["排放因子"].to_dict()
    return local, ext


def load_power_structure() -> pd.DataFrame:
    """附件3B:2025 电源规模、省外输入年容量上限与因子。8 行。"""
    df = _read("附件3_B_区域电源结构.csv", skiprows=2)
    df = df[df["区域"].isin(REGIONS)].copy()
    num_cols = [c for c in df.columns if c not in ("区域", "区域类型")]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    return df.reset_index(drop=True)


def load_network() -> pd.DataFrame:
    """附件3C:11 条双向通道(工程连接、参考线损率、月度基准容量)。"""
    df = _read("附件3_C_网络连接.csv", skiprows=2)
    df = df[df["通道编号"].astype(str).str.match(r"^E\d{2}$")].copy()
    for c in ("工程参考线损率", "月度基准容量"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.reset_index(drop=True)


def load_region_development() -> pd.DataFrame:
    """附件4A:区域发展参数。8 行。"""
    df = _read("附件4_A_区域发展参数.csv", skiprows=1)
    df = df[df["区域"].isin(REGIONS)].copy()
    num_cols = [c for c in df.columns if c not in ("区域", "区域类型")]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    return df.reset_index(drop=True)


def load_annual_constraints() -> pd.DataFrame:
    """附件4B:2026–2030 年度双控约束。5 行。"""
    df = _read("附件4_B_年度双控约束.csv", skiprows=1)
    df = df[pd.to_numeric(df["年份"], errors="coerce").notna()].copy()
    df = df.apply(pd.to_numeric, errors="coerce")
    df["年份"] = df["年份"].astype(int)
    return df.reset_index(drop=True)


def load_projects() -> pd.DataFrame:
    """附件5A:候选项目库 P01–P35。"""
    df = _read("附件5_A_候选项目库.csv", skiprows=1)
    df = df[df["项目编号"].astype(str).str.match(r"^P\d{2}$")].copy()
    text_cols = ("项目编号", "区域/位置", "项目名称", "规模单位", "施工资源类型")
    num_cols = [c for c in df.columns if c not in text_cols]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    return df.reset_index(drop=True)


def load_project_relations() -> pd.DataFrame:
    """附件5B:协同/互斥关系。6 行。"""
    df = _read("附件5_B_项目关系.csv", skiprows=1)
    df = df[df["关系编号"].astype(str).str.contains("-", na=False)].copy()
    return df.reset_index(drop=True)


def load_resource_limits() -> pd.DataFrame:
    """附件5C:年度施工资源与投资上限。5 行。"""
    df = _read("附件5_C_年度资源上限.csv", skiprows=1)
    df = df[pd.to_numeric(df["年份"], errors="coerce").notna()].copy()
    df = df.apply(pd.to_numeric, errors="coerce")
    df["年份"] = df["年份"].astype(int)
    return df.reset_index(drop=True)


def load_uncertainty() -> tuple[pd.DataFrame, dict[int, float]]:
    """附件6A → (ξ 区间表, 年度预算 Γ dict)。"""
    raw = pd.read_csv(DATA_DIR / "附件6_A_送端碳因子区间.csv", skiprows=1,
                      encoding="utf-8-sig")
    main = raw[raw["区域"].isin(REGIONS)].copy()
    main = main[["年份", "区域", "偏离系数下界", "基准值", "偏离系数上界"]]
    main = main.apply(lambda s: pd.to_numeric(s, errors="coerce")
                      if s.name != "区域" else s)
    main["年份"] = main["年份"].astype(int)

    gcols = raw.columns[-2:]
    g = raw[gcols].dropna()
    gamma = {int(float(y)): float(v) for y, v in zip(g.iloc[:, 0], g.iloc[:, 1])}
    return main.reset_index(drop=True), gamma


def load_scenarios() -> pd.DataFrame:
    """附件6B:典型情景 S0–S3 逐年 ξ 乘数。12 行。"""
    df = _read("附件6_B_典型情景.csv", skiprows=1)
    df = df[df["情景编号"].astype(str).str.match(r"^S\d$")].copy()
    df["年份"] = pd.to_numeric(df["年份"], errors="coerce").astype(int)
    df[REGIONS] = df[REGIONS].apply(pd.to_numeric, errors="coerce")
    return df.reset_index(drop=True)


def _selftest() -> None:
    mr = load_monthly_region()
    mc = load_monthly_channel()
    ann = load_annual_summary()
    aux_top, aux_ch = load_aux_monitor()
    ef_local, ef_ext = load_emission_factors()
    ps = load_power_structure()
    net = load_network()
    dev = load_region_development()
    con = load_annual_constraints()
    prj = load_projects()
    rel = load_project_relations()
    res = load_resource_limits()
    unc, gamma = load_uncertainty()
    sc = load_scenarios()

    assert mr.shape[0] == 96, mr.shape
    assert mc.shape[0] == 132, mc.shape
    assert ann.shape[0] == 8
    assert aux_top.shape[0] == 32 and aux_ch.shape[0] == 11
    assert set(ef_local) == {"火电", "水电", "风电", "光伏"}
    assert len(ef_ext) == 8
    assert ps.shape[0] == 8 and net.shape[0] == 11
    assert dev.shape[0] == 8 and con.shape[0] == 5
    assert prj.shape[0] == 35 and rel.shape[0] == 6 and res.shape[0] == 5
    assert unc.shape[0] == 24 and gamma == {2028: 2.0, 2029: 2.5, 2030: 3.0}
    assert sc.shape[0] == 12
    n_missing = int(mr.isna().sum().sum())
    print(f"selftest OK | 附件1A 缺失单元格: {n_missing}")
    print(mr[mr.isna().any(axis=1)][["月份", "区域"]].to_string(index=False))


if __name__ == "__main__":
    _selftest()
