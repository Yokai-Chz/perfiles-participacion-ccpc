"""Gráficas y fichas de perfil, generadas desde las tablas de `entrega/tablas/` (RF-11, RNF-06)."""
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import polars as pl
from matplotlib import font_manager

import contenido
from configuracion import ARCHIVOS_FUENTE, ELECCIONES, FUENTE, NOMBRE_EQUIPO, PRESIDENCIALES, TABLAS

FIGURAS = TABLAS.parent / "figuras"
FICHAS = TABLAS.parent / "fichas"

# Cinco primeras posiciones de la paleta categórica validada (azul, naranja, aqua, amarillo, magenta), en orden fijo.
SERIE = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a", 4: "#eda100", 5: "#e87ba4"}
TINTA, TINTA_2, SUPERFICIE, REJILLA = "#0b0b0b", "#52514e", "#fcfcfb", "#e4e3df"
NEUTRO = "#9a998f"

for ruta in ARCHIVOS_FUENTE.values():
    font_manager.fontManager.addfont(ruta)
plt.rcParams.update({"font.family": FUENTE, "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE,
                     "savefig.facecolor": SUPERFICIE, "text.color": TINTA, "axes.labelcolor": TINTA_2,
                     "xtick.color": TINTA_2, "ytick.color": TINTA_2, "axes.edgecolor": REJILLA,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 10})


def _t(nombre):
    return pl.read_csv(TABLAS / nombre)


def _limpiar(ax, rejilla="y"):
    ax.grid(axis=rejilla, color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)


def _bandas_presidenciales(ax):
    for a in PRESIDENCIALES:
        ax.axvspan(a - 1.2, a + 1.2, color=REJILLA, alpha=0.55, linewidth=0)


