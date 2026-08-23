"""论文用高级图元：脊线、哑铃、棒棒糖、斜坡、冲积、平行坐标、甘特。

只提供 ax/fig 级绘图，不写大标题；中文与数学走 XeLaTeX/PGF。
"""
from __future__ import annotations

import numpy as np

OKABE = ["#E69F00", "#56B4E9", "#009E73", "#F0E442",
         "#0072B2", "#D55E00", "#CC79A7", "#000000"]
ORIGIN_COLORS = {
    "火电": "#8c564b",
    "水电": "#0072B2",
    "风电": "#009E73",
    "光伏": "#E69F00",
    "省外输入": "#7f7f7f",
}


def ridge(ax, x, Y, labels, colors=None, ylabel=None):
    """Joyplot：每条序列一个偏移填充脊。Y 形状 (n_series, n_x)。"""
    Y = np.asarray(Y, float)
    n = Y.shape[0]
    colors = colors or [OKABE[i % len(OKABE)] for i in range(n)]
    peak = float(np.nanmax(Y)) if Y.size else 1.0
    offset = 0.78 * peak
    yticks = []
    for i in range(n):
        base = (n - 1 - i) * offset
        y = Y[i] + base
        ax.fill_between(x, base, y, color=colors[i], alpha=0.38, lw=0)
        ax.plot(x, y, color=colors[i], lw=1.15)
        yticks.append(base + 0.18 * peak)
    ax.set_yticks(yticks, labels)
    ax.tick_params(axis="y", length=0)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.set_xlim(x[0], x[-1])


def dumbbell(ax, labels, left, right, left_label, right_label,
             mid=None, mid_label=None, colors=None):
    """类别轴上的哑铃图；可选第三点（如原始隐含值）。"""
    y = np.arange(len(labels))
    left = np.asarray(left, float)
    right = np.asarray(right, float)
    c_left, c_right = (colors or ("#0072B2", "#D55E00"))
    ax.hlines(y, left, right, color="#8a8a8a", lw=1.15, zorder=1)
    ax.scatter(left, y, s=38, facecolors="none", edgecolors=c_left,
               linewidths=1.2, zorder=3, label=left_label)
    ax.scatter(right, y, s=36, color=c_right, zorder=3, label=right_label)
    if mid is not None:
        mid = np.asarray(mid, float)
        mask = np.isfinite(mid)
        ax.scatter(mid[mask], y[mask], s=46, marker="|", color="#4d4d4d",
                   linewidths=1.4, zorder=2, label=mid_label)
    ax.set_yticks(y, labels)
    ax.legend(fontsize=8, loc="lower right")


def lollipop_h(ax, labels, values, color="#0072B2", diverging=False):
    """水平棒棒糖图。diverging=True 时按正负着色。"""
    y = np.arange(len(labels))
    values = np.asarray(values, float)
    if diverging:
        colors = np.where(values >= 0, "#D55E00", "#0072B2")
        ax.axvline(0.0, color="#666", lw=0.7)
    else:
        colors = [color] * len(values)
    ax.hlines(y, 0.0 if not diverging else np.minimum(values, 0.0),
              values, color="#8a8a8a", lw=1.05, zorder=1)
    ax.scatter(values, y, s=34, c=colors, zorder=3, edgecolors="white",
               linewidths=0.4)
    ax.set_yticks(y, labels)


def slope(ax, stages, series, colors=None, lw=1.2):
    """多系列斜坡图：横轴为口径/阶段。"""
    x = np.arange(len(stages))
    names = list(series.keys())
    colors = colors or [OKABE[i % len(OKABE)] for i in range(len(names))]
    for i, name in enumerate(names):
        y = np.asarray(series[name], float)
        ax.plot(x, y, "-o", color=colors[i], lw=lw, ms=4.2,
                label=name, zorder=2)
    ax.set_xticks(x, stages)
    ax.legend(ncols=4, fontsize=7.5, loc="upper center",
              bbox_to_anchor=(0.5, 1.14), frameon=False)


def parallel_coordinates(ax, df, class_col, value_cols, colors=None):
    """平行坐标：每行一条折线，列已在调用方归一化到 [0,1]。"""
    x = np.arange(len(value_cols))
    colors = colors or [OKABE[i % len(OKABE)] for i in range(len(df))]
    for i, (_, row) in enumerate(df.iterrows()):
        ax.plot(x, [row[c] for c in value_cols], "-o", color=colors[i],
                lw=1.15, ms=3.6, label=str(row[class_col]))
    ax.set_xticks(x, value_cols)
    ax.set_ylim(-0.05, 1.08)
    ax.legend(ncols=8, fontsize=7.5, loc="upper center",
              bbox_to_anchor=(0.5, 1.16), frameon=False)


