"""Gráficas y fichas de perfil, generadas desde las tablas de `entrega/tablas/` (RF-11, RNF-06)."""
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

import contenido
from configuracion import ARCHIVOS_FUENTE, ELECCIONES, FUENTE, NOMBRE_EQUIPO, PRESIDENCIALES, TABLAS

FIGURAS = TABLAS.parent / "figuras"
FICHAS = TABLAS.parent / "fichas"

# Primeras posiciones de la paleta categórica validada (azul, naranja, aqua, amarillo, magenta, verde), en orden fijo.
# La sexta solo la usan las variantes de la spec 004 con k = 6.
SERIE = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a", 4: "#eda100", 5: "#e87ba4", 6: "#008300"}
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
    etiquetas = [textwrap.fill(f"{p}. {x['nombre']}", 30) for p, x in metricas.items()][::-1]
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


def _ajustar_a_ancho(fig, texto, ancho: float, minimo: float):
    """Reduce la letra de `texto` hasta que ocupe a lo más `ancho` (fracción de la figura) en una línea."""
    render = fig.canvas.get_renderer()
    while texto.get_fontsize() > minimo and texto.get_window_extent(render).width > ancho * fig.bbox.width:
        texto.set_fontsize(texto.get_fontsize() - 0.5)


def ficha(p, metricas, ruta):
    """Ficha A4 a 300 ppp: cifras clave, trayectoria, edad y estrategia de un perfil."""
    x, est = metricas[p], contenido.ESTRATEGIAS[p]
    fig = plt.figure(figsize=(8.27, 11.69), dpi=300)
    fig.add_artist(plt.Rectangle((0, 0.955), 1, 0.045, transform=fig.transFigure, color=SERIE[p]))
    fig.text(0.06, 0.915, f"Perfil {p}", fontsize=11, color=TINTA_2)
    titulo = fig.text(0.06, 0.88, x["nombre"], fontsize=22, fontweight="bold")
    _ajustar_a_ancho(fig, titulo, ancho=0.88, minimo=15)
    cuerpo = textwrap.fill(contenido.narrativa(p, metricas), 86)
    fig.text(0.06, 0.865, cuerpo, fontsize=10, va="top", linespacing=1.5)

    cifras = [(f"{x['pct_lista']:.0f} %", "de la lista nominal 2024"), (x["mediana_edad"], "tramo de edad mediano"),
              (f"{x['pct_mujeres']:.0f} %", "mujeres"), (f"{100 * x['part'][2024]:.0f} %", "participación en 2024")]
    for i, (valor, rotulo) in enumerate(cifras):
        fig.text(0.06 + 0.23 * i, 0.745, valor, fontsize=20, fontweight="bold")
        fig.text(0.06 + 0.23 * i, 0.728, rotulo, fontsize=8.5, color=TINTA_2)

    nac = _t("participacion_nacional_filtrada.csv")
    ax = fig.add_axes([0.09, 0.535, 0.38, 0.155])
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
    ax2 = fig.add_axes([0.57, 0.535, 0.38, 0.155])
    ax2.bar(range(len(grupos)), [fila[g] for g in grupos], color=SERIE[p], width=0.7)
    ax2.set_xticks(range(len(grupos)), grupos, rotation=70, fontsize=6.5)
    ax2.set_title("Edad (% de la lista del perfil)", loc="left", fontsize=9.5, fontweight="bold")
    _limpiar(ax2)

    fig.text(0.06, 0.445, "Estrategia propuesta", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.425, f"Prioridad: {est['prioridad']}", fontsize=9.5, color=TINTA_2)
    y = 0.40
    bloques = [("Objetivo: " + est["objetivo"], "")] + [("• " + a, "") for a in est["acciones"]] \
        + [("Cómo se mide: " + est["indicador"], "")]
    for texto, _ in bloques:
        envuelto = textwrap.fill(texto, 92, subsequent_indent="   ")
        fig.text(0.06, y, envuelto, fontsize=10, va="top", linespacing=1.5)
        y -= 0.0185 * (envuelto.count("\n") + 1) + 0.016

    # Dónde empezar (spec 002, RF-11).
    y -= 0.008
    fig.text(0.06, y, "Dónde empezar", fontsize=11, fontweight="bold", va="top")
    y -= 0.024
    lineas = ["Distritos federales con más personas del perfil (entidad y distrito; personas y % de la lista 2024 del distrito): "
              + "; ".join(contenido.distritos_prioritarios(p)) + "."]
    for texto in lineas:
        envuelto = textwrap.fill(texto, 92)
        fig.text(0.06, y, envuelto, fontsize=9.5, va="top", linespacing=1.5)
        y -= 0.0175 * (envuelto.count("\n") + 1) + 0.012
    assert y > 0.092, f"la ficha {p} se encima con el pie (y = {y:.3f})"

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