def participacion_nacional(ruta):
    d = _t("participacion_nacional_filtrada.csv")
    fig, ax = plt.subplots(figsize=(6.2, 3.2), dpi=200)
    colores = [SERIE[1] if a in PRESIDENCIALES else NEUTRO for a in d["AELEC"]]
    barras = ax.bar([str(a) for a in d["AELEC"]], 100 * d["tasa_nacional"], color=colores, width=0.6)
    for b, v in zip(barras, d["tasa_nacional"]):
        ax.text(b.get_x() + b.get_width() / 2, 100 * v + 1.2, f"{100 * v:.0f} %", ha="center", fontsize=9)
    ax.set_ylim(0, 80)
    ax.set_ylabel("Participación, SV / (SV + NV)")
    ax.set_title("Participación nacional por elección", loc="left", fontsize=11, fontweight="bold")
    _limpiar(ax)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=SERIE[1]), plt.Rectangle((0, 0), 1, 1, color=NEUTRO)],
              labels=["Presidencial", "Intermedia"], frameon=False, loc="upper left", ncol=2, bbox_to_anchor=(0, 0.97))
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def trayectorias(ruta, metricas):
    nac = _t("participacion_nacional_filtrada.csv")
    fig, ax = plt.subplots(figsize=(6.6, 3.9), dpi=200)
    _bandas_presidenciales(ax)
    ax.plot(nac["AELEC"], 100 * nac["tasa_nacional"], color=NEUTRO, linewidth=1.6, linestyle=(0, (4, 3)), label="Promedio nacional")
    for p, x in metricas.items():
        ax.plot(ELECCIONES, [100 * x["part"][a] for a in ELECCIONES], color=SERIE[p], linewidth=2, marker="o",
                markersize=6, markeredgecolor=SUPERFICIE, markeredgewidth=1.5, label=f"{p}. {x['nombre']}")
    ax.set_xticks(ELECCIONES)
    ax.set_ylim(30, 80)
    ax.set_ylabel("Participación (%)")
    ax.set_title("Participación de cada perfil por elección (franja gris: presidencial)", loc="left", fontsize=10.5, fontweight="bold")
    _limpiar(ax)
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def pesos(ruta, metricas):
    fig, ax = plt.subplots(figsize=(6.2, 2.8), dpi=200)
    etiquetas = [f"{p}. {x['nombre']}" for p, x in metricas.items()][::-1]
    valores = [x["pct_lista"] for x in metricas.values()][::-1]
    colores = [SERIE[p] for p in metricas][::-1]
    barras = ax.barh(etiquetas, valores, color=colores, height=0.6)
    for b, v in zip(barras, valores):
        ax.text(v + 0.6, b.get_y() + b.get_height() / 2, f"{v:.1f} %", va="center", fontsize=9)
    ax.set_xlim(0, 42)
    ax.set_xlabel("Porcentaje de la lista nominal 2024")
    ax.set_title("Peso de cada perfil", loc="left", fontsize=11, fontweight="bold")
    _limpiar(ax, "x")
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def edades(ruta, metricas):
    d = _t("perfiles_edad.csv")
    grupos = [c for c in d.columns if c != "perfil"]
    fig, ejes = plt.subplots(len(metricas), 1, figsize=(6.2, 6.4), dpi=200, sharex=True, sharey=True)
    for ax, (p, x) in zip(ejes, metricas.items()):
        fila = d.filter(pl.col("perfil") == p).row(0, named=True)
        ax.bar(range(len(grupos)), [fila[g] for g in grupos], color=SERIE[p], width=0.7)
        ax.set_title(f"{p}. {x['nombre']}", loc="left", fontsize=8.5, pad=2)
        _limpiar(ax)
        ax.set_ylim(0, 30)
    ejes[-1].set_xticks(range(len(grupos)), grupos, rotation=60, fontsize=8)
    fig.supylabel("% de la lista del perfil", fontsize=9)
    fig.suptitle("Distribución por grupo de edad", x=0.02, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def seleccion_k(ruta):
    d = _t("seleccion_k.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.4, 2.8), dpi=200)
    a1.plot(d["k"], d["silhouette_sin_pesos"], color=SERIE[1], marker="o", linewidth=2, markeredgecolor=SUPERFICIE)
    a1.set_title("Silhouette (sin pesos)", loc="left", fontsize=10, fontweight="bold")
    a2.plot(d["k"], d["ARI_semillas_media"], color=SERIE[1], marker="o", linewidth=2, label="Entre semillas", markeredgecolor=SUPERFICIE)
    a2.plot(d["k"], d["ARI_submuestras_media"], color=SERIE[2], marker="o", linewidth=2, label="Entre submuestras", markeredgecolor=SUPERFICIE)
    a2.axhline(0.8, color=NEUTRO, linestyle=(0, (4, 3)), linewidth=1.2)
    a2.set_title("Estabilidad (ARI medio)", loc="left", fontsize=10, fontweight="bold")
    a2.legend(frameon=False, fontsize=8, loc="lower right")
    for ax in (a1, a2):
        ax.set_xticks(d["k"])
        ax.set_xlabel("Número de perfiles (k)")
        _limpiar(ax)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def ficha(p, metricas, ruta):
    """Ficha A4 a 300 ppp: cifras clave, trayectoria, edad y estrategia de un perfil."""
    x, est = metricas[p], contenido.ESTRATEGIAS[p]
    fig = plt.figure(figsize=(8.27, 11.69), dpi=300)
    fig.add_artist(plt.Rectangle((0, 0.955), 1, 0.045, transform=fig.transFigure, color=SERIE[p]))
    fig.text(0.06, 0.915, f"Perfil {p}", fontsize=11, color=TINTA_2)
    fig.text(0.06, 0.88, x["nombre"], fontsize=22, fontweight="bold")
    cuerpo = textwrap.fill(contenido.narrativa(p, metricas), 86)
    fig.text(0.06, 0.865, cuerpo, fontsize=10, va="top", linespacing=1.5)

    cifras = [(f"{x['pct_lista']:.0f} %", "de la lista nominal 2024"), (x["mediana_edad"], "tramo de edad mediano"),
              (f"{x['pct_mujeres']:.0f} %", "mujeres"), (f"{100 * x['part'][2024]:.0f} %", "participación en 2024")]
    for i, (valor, rotulo) in enumerate(cifras):
        fig.text(0.06 + 0.23 * i, 0.745, valor, fontsize=20, fontweight="bold")
        fig.text(0.06 + 0.23 * i, 0.728, rotulo, fontsize=8.5, color=TINTA_2)

    nac = _t("participacion_nacional_filtrada.csv")
    ax = fig.add_axes([0.09, 0.50, 0.38, 0.19])
    _bandas_presidenciales(ax)
    ax.plot(nac["AELEC"], 100 * nac["tasa_nacional"], color=NEUTRO, linewidth=1.5, linestyle=(0, (4, 3)), label="Promedio nacional")
    ax.plot(ELECCIONES, [100 * x["part"][a] for a in ELECCIONES], color=SERIE[p], linewidth=2.2, marker="o", markersize=6,
            markeredgecolor=SUPERFICIE, markeredgewidth=1.5, label=f"Perfil {p}")
    ax.set_xticks(ELECCIONES, [str(a)[2:] for a in ELECCIONES])
    ax.set_ylim(30, 80)
    ax.set_title("Participación por elección (%)", loc="left", fontsize=9.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    _limpiar(ax)

    d = _t("perfiles_edad.csv")
    grupos = [c for c in d.columns if c != "perfil"]
    fila = d.filter(pl.col("perfil") == p).row(0, named=True)
    ax2 = fig.add_axes([0.57, 0.50, 0.38, 0.19])
    ax2.bar(range(len(grupos)), [fila[g] for g in grupos], color=SERIE[p], width=0.7)
    ax2.set_xticks(range(len(grupos)), grupos, rotation=70, fontsize=6.5)
    ax2.set_title("Edad (% de la lista del perfil)", loc="left", fontsize=9.5, fontweight="bold")
    _limpiar(ax2)

    fig.text(0.06, 0.41, "Estrategia propuesta", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.39, f"Prioridad: {est['prioridad']}", fontsize=9.5, color=TINTA_2)
    y = 0.365
    bloques = [("Objetivo: " + est["objetivo"], "")] + [("• " + a, "") for a in est["acciones"]] \
        + [("Cómo se mide: " + est["indicador"], "")]
    for texto, _ in bloques:
        envuelto = textwrap.fill(texto, 92, subsequent_indent="   ")
        fig.text(0.06, y, envuelto, fontsize=10, va="top", linespacing=1.5)
        y -= 0.0185 * (envuelto.count("\n") + 1) + 0.016

    pie = ("Borrador para revisión del equipo. Fuente: Conteos Censales de Participación Ciudadana (INE), cálculos propios. "
           "Los perfiles describen grupos de edad y sexo (campo SEXO de la fuente) en cada elección, no a las mismas personas a lo largo del tiempo.")
    fig.text(0.06, 0.085, textwrap.fill(pie, 105), fontsize=7.5, color=TINTA_2, va="top", linespacing=1.4)
    fig.text(0.06, 0.03, f"{NOMBRE_EQUIPO} · Eje 1, Reto 1: Perfiles ciudadanos de participación", fontsize=8, color=TINTA_2)
    fig.savefig(ruta)
    plt.close(fig)


def generar_todo():
    FIGURAS.mkdir(parents=True, exist_ok=True)
    FICHAS.mkdir(parents=True, exist_ok=True)
    m = contenido.metricas()
    participacion_nacional(FIGURAS / "participacion_nacional.png")
    trayectorias(FIGURAS / "trayectorias.png", m)
    pesos(FIGURAS / "pesos.png", m)
    edades(FIGURAS / "edades.png", m)
    seleccion_k(FIGURAS / "seleccion_k.png")
    for p in m:
        ficha(p, m, FICHAS / f"ficha_perfil_{p}.png")