def alluvial(ax, flow, left_labels, right_labels, left_colors,
             gap=0.035):
    """两列冲积/桑基：flow[i,j] 为左 i → 右 j。"""
    from matplotlib.patches import FancyBboxPatch, PathPatch
    from matplotlib.path import Path

    flow = np.asarray(flow, float)
    flow = np.where(np.isfinite(flow), flow, 0.0)
    left_tot = flow.sum(axis=1)
    right_tot = flow.sum(axis=0)
    total = float(left_tot.sum())
    if total <= 0:
        ax.axis("off")
        return

    def _stack(totals):
        usable = 1.0 - gap * max(len(totals) - 1, 0)
        scale = usable / total
        y, blocks = 1.0, []
        for v in totals:
            h = v * scale
            blocks.append((y - h, y))
            y -= h + gap
        return blocks

    left_blk = _stack(left_tot)
    right_blk = _stack(right_tot)
    left_cur = [b[0] for b in left_blk]
    right_cur = [b[0] for b in right_blk]
    order = np.argsort(-flow.ravel())
    n_r = len(right_labels)
    for idx in order:
        i, j = divmod(int(idx), n_r)
        v = flow[i, j]
        if v < 0.002 * total:
            continue
        h = v / total * (1.0 - gap * max(len(left_labels) - 1, 0))
        y0a, y0b = left_cur[i], left_cur[i] + h
        y1a, y1b = right_cur[j], right_cur[j] + h
        left_cur[i], right_cur[j] = y0b, y1b
        verts = [
            (0.0, y0a), (0.38, y0a), (0.62, y1a), (1.0, y1a),
            (1.0, y1b), (0.62, y1b), (0.38, y0b), (0.0, y0b),
            (0.0, y0a),
        ]
        codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
                 Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
                 Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes),
                               facecolor=left_colors[i], edgecolor="none",
                               alpha=0.38, zorder=1))

    for i, lab in enumerate(left_labels):
        y0, y1 = left_blk[i]
        ax.add_patch(FancyBboxPatch(
            (-0.08, y0), 0.08, max(y1 - y0, 0.02),
            boxstyle="round,pad=0.006", facecolor=left_colors[i],
            edgecolor="none", zorder=3))
        ax.text(-0.11, 0.5 * (y0 + y1), lab, ha="right", va="center",
                fontsize=8, zorder=4)
    for j, lab in enumerate(right_labels):
        y0, y1 = right_blk[j]
        ax.add_patch(FancyBboxPatch(
            (1.0, y0), 0.06, max(y1 - y0, 0.02),
            boxstyle="round,pad=0.006", facecolor="#4a4a4a",
            edgecolor="none", zorder=3))
        ax.text(1.08, 0.5 * (y0 + y1), lab, ha="left", va="center",
                fontsize=8, zorder=4)
    ax.set_xlim(-0.42, 1.22)
    ax.set_ylim(-0.04, 1.04)
    ax.axis("off")


def heatmap_with_marginals(fig, z, xlabels, ylabels, cmap="RdBu_r",
                           vmin=-6, vmax=6, cbar_label="",
                           annotate_abs=3.0):
    """主热力图 + 顶/侧 |z| 最大边际条。z 形状 (n_x, n_y)。"""
    from matplotlib.gridspec import GridSpec

    z = np.asarray(z, float)
    nx, ny = z.shape
    gs = GridSpec(2, 3, figure=fig, width_ratios=[8.0, 1.25, 0.28],
                  height_ratios=[1.15, 3.4], hspace=0.08, wspace=0.08)
    ax_top = fig.add_subplot(gs[0, 0])
    ax = fig.add_subplot(gs[1, 0])
    ax_r = fig.add_subplot(gs[1, 1])
    cax = fig.add_subplot(gs[1, 2])

    im = ax.imshow(z.T, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto",
                   interpolation="nearest")
    ax.set_xticks(range(nx), xlabels)
    ax.set_yticks(range(ny), ylabels)
    ax.grid(False)
    for t in range(nx):
        for i in range(ny):
            if abs(z[t, i]) > annotate_abs:
                ax.text(t, i, f"{z[t, i]:.1f}", ha="center", va="center",
                        fontsize=6.5,
                        color="white" if abs(z[t, i]) > 4 else "black")

    top_v = np.nanmax(np.abs(z), axis=1)
    ax_top.scatter(np.arange(nx), top_v, s=28, color="#4c72b0", zorder=3)
    ax_top.vlines(np.arange(nx), 0.0, top_v, color="#4c72b0", lw=0.8)
    ax_top.set_xlim(-0.5, nx - 0.5)
    ax_top.set_xticks([])
    ax_top.set_ylabel(r"月 $\max|z|$", fontsize=8)
    ax_top.grid(False)

    side_v = np.nanmax(np.abs(z), axis=0)
    ax_r.scatter(side_v, np.arange(ny), s=28, color="#c44e52", zorder=3)
    ax_r.hlines(np.arange(ny), 0.0, side_v, color="#c44e52", lw=0.8)
    ax_r.set_ylim(ny - 0.5, -0.5)
    ax_r.set_yticks([])
    ax_r.set_xlabel(r"区 $\max|z|$", fontsize=8)
    ax_r.grid(False)

    cbar = fig.colorbar(im, cax=cax)
    if cbar_label:
        cbar.set_label(cbar_label)
    return ax, im


