"""问题二:区域电力碳流追踪与碳排放责任分担。

方法:比例共享原则下的电力碳排放流模型(Bialek 1996; Kang et al. 2012/2015),
核心量为节点碳势 ρ_{i,t}:节点入流碳量守恒、出流按同一碳势混合,逐月解
8 维线性方程组。责任核算:生产侧 / 消费侧(Peters 2008; Davis & Caldeira
2010)与 λ-加权共担(Gallego & Lenzen 2005; Lenzen et al. 2007),并按
"责任守恒"公理数值校验。

线损碳排口径:主口径"送端承担"(受端仅承接到达电量携带的碳,通道损耗碳
计入送端台账);备选口径"受端承担"做敏感性。

单位:电量 GWh,因子 kgCO2/kWh,碳量 GWh×kg/kWh = ktCO2。
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from ..common import data_io
from ..common.paths import MONTHS, REGIONS, SECTORS, SOURCES, out_dir
from ..common.plotting import setup as plot_setup

Q1 = out_dir("q1")
OUT = out_dir("q2")

GEN_COLS = [f"{s}发电量" for s in SOURCES]
ORIGIN_CLASSES = SOURCES + ["省外输入"]


def load_inputs():
    rm = pd.read_csv(Q1 / "q1_reconciled_region_month.csv")
    cm = pd.read_csv(Q1 / "q1_reconciled_channel_month.csv")
    ef_local, ef_ext = data_io.load_emission_factors()
    return rm, cm, ef_local, ef_ext


def solve_month(rm_t: pd.DataFrame, cm_t: pd.DataFrame,
                ef_local: dict, ef_ext: dict,
                loss_carbon: str = "sender"):
    """单月节点碳势与来源分解。

    返回 (rho[8], mix[8×5 来源能量占比], Q[8 总入流能量])。
    """
    idx = {r: i for i, r in enumerate(REGIONS)}
    g = rm_t.set_index("区域")
    G = g[GEN_COLS].to_numpy(float)                 # (8,4)
    imp = g["省外输入电量"].to_numpy(float)          # (8,)

    inflow = np.zeros((8, 8))                       # inflow[i,j]: j→i 能量
    carried = np.zeros((8, 8))                      # 碳随电量口径
    for _, row in cm_t.iterrows():
        i, j = idx[row["受端区域"]], idx[row["送端区域"]]
        recv, sent = row["受端电量"], row["送端电量"]
        inflow[i, j] += recv
        carried[i, j] += recv if loss_carbon == "sender" else sent

    Q = G.sum(axis=1) + imp + inflow.sum(axis=1)    # 节点总入流能量
    ef_src = np.array([ef_local[s] for s in SOURCES])
    b = G @ ef_src + imp * np.array([ef_ext[r] for r in REGIONS])

    A = np.diag(Q) - carried
    rho = np.linalg.solve(A, b)

    # 来源能量占比:同一比例共享结构,(diag(Q) − inflow)·share = B 的解
    # 即为占比(行 i:Q_i·s_i = B_i + Σ_e R_e·s_from)
    B = np.concatenate([G, imp[:, None]], axis=1)   # (8,5) 各类注入能量
    mix = np.linalg.solve(np.diag(Q) - inflow, B)

    # 省外输入按接入区域细分的来源占比(8 消费区 × 8 输入接入区)
    imp_share = np.linalg.solve(np.diag(Q) - inflow, np.diag(imp))
    return rho, mix, Q, imp_share


def run_tracing(rm, cm, ef_local, ef_ext, loss_carbon="sender"):
    rho_m = np.zeros((12, 8))
    mix_m = np.zeros((12, 8, 5))
    impshare_m = np.zeros((12, 8, 8))
    for t, m in enumerate(MONTHS):
        rho, mix, _, ish = solve_month(rm[rm["月份"] == m],
                                       cm[cm["月份"] == m],
                                       ef_local, ef_ext, loss_carbon)
        rho_m[t] = rho
        mix_m[t] = mix
        impshare_m[t] = ish
    return rho_m, mix_m, impshare_m


def responsibility(rm, cm, ef_local, ef_ext, rho_m) -> pd.DataFrame:
    """年度责任核算(ktCO2):生产/扩展生产/消费/消费全口径/λ共担。"""
    idx = {r: i for i, r in enumerate(REGIONS)}
    ef_src = np.array([ef_local[s] for s in SOURCES])

    P_local = np.zeros(8)
    imp_carbon = np.zeros(8)
    C_term = np.zeros(8)
    loss_carbon_in = np.zeros(8)     # 区内损耗碳
    ch_loss_carbon = np.zeros(8)     # 通道损耗碳(送端承担)
    for t, m in enumerate(MONTHS):
        g = rm[rm["月份"] == m].set_index("区域")
        G = g[GEN_COLS].to_numpy(float)
        imp = g["省外输入电量"].to_numpy(float)
        D = g["终端用电合计"].to_numpy(float)
        L = g["区内损耗"].to_numpy(float)
        P_local += G @ ef_src
        imp_carbon += imp * np.array([ef_ext[r] for r in REGIONS])
        C_term += D * rho_m[t]
        loss_carbon_in += L * rho_m[t]
        for _, row in cm[cm["月份"] == m].iterrows():
            j = idx[row["送端区域"]]
            ch_loss_carbon[j] += (row["送端电量"] - row["受端电量"]) * rho_m[t, j]

    P_plus = P_local + imp_carbon
    C_full = C_term + loss_carbon_in + ch_loss_carbon
    df = pd.DataFrame({
        "区域": REGIONS,
        "生产责任(本地发电)": P_local,
        "省外输入碳": imp_carbon,
        "扩展生产责任P+": P_plus,
        "消费责任(终端)": C_term,
        "区内损耗碳": loss_carbon_in,
        "通道损耗碳(送端)": ch_loss_carbon,
        "消费责任全口径C+": C_full,
    })
    for lam in (0.3, 0.5, 0.7):
        df[f"共担责任(λ={lam})"] = lam * P_plus + (1 - lam) * C_full
    return df


def export(rm, rho_m, rho_recv, mix_m, impshare_m, resp: pd.DataFrame) -> dict:
    rows = []
    for t, m in enumerate(MONTHS):
        for i, r in enumerate(REGIONS):
            rows.append(dict(月份=m, 区域=r,
                             节点碳势_送端口径=round(rho_m[t, i], 5),
                             节点碳势_受端口径=round(rho_recv[t, i], 5)))
    pd.DataFrame(rows).to_csv(OUT / "q2_rho_monthly.csv", index=False,
                              encoding="utf-8-sig")

    # 年度加权碳强度(供 Q3 使用)
    D = np.zeros((12, 8))
    for t, m in enumerate(MONTHS):
        D[t] = rm[rm["月份"] == m].set_index("区域")["终端用电合计"] \
            .reindex(REGIONS).to_numpy(float)
    rho_ann = (rho_m * D).sum(axis=0) / D.sum(axis=0)
    pd.DataFrame({"区域": REGIONS, "2025终端碳强度": np.round(rho_ann, 5),
                  "2025终端用电GWh": np.round(D.sum(axis=0), 1)}) \
        .to_csv(OUT / "q2_rho_annual.csv", index=False, encoding="utf-8-sig")

    # 来源结构(年度能量加权)
    Dw = D / D.sum(axis=0, keepdims=True)
    mix_ann = np.einsum("tio,ti->io", mix_m, Dw)

    # 省外输入分接入区来源份额(年度需求加权,供 Q4 送端不确定性传导)
    ish_ann = np.einsum("tij,ti->ij", impshare_m, Dw)
    ish_df = pd.DataFrame(ish_ann, columns=[f"来自{r}省外输入" for r in REGIONS])
    ish_df.insert(0, "区域", REGIONS)
    ish_df.to_csv(OUT / "q2_import_share.csv", index=False,
                  encoding="utf-8-sig")
    mix_df = pd.DataFrame(mix_ann, columns=ORIGIN_CLASSES)
    mix_df.insert(0, "区域", REGIONS)
    mix_df["本地清洁占比"] = mix_ann[:, 1:4].sum(axis=1)
    mix_df.to_csv(OUT / "q2_origin_mix_annual.csv", index=False,
                  encoding="utf-8-sig")

    # 先对原始口径四舍五入,再由舍入后的 P+/C+ 生成共担列,避免 0.5(P+C) 与表内不一致
    rounded = resp.copy()
    share_cols = [c for c in rounded.columns if str(c).startswith("共担")]
    for c in rounded.columns:
        if c != "区域" and c not in share_cols:
            rounded[c] = rounded[c].round(2)
    P_r = rounded["扩展生产责任P+"]
    C_r = rounded["消费责任全口径C+"]
    for lam in (0.3, 0.5, 0.7):
        rounded[f"共担责任(λ={lam})"] = (lam * P_r + (1 - lam) * C_r).round(2)
    rounded.to_csv(OUT / "q2_responsibility.csv", index=False,
                   encoding="utf-8-sig")

    total_P = float(resp["扩展生产责任P+"].sum())
    total_C = float(resp["消费责任全口径C+"].sum())
    rel = abs(total_P - total_C) / max(abs(total_P), 1e-12)
    i_a3, i_a4 = REGIONS.index("A3"), REGIONS.index("A4")
    a3_imp = float(ish_ann[i_a3].sum())
    a3_via_a4 = float(ish_ann[i_a3, i_a4])
    summary = {
        "全省总排放ktCO2(生产口径)": round(total_P, 2),
        "全省总排放ktCO2(消费口径)": round(total_C, 2),
        "责任守恒相对误差": float(rel),
        "CSV两位小数P+合计": round(float(P_r.sum()), 2),
        "CSV两位小数C+合计": round(float(C_r.sum()), 2),
        "A3省外输入占消费": round(a3_imp, 4),
        "A3经A4接入占消费": round(a3_via_a4, 4),
        "2025区域终端碳强度": {r: round(float(v), 4)
                               for r, v in zip(REGIONS, rho_ann)},
        "碳势最高区域": REGIONS[int(rho_ann.argmax())],
        "碳势最低区域": REGIONS[int(rho_ann.argmin())],
    }
    with open(OUT / "q2_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary


def make_plots(rho_m, rho_recv, mix_ann_path, resp) -> None:
    import matplotlib.pyplot as plt

    plot_setup()
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for i, r in enumerate(REGIONS):
        ax.plot(range(1, 13), rho_m[:, i], marker="o", ms=3, label=r)
    ax.set_xlabel("月份(2025)")
    ax.set_ylabel(r"终端用电碳强度 kgCO$_2$/kWh")
    ax.set_title("各区域逐月节点碳势(送端承担口径)")
    ax.legend(ncols=4, fontsize=8)
    fig.savefig(OUT / "fig_q2_rho_monthly.png")
    plt.close(fig)

    mix = pd.read_csv(mix_ann_path)
    fig, ax = plt.subplots(figsize=(7.5, 4))
    bottom = np.zeros(8)
    colors = {"火电": "#8c564b", "水电": "#1f77b4", "风电": "#2ca02c",
              "光伏": "#ff7f0e", "省外输入": "#7f7f7f"}
    for o in ORIGIN_CLASSES:
        ax.bar(mix["区域"], mix[o], bottom=bottom, label=o, color=colors[o])
        bottom += mix[o].to_numpy()
    ax.set_ylabel("消费电量来源占比")
    ax.set_title("各区域终端用电的电源来源分解(2025,能量口径)")
    ax.legend(ncols=5, fontsize=8)
    fig.savefig(OUT / "fig_q2_origin_mix.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4))
    x = np.arange(8)
    ax.bar(x - 0.3, resp["扩展生产责任P+"], 0.3, label="生产责任 P+")
    ax.bar(x, resp["消费责任全口径C+"], 0.3, label="消费责任 C+")
    ax.bar(x + 0.3, resp["共担责任(λ=0.5)"], 0.3, label=r"共担 $\lambda=0.5$")
    ax.set_xticks(x, REGIONS)
    ax.set_ylabel(r"年度碳排放责任 ktCO$_2$")
    ax.set_title("三种口径下的区域碳排放责任(2025)")
    ax.legend()
    fig.savefig(OUT / "fig_q2_responsibility.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    diff = rho_recv - rho_m
    im = ax.imshow(diff.T, cmap="PuOr", aspect="auto")
    ax.set_xticks(range(12), [m[-2:] for m in MONTHS])
    ax.set_yticks(range(8), REGIONS)
    ax.set_title(r"线损碳排口径差:受端承担 $-$ 送端承担(kgCO$_2$/kWh)")
    fig.colorbar(im, ax=ax, shrink=0.85)
    fig.savefig(OUT / "fig_q2_loss_convention_diff.png")
    plt.close(fig)


def main() -> None:
    rm, cm, ef_local, ef_ext = load_inputs()
    rho_m, mix_m, impshare_m = run_tracing(rm, cm, ef_local, ef_ext, "sender")
    rho_recv, _, _ = run_tracing(rm, cm, ef_local, ef_ext, "receiver")
    resp = responsibility(rm, cm, ef_local, ef_ext, rho_m)
    summary = export(rm, rho_m, rho_recv, mix_m, impshare_m, resp)
    make_plots(rho_m, rho_recv, OUT / "q2_origin_mix_annual.csv", resp)
    print(f"[Q2] 责任守恒相对误差: {summary['责任守恒相对误差']:.3e}")
    print("[Q2] 2025 区域终端碳强度:", summary["2025区域终端碳强度"])
    print(resp[["区域", "扩展生产责任P+", "消费责任全口径C+",
                "共担责任(λ=0.5)"]].round(1).to_string(index=False))
    print(f"[Q2] 输出目录: {OUT}")


if __name__ == "__main__":
    main()