def radar_centroides(centroides: pl.DataFrame, ruta, nombres: dict[int, str],
                     titulo: str = "Centroides de los perfiles en z-score (línea punteada: promedio de las celdas)"):
    """Un radar por perfil con la misma escala; la línea punteada es z = 0, el promedio de las celdas (spec 004, RF-07)."""
    rasgos = [c for c in centroides.columns if c != "perfil"]
    ang = np.linspace(0, 2 * np.pi, len(rasgos), endpoint=False)
    cerrar = lambda v: np.r_[v, v[:1]]
    lim = max(1.0, np.ceil(np.abs(centroides.select(rasgos).to_numpy()).max() * 2) / 2)
    k = centroides.height
    fig, ejes = plt.subplots(1, k, figsize=(2.6 * k, 3.5), dpi=200, subplot_kw={"polar": True})
    for ax, fila in zip(np.atleast_1d(ejes), centroides.iter_rows(named=True)):
        v = np.array([fila[r] for r in rasgos])
        color = SERIE[fila["perfil"]]
        ax.plot(cerrar(ang), np.zeros(len(ang) + 1), color=NEUTRO, lw=1, ls="--")
        ax.plot(cerrar(ang), cerrar(v), color=color, lw=2)
        ax.fill(cerrar(ang), cerrar(v), color=color, alpha=0.18, linewidth=0)
        ax.set_ylim(-lim, lim)
        ax.set_xticks(ang, rasgos, fontsize=8, color=TINTA_2)
        ax.set_yticks([-1, 0, 1], ["−1", "0", "+1"], fontsize=7, color=TINTA_2)
        ax.set_rlabel_position(45)
        ax.tick_params(axis="x", pad=7)
        ax.grid(color=REJILLA, linewidth=0.8)
        ax.spines["polar"].set_color(REJILLA)
        ax.set_title(f"{fila['perfil']}. {textwrap.fill(nombres[fila['perfil']], 24)}", fontsize=9, color=TINTA, pad=16)
    fig.suptitle(titulo, x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def mapa_centroides(centroides: pl.DataFrame, ruta, nombres: dict[int, str]):
    """Valores de los centroides en z-score; escala divergente con gris en 0 (spec 004, RF-07)."""
    rasgos = [c for c in centroides.columns if c != "perfil"]
    divergente = LinearSegmentedColormap.from_list("divergente", [SERIE[1], "#efeeea", SERIE[2]])
    valores = centroides.select(rasgos).to_numpy()
    fig, ax = plt.subplots(figsize=(6.6, 0.55 * centroides.height + 1.3), dpi=200)
    tope = float(np.abs(valores).max())
    sns.heatmap(valores, vmin=-tope, vmax=tope, center=0, cmap=divergente, annot=True, fmt="+.2f",
                annot_kws={"color": TINTA, "fontsize": 9}, linewidths=2, linecolor=SUPERFICIE, cbar=False, ax=ax,
                xticklabels=rasgos, yticklabels=[f"{p}. {nombres[p]}" for p in centroides["perfil"]])
    ax.tick_params(length=0, labelsize=8.5)
    fig.suptitle("Centroides en z-score (azul: bajo el promedio; naranja: arriba)", x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def mezcla_por_perfil(mezcla: pl.DataFrame, ruta, nombres_perfil: dict[int, str], nombres_arquetipo: dict[int, str]):
    """Barras apiladas al 100 %: de qué arquetipos se compone, en promedio, cada perfil (spec 004, RF-10)."""
    columnas = [c for c in mezcla.columns if c.startswith("arq_")]
    filas = list(mezcla.iter_rows(named=True))[::-1]   # perfil 1 arriba
    fig, ax = plt.subplots(figsize=(7.4, 0.62 * len(filas) + 1.6), dpi=200)
    for y, fila in enumerate(filas):
        izquierda = 0.0
        for c in columnas:
            j, v = int(c.split("_")[1]), 100 * fila[c]
            ax.barh(y, v, left=izquierda, height=0.62, color=SERIE[j], edgecolor=SUPERFICIE, linewidth=2)
            if v >= 10:
                ax.text(izquierda + v / 2, y, f"{v:.0f} %", ha="center", va="center", fontsize=8, color=TINTA)
            izquierda += v
    ax.set_yticks(range(len(filas)), [f"{f['grupo']}. {textwrap.fill(nombres_perfil[f['grupo']], 34)}" for f in filas], fontsize=8)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% de la lista nominal 2024 del perfil")
    ax.tick_params(axis="y", length=0)
    _limpiar(ax, "x")
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=SERIE[int(c.split("_")[1])]) for c in columnas],
              labels=[textwrap.fill(f"A{int(c.split('_')[1])}. {nombres_arquetipo[int(c.split('_')[1])]}", 30) for c in columnas],
              frameon=False, fontsize=7.5, ncol=2, loc="lower left", bbox_to_anchor=(0, 1.0))
    fig.suptitle("Mezcla de arquetipos dentro de cada perfil", x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)