def gantt(ax, rows, years, color_of, vmax=None):
    """离散甘特：rows 为 (label, year, scale, kind) 列表。"""
    labels = []
    for lab, *_ in rows:
        if lab not in labels:
            labels.append(lab)
    ypos = {lab: i for i, lab in enumerate(labels)}
    vmax = float(vmax or max((r[2] for r in rows), default=1.0))
    for lab, year, scale, kind in rows:
        if scale <= 0:
            continue
        alpha = 0.28 + 0.72 * (scale / vmax)
        ax.barh(ypos[lab], 0.82, left=year - 0.41, height=0.62,
                color=color_of(kind), alpha=alpha, edgecolor="white",
                linewidth=0.4)
        ax.text(year, ypos[lab], f"{scale:g}", ha="center", va="center",
                fontsize=7)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xticks(years)
    ax.set_xlim(min(years) - 0.7, max(years) + 0.7)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)


def connected_scatter(ax, x, y, labels, color="#0072B2", marker="o",
                     sizes=None):
    """带阶段标注的气泡散点，不连线。"""
    s = 42 if sizes is None else np.asarray(sizes, float)
    ax.scatter(x, y, s=s, color=color, marker=marker, zorder=3,
               edgecolors="white", linewidths=0.4)
    for xi, yi, lab in zip(x, y, labels):
        ax.annotate(lab, (xi, yi), textcoords="offset points",
                    xytext=(5, 5), fontsize=8)


def annotated_heatmap(ax, data, xlabels, ylabels, cmap="YlOrRd",
                      fmt=".0f", vmin=None, vmax=None, skip_zero=False):
    """带格值的矩阵热力图。"""
    data = np.asarray(data, float)
    im = ax.imshow(data, cmap=cmap, aspect="auto", interpolation="nearest",
                   vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(xlabels)), xlabels)
    ax.set_yticks(range(len(ylabels)), ylabels)
    ax.grid(False)
    scale = float(np.nanmax(np.abs(data))) if data.size else 1.0
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            if skip_zero and abs(v) < 1e-9:
                continue
            ax.text(j, i, format(v, fmt), ha="center", va="center",
                    fontsize=7,
                    color="white" if abs(v) > 0.55 * scale else "black")
    return im


def marimekko(ax, shares, widths, col_labels, row_labels, colors):
    """马赛克/Marimekko：列宽正比总量，块高为份额。shares 为 (n_col, n_row)。"""
    from matplotlib.patches import Rectangle

    shares = np.asarray(shares, float)
    widths = np.asarray(widths, float)
    widths = np.where(widths > 0, widths, 0.0)
    total_w = float(widths.sum()) or 1.0
    x = 0.0
    for j, w in enumerate(widths):
        wn = w / total_w
        y = 0.0
        for i, lab in enumerate(row_labels):
            h = float(shares[j, i])
            ax.add_patch(Rectangle((x, y), wn, h, facecolor=colors[i],
                                   edgecolor="white", linewidth=0.6))
            if h * wn >= 0.035:
                ax.text(x + 0.5 * wn, y + 0.5 * h, f"{100 * h:.0f}",
                        ha="center", va="center", fontsize=7, color="white")
            y += h
        ax.text(x + 0.5 * wn, -0.055, col_labels[j], ha="center", va="top",
                fontsize=8)
        x += wn
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(-0.12, 1.02)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0],
                  [r"0\%", r"25\%", r"50\%", r"75\%", r"100\%"])
    ax.set_xticks([])
    handles = [Rectangle((0, 0), 1, 1, color=c) for c in colors]
    ax.legend(handles, row_labels, ncols=min(len(row_labels), 5),
              fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.16),
              frameon=False)


