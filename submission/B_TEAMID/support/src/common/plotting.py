"""SciencePlots + XeLaTeX（ctex，与论文 Times / 中宋一致）。"""
import matplotlib

matplotlib.use("pgf")
import matplotlib.pyplot as plt  # noqa: E402
import scienceplots  # noqa: F401  # registers plt.style names

# 与 paper/main.tex 对齐：Fandol 中文 + TeX Gyre Termes 西文
_PGF_PREAMBLE = r"""
\usepackage{amsmath,amssymb}
\usepackage[UTF8,fontset=fandol]{ctex}
\setmainfont{TeX Gyre Termes}[
  Extension      = .otf,
  UprightFont    = texgyretermes-regular,
  BoldFont       = texgyretermes-bold,
  ItalicFont     = texgyretermes-italic,
  BoldItalicFont = texgyretermes-bolditalic,
  Path           = /usr/share/texmf/fonts/opentype/public/tex-gyre/,
  Ligatures      = TeX,
]
"""


def setup() -> None:
    plt.style.use(["science", "grid"])
    plt.rcParams.update({
        "pgf.texsystem": "xelatex",
        "pgf.rcfonts": False,
        "pgf.preamble": _PGF_PREAMBLE,
        "text.usetex": True,
        "font.family": "serif",
        "axes.unicode_minus": False,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    })
