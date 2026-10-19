"""Estilo visual común para Matplotlib y Seaborn.

Paleta categórica validada para daltonismo (orden fijo, nunca cíclico): las
tres primeras posiciones pasan la validación "todos contra todos", por eso
ningún gráfico usa más de tres colores con significado; el resto va en gris.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

FIGURES = Path(__file__).resolve().parents[1] / "output" / "figures"

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_TENUE = "#898781"
GRILLA = "#e1e0d9"
EJE = "#c3c2b7"
GRIS_CONTEXTO = "#c3c2b7"

AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"

# El color sigue a la entidad: Doméstico siempre azul, Internacional siempre naranja.
COLOR_AMBITO = {"Doméstico": AZUL, "Internacional": NARANJA}

RAMPA_AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6",
              "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
CMAP_SECUENCIAL = LinearSegmentedColormap.from_list("azul", RAMPA_AZUL)


def aplicar_estilo() -> None:
    sns.set_theme(style="ticks", context="notebook")
    mpl.rcParams.update({
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "savefig.facecolor": SUPERFICIE,
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
        "text.color": TINTA,
        "axes.labelcolor": TINTA_2,
        "axes.titlecolor": TINTA,
        "axes.titlesize": 13,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.labelsize": 10,
        "axes.edgecolor": EJE,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRILLA,
        "grid.linewidth": 0.6,
        "grid.linestyle": "-",
        "xtick.color": TINTA_TENUE,
        "ytick.color": TINTA_TENUE,
        "xtick.labelcolor": TINTA_2,
        "ytick.labelcolor": TINTA_2,
        "lines.linewidth": 2,
        "legend.frameon": False,
        "legend.fontsize": 9,
    })


def fuente(ax: plt.Axes, texto: str = "Fuente: JAC/DGAC, Bitácora de Vuelos (datos.gob.cl, versión 2026-10-13).") -> None:
    """Nota de procedencia al pie de la figura."""
    ax.figure.text(0.01, 0.005, texto, fontsize=8, color=TINTA_TENUE, ha="left", va="bottom")


def miles(x: float, _pos=None) -> str:
    """Formato de miles con punto (convención chilena)."""
    return f"{x:,.0f}".replace(",", ".")


def guardar(fig: plt.Figure, nombre: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / f"{nombre}.png"
    fig.savefig(path, bbox_inches="tight")
    return path