def streamgraph(ax, x, stacks, labels, colors):
    """对称流图：手工累加基线。PGF 下 stackplot(baseline='sym') 不会居中。"""
    x = np.asarray(x, float)
    S = np.vstack([np.asarray(s, float) for s in stacks])
    lower = -0.5 * S.sum(axis=0)
    for i, lab in enumerate(labels):
        upper = lower + S[i]
        ax.fill_between(x, lower, upper, color=colors[i], linewidth=0,
                        alpha=0.92, label=lab, zorder=1)
        lower = upper
    ax.axhline(0.0, color="#666666", lw=0.55, ls="--", zorder=2)
    half = 0.5 * float(np.nanmax(S.sum(axis=0)) or 1.0)
    ax.set_ylim(-1.12 * half, 1.12 * half)


def bubble_matrix(ax, Z, xlabels, ylabels, cmap="YlOrRd"):
    """气泡矩阵：位置为类别网格，面积与颜色编码数值。Z 为 (n_x, n_y)。"""
    Z = np.asarray(Z, float)
    nx, ny = Z.shape
    xx, yy = np.meshgrid(np.arange(nx), np.arange(ny))
    z = Z.T
    lo, hi = float(np.nanmin(z)), float(np.nanmax(z))
    span = max(hi - lo, 1e-9)
    sizes = 36 + 260 * (z - lo) / span
    sc = ax.scatter(xx.ravel(), yy.ravel(), s=sizes.ravel(), c=z.ravel(),
                    cmap=cmap, edgecolors="white", linewidths=0.35, zorder=3)
    ax.set_xticks(range(nx), xlabels)
    ax.set_yticks(range(ny), ylabels)
    ax.set_xlim(-0.6, nx - 0.4)
    ax.set_ylim(ny - 0.4, -0.6)
    ax.grid(False)
    return sc


def forest(ax, labels, mid, lo, hi, points=None, mid_label="P50",
           point_label="点估计"):
    """水平森林图：区间加中位，不连成折线。"""
    y = np.arange(len(labels))
    mid = np.asarray(mid, float)
    lo = np.asarray(lo, float)
    hi = np.asarray(hi, float)
    ax.hlines(y, lo, hi, color="#0072B2", lw=1.15, zorder=1)
    ax.scatter(mid, y, s=34, color="#0072B2", zorder=3, label=mid_label)
    if points is not None:
        ax.scatter(np.asarray(points, float), y, s=36, marker="x",
                   color="#D55E00", zorder=4, label=point_label)
    ax.set_yticks(y, labels)


def level_deviation_forest(fig, labels, point, mid, lo, hi, *,
                           level_label, dev_label, level_fmt=".3f",
                           cmap="YlOrRd", mid_label="P50",
                           point_label="点估计"):
    """左列色带给出水平，右列把区间画成相对点估计的偏差，避免被量级吞掉。"""
    labels = list(labels)
    point = np.asarray(point, float)
    mid = np.asarray(mid, float)
    lo = np.asarray(lo, float)
    hi = np.asarray(hi, float)
    n = len(labels)
    # 右图不再重复类别名；色条跟在右图外侧，避免与纵轴文字抢中间缝。
    outer = fig.add_gridspec(1, 2, width_ratios=[1.15, 2.65], wspace=0.28)
    right = outer[0, 1].subgridspec(1, 2, width_ratios=[1.0, 0.032], wspace=0.10)
    ax_l = fig.add_subplot(outer[0, 0])
    ax_r = fig.add_subplot(right[0, 0])
    cax = fig.add_subplot(right[0, 1])
    ylim = (n - 0.5, -0.5)

    im = ax_l.imshow(point.reshape(-1, 1), cmap=cmap, aspect="auto",
                     interpolation="nearest")
    ax_l.set_xticks([])
    ax_l.set_yticks(range(n), labels)
    ax_l.set_ylim(ylim)
    ax_l.tick_params(axis="y", right=False)
    ax_l.grid(False)
    vmax = float(np.nanmax(np.abs(point))) or 1.0
    for i, v in enumerate(point):
        ax_l.text(0, i, format(v, level_fmt), ha="center", va="center",
                  fontsize=7,
                  color="white" if v > 0.55 * vmax else "black")
    fig.colorbar(im, cax=cax).set_label(level_label)

    y = np.arange(n)
    ax_r.axvline(0.0, color="#666666", lw=0.7, zorder=0)
    ax_r.hlines(y, lo - point, hi - point, color="#0072B2", lw=2.0, zorder=1)
    ax_r.scatter(mid - point, y, s=34, color="#0072B2", zorder=3,
                 label=mid_label)
    ax_r.scatter(np.zeros_like(y), y, s=36, marker="x", color="#D55E00",
                 zorder=4, label=point_label)
    ax_r.set_yticks(y)
    ax_r.set_ylim(ylim)
    ax_r.tick_params(axis="y", left=False, labelleft=False)
    ax_r.set_xlabel(dev_label)
    ax_r.legend(fontsize=7, loc="best")
    return ax_l, ax_r


def _em_width(text: str) -> float:
    """粗估显示宽度：汉字 1 em，ASCII 0.55 em。"""
    return float(sum(1.0 if ord(ch) > 127 else 0.55 for ch in text))


def _treemap_lines(lab: str, max_em: float) -> list[str]:
    """按 / 断行，使每行尽量不超过 max_em。"""
    parts = [p for p in str(lab).split("/") if p]
    if not parts:
        return []
    lines: list[str] = []
    cur = parts[0]
    for part in parts[1:]:
        cand = f"{cur}/{part}"
        if _em_width(cand) <= max_em:
            cur = cand
        else:
            lines.append(cur)
            cur = part
    lines.append(cur)
    return lines


def treemap(ax, values, labels, colors=None):
    """矩形树图。标签按块宽换行，放不下则不画，避免溢出图外。"""
    from matplotlib.patches import Rectangle

    values = np.asarray(values, float)
    values = np.maximum(values, 1e-12)
    colors = colors or [OKABE[i % len(OKABE)] for i in range(len(values))]
    rects = _squarify((values / values.sum() * 1.0).tolist(), 0.0, 0.0, 1.0, 1.0)
    # 等比例轴约 2.5 in；按略宽字号估计，避免贴边。
    em7 = (7.0 / 72.0) / 2.5
    for (x, y, w, h), lab, c in zip(rects, labels, colors):
        rect = Rectangle((x, y), w, h, facecolor=c, edgecolor="white",
                         linewidth=1.0)
        ax.add_patch(rect)
        pad = 0.024
        inner_w, inner_h = w - 2.0 * pad, h - 2.0 * pad
        if inner_w < 0.06 or inner_h < 0.045:
            continue
        fs, em = 7.0, em7
        lines = _treemap_lines(lab, 0.82 * inner_w / em)
        line_h = 1.22 * em
        if lines and (len(lines) * line_h > inner_h
                      or max(_em_width(s) for s in lines) * em > inner_w):
            fs, em = 6.0, em7 * 6.0 / 7.0
            lines = _treemap_lines(lab, 0.82 * inner_w / em)
            line_h = 1.22 * em
        if (not lines or len(lines) * line_h > inner_h
                or max(_em_width(s) for s in lines) * em > inner_w):
            continue
        n = len(lines)
        for i, line in enumerate(lines):
            yy = y + 0.5 * h + (0.5 * (n - 1) - i) * line_h
            txt = ax.text(x + 0.5 * w, yy, line, ha="center", va="center",
                          fontsize=fs, clip_on=True)
            txt.set_clip_path(rect.get_path(), rect.get_transform())
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_aspect("equal")


def _squarify(areas, x, y, w, h):
    """Bruls 等的 squarified treemap，返回 (x,y,w,h) 列表。"""

    def worst(row, length):
        s = sum(row)
        if s <= 0 or length <= 0:
            return 1e9
        return max(max(r * length ** 2 / s ** 2, s ** 2 / (r * length ** 2))
                   for r in row)

    def layout_row(row, x, y, w, h):
        s = sum(row)
        out = []
        if w >= h:
            tw = s / h if h else 0.0
            cy = y
            for r in row:
                rh = r / tw if tw else 0.0
                out.append((x, cy, tw, rh))
                cy += rh
            return out, x + tw, y, w - tw, h
        th = s / w if w else 0.0
        cx = x
        for r in row:
            rw = r / th if th else 0.0
            out.append((cx, y, rw, th))
            cx += rw
        return out, x, y + th, w, h - th

    def leftover(vals, x, y, w, h):
        if not vals:
            return []
        length = h if w >= h else w
        row = [vals[0]]
        i = 1
        while i < len(vals) and worst(row, length) >= worst(row + [vals[i]],
                                                            length):
            row.append(vals[i])
            i += 1
        rects, nx, ny, nw, nh = layout_row(row, x, y, w, h)
        return rects + leftover(vals[i:], nx, ny, nw, nh)

    return leftover(areas, x, y, w, h)
