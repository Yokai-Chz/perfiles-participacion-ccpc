"""Figuras de apoyo: estadísticas de los datos, algoritmos, cohortes y distritos (spec 002, RF-16).

Cada figura lee una tabla de `entrega/tablas/`. No cuentan para el límite de páginas del documento técnico.
"""
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.colors import LinearSegmentedColormap

import contenido
from configuracion import ELECCIONES, ESTADISTICAS, PRESIDENCIALES, SEDE_CIRCUNSCRIPCION, UMBRAL_NS
from figuras import NEUTRO, REJILLA, SERIE, SUPERFICIE, TINTA, TINTA_2, _limpiar, _t

# Rampa secuencial azul y par divergente rojo-gris-azul de la paleta validada (references/palette.md del skill dataviz).
SECUENCIAL = LinearSegmentedColormap.from_list("secuencial", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
DIVERGENTE = LinearSegmentedColormap.from_list("divergente", ["#e34948", "#f0efec", "#2a78d6"])
TIPOS = {"U": "Urbana", "M": "Mixta", "R": "Rural"}
SEXOS = {0: "Hombres", 1: "Mujeres"}
RASGOS = {"nivel": "Nivel", "brecha": "Brecha presidencial - intermedia", "tendencia": "Tendencia por elección",
          "volatilidad": "Volatilidad"}


def _titulo(fig, texto, sub=None):
    """Título y subtítulo a distancia fija del borde superior, sin importar la altura de la figura."""
    alto = fig.get_figheight()
    fig.text(0.02, 1 - 0.14 / alto, texto, fontsize=11.5, fontweight="bold", ha="left", va="top")
    if sub:
        fig.text(0.02, 1 - 0.40 / alto, sub, fontsize=8.5, color=TINTA_2, ha="left", va="top")


def _guardar(fig, nombre, sub=None, abajo=0.0):
    """`abajo`: pulgadas reservadas al pie para una leyenda de figura."""
    alto = fig.get_figheight()
    fig.tight_layout(rect=(0, abajo / alto, 1, 1 - (0.62 if sub else 0.40) / alto))
    fig.savefig(ESTADISTICAS / nombre)
    plt.close(fig)


def _nombre_perfil(p):
    return f"{p}. {contenido.NOMBRES[p]}"


def _perfiles():
    return sorted(contenido.NOMBRES)


# ---------- (a) Datos ----------

def piramide():
    d = _t("descriptiva_piramide_2024.csv").filter(pl.col("SEXO") < 2)
    grupos = d.select("g", "grupo_edad").unique().sort("g")["grupo_edad"].to_list()
    h = d.filter(pl.col("SEXO") == 0).sort("g")["LN"].to_numpy() / 1e6
    m = d.filter(pl.col("SEXO") == 1).sort("g")["LN"].to_numpy() / 1e6
    fig, ax = plt.subplots(figsize=(7, 4.6), dpi=200)
    y = np.arange(len(grupos))
    ax.barh(y, -h, color=SERIE[1], height=0.78, label="Hombres")
    ax.barh(y, m, color=SERIE[2], height=0.78, label="Mujeres")
    ax.set_yticks(y, grupos, fontsize=8)
    limite = max(h.max(), m.max()) * 1.15
    ax.set_xlim(-limite, limite)
    marcas = ax.get_xticks()
    ax.set_xticks(marcas, [f"{abs(v):.0f}" for v in marcas])
    ax.set_xlabel("Millones de personas en lista nominal")
    ax.axvline(0, color=TINTA_2, linewidth=0.8)
    ax.legend(frameon=False, loc="upper right", fontsize=8.5)
    _limpiar(ax, "x")
    nb = _t("descriptiva_piramide_2024.csv").filter(pl.col("SEXO") == 2)["LN"].sum()
    sub = f"Lista nominal 2024 por grupo de edad y sexo. Además, {nb:,} personas registradas como no binarias (solo en 2024)."
    _titulo(fig, "Pirámide de la lista nominal 2024", sub)
    _guardar(fig, "01_piramide_lista_nominal_2024.png", sub)


def participacion_tipo():
    d = _t("descriptiva_participacion_tipo.csv")
    fig, ax = plt.subplots(figsize=(7, 3.8), dpi=200)
    for a in PRESIDENCIALES:
        ax.axvspan(a - 1.2, a + 1.2, color=REJILLA, alpha=0.55, linewidth=0)
    for i, (t, nombre) in enumerate(TIPOS.items(), start=1):
        s = d.filter(pl.col("TIPOSEC") == t).sort("AELEC")
        ax.plot(s["AELEC"], 100 * s["tasa"], color=SERIE[i], linewidth=2, marker="o", markersize=6,
                markeredgecolor=SUPERFICIE, markeredgewidth=1.5, label=nombre)
    finales = sorted(((100 * d.filter((pl.col("TIPOSEC") == t) & (pl.col("AELEC") == ELECCIONES[-1]))["tasa"].item(), n)
                      for t, n in TIPOS.items()))
    y_previo = -np.inf
    for y, nombre in finales:   # separa las etiquetas al menos 1.6 puntos
        y = max(y, y_previo + 1.6)
        ax.text(ELECCIONES[-1] + 0.5, y, nombre, color=TINTA, fontsize=8.5, va="center")
        y_previo = y
    ax.set_xticks(ELECCIONES)
    ax.set_xlim(ELECCIONES[0] - 1, ELECCIONES[-1] + 3.5)
    ax.set_ylabel("Participación, SV / (SV + NV) (%)")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=3)
    _limpiar(ax)
    sub = "Toda la lista nominal, sin filtrar. Franja gris: elección presidencial."
    _titulo(fig, "Participación por tipo de sección", sub)
    _guardar(fig, "02_participacion_por_tipo_seccion.png", sub)


def participacion_entidad():
    d = _t("descriptiva_participacion_entidad.csv")
    orden = (d.group_by("EDOCVE").agg(pl.col("tasa").mean()).sort("tasa", "EDOCVE", descending=[True, False])["EDOCVE"].to_list())
    matriz = np.array([[d.filter((pl.col("EDOCVE") == e) & (pl.col("AELEC") == a))["tasa"].item() for a in ELECCIONES] for e in orden])
    fig, ax = plt.subplots(figsize=(6.4, 8.4), dpi=200)
    im = ax.imshow(100 * matriz, cmap=SECUENCIAL, aspect="auto", vmin=30, vmax=80)
    ax.set_xticks(range(len(ELECCIONES)), ELECCIONES)
    ax.set_yticks(range(len(orden)), [contenido.NOMBRES_ENTIDAD[e] for e in orden], fontsize=7.5)
    for i in range(matriz.shape[0]):
        for j in range(matriz.shape[1]):
            v = 100 * matriz[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.5, color="white" if v > 62 else TINTA)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    barra = fig.colorbar(im, ax=ax, shrink=0.5, pad=0.02)
    barra.set_label("Participación (%)", fontsize=8)
    sub = "Entidades ordenadas por su participación media en las 6 elecciones."
    _titulo(fig, "Participación por entidad y elección", sub)
    _guardar(fig, "03_participacion_por_entidad.png", sub)


def curva_edad():
    d = _t("cohortes_curva_edad.csv")
    fig, ejes = plt.subplots(2, 3, figsize=(8, 4.8), dpi=200, sharex=True, sharey=True)
    for ax, a in zip(ejes.flat, ELECCIONES):
        for otra in ELECCIONES:
            s = d.filter(pl.col("AELEC") == otra)
            ax.plot(s["EDAD"], 100 * s["tasa"], color=REJILLA, linewidth=1)
        s = d.filter(pl.col("AELEC") == a)
        ax.plot(s["EDAD"], 100 * s["tasa"], color=SERIE[1] if a in PRESIDENCIALES else SERIE[2], linewidth=2)
        ax.set_title(f"{a} ({'presidencial' if a in PRESIDENCIALES else 'intermedia'})", loc="left", fontsize=9)
        _limpiar(ax)
    for ax in ejes[1]:
        ax.set_xlabel("Edad exacta")
    for ax in ejes[:, 0]:
        ax.set_ylabel("Participación (%)")
    sub = "Cada panel resalta una elección; en gris, las demás. El salto a los 18 años es el primer voto."
    _titulo(fig, "Participación por edad exacta en cada elección", sub)
    _guardar(fig, "04_participacion_por_edad.png", sub)


def distribucion_ns():
    d = _t("distribucion_ns.csv")
    fig, ejes = plt.subplots(2, 3, figsize=(8, 4.6), dpi=200, sharex=True, sharey=True)
    for ax, a in zip(ejes.flat, ELECCIONES):
        s = d.filter(pl.col("AELEC") == a)
        colores = [SERIE[2] if desde >= UMBRAL_NS else SERIE[1] for desde in s["desde"]]
        ax.bar(100 * s["desde"], s["pct_secciones"], width=4.4, align="edge", color=colores)
        ax.axvline(100 * UMBRAL_NS, color=TINTA_2, linewidth=1, linestyle=(0, (4, 3)))
        ax.set_yscale("log")
        ax.set_title(str(a), loc="left", fontsize=9)
        _limpiar(ax)
    for ax in ejes[1]:
        ax.set_xlabel("NS como % de la lista de la sección")
    fig.supylabel("% de secciones (escala log)", fontsize=9)
    sub = f"Naranja: secciones marcadas por NS mayor a {100 * UMBRAL_NS:.0f} % (línea punteada). NS son cuadernillos sin captura, no abstención."
    _titulo(fig, "Distribución de NS por sección", sub)
    _guardar(fig, "05_distribucion_ns_por_seccion.png", sub)


def distribucion_rasgos():
    d = _t("celdas_perfil.csv")
    fig, ejes = plt.subplots(1, 4, figsize=(9, 2.9), dpi=200)
    for ax, (col, nombre) in zip(ejes, RASGOS.items()):
        ax.hist(100 * d[col].to_numpy(), bins=40, color=SERIE[1], edgecolor=SUPERFICIE, linewidth=0.4)
        ax.set_title(nombre, loc="left", fontsize=8.5)
        ax.set_xlabel("Puntos porcentuales", fontsize=8)
        _limpiar(ax)
    ejes[0].set_ylabel("Celdas")
    sub = f"{d.height:,} celdas (entidad × tipo de sección × sexo × grupo de edad), sin ponderar. Participación relativa a la entidad."
    _titulo(fig, "Distribución de los rasgos de las celdas", sub)
    _guardar(fig, "06_distribucion_rasgos_celdas.png", sub)


# ---------- (b) Algoritmos ----------

def seleccion_k():
    d, bic = _t("seleccion_k.csv"), _t("robustez_bic_mezcla.csv")
    k = int((ESTADISTICAS.parent / "tablas" / "k_elegido.txt").read_text())
    paneles = [("Inercia de k-means (codo)", d["inercia"] / 1e6, "Millones"),
               ("Silhouette (sin pesos)", d["silhouette_sin_pesos"], "Mayor es mejor"),
               ("Estabilidad entre submuestras", d["ARI_submuestras_media"], "ARI medio"),
               ("BIC de la mezcla gaussiana", bic["BIC_mezcla"], "Menor es mejor")]
    fig, ejes = plt.subplots(1, 4, figsize=(9.4, 2.9), dpi=200)
    for ax, (titulo, y, etiqueta) in zip(ejes, paneles):
        ax.plot(d["k"], y, color=SERIE[1], marker="o", linewidth=2, markersize=7, markeredgecolor=SUPERFICIE, markeredgewidth=1.5)
        ax.axvline(k, color=NEUTRO, linestyle=(0, (4, 3)), linewidth=1)
        ax.set_title(titulo, loc="left", fontsize=8.5)
        ax.set_ylabel(etiqueta, fontsize=8)
        ax.set_xticks(d["k"])
        ax.set_xlabel("k")
        _limpiar(ax)
    ejes[2].axhline(0.8, color=SERIE[2], linewidth=1, linestyle=(0, (2, 2)))
    sub = f"Línea gris: k elegido ({k}), el de mayor silhouette entre los estables (ARI >= 0.80, línea naranja)."
    _titulo(fig, "Selección del número de perfiles", sub)
    _guardar(fig, "07_seleccion_k.png", sub)


def pca_varianza():
    v, c = _t("pca_varianza.csv"), _t("pca_cargas.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8, 3.2), dpi=200, gridspec_kw={"width_ratios": [1, 1.3]})
    barras = a1.bar(v["componente"], 100 * v["varianza_explicada"], color=SERIE[1], width=0.6)
    for b, val in zip(barras, v["varianza_explicada"]):
        a1.text(b.get_x() + b.get_width() / 2, 100 * val + 1, f"{100 * val:.0f} %", ha="center", fontsize=8.5)
    a1.set_ylabel("% de la varianza")
    a1.set_ylim(0, 60)
    a1.set_title("Varianza explicada", loc="left", fontsize=9.5)
    _limpiar(a1)
    componentes = [col for col in c.columns if col.startswith("PC")]
    matriz = c.select(componentes).to_numpy()
    im = a2.imshow(matriz, cmap=DIVERGENTE, vmin=-1, vmax=1, aspect="auto")
    a2.set_xticks(range(len(componentes)), componentes)
    a2.set_yticks(range(c.height), [RASGOS[r] for r in c["rasgo"]], fontsize=8)
    for i in range(matriz.shape[0]):
        for j in range(matriz.shape[1]):
            a2.text(j, i, f"{matriz[i, j]:+.2f}", ha="center", va="center", fontsize=8, color=TINTA)
    a2.set_title("Cargas de cada rasgo", loc="left", fontsize=9.5)
    a2.tick_params(length=0)
    fig.colorbar(im, ax=a2, shrink=0.8)
    sub = "Componentes principales de los tres rasgos estandarizados de la corrida principal."
    _titulo(fig, "Estructura de los datos (PCA)", sub)
    _guardar(fig, "08_pca_varianza_cargas.png", sub)


def pca_perfiles():
    d = _t("celdas_pca.csv")
    v = _t("pca_varianza.csv")["varianza_explicada"].to_list()
    fig, ejes = plt.subplots(1, 5, figsize=(10, 2.7), dpi=200, sharex=True, sharey=True)
    for ax, p in zip(ejes, _perfiles()):
        resto, este = d.filter(pl.col("perfil") != p), d.filter(pl.col("perfil") == p)
        ax.scatter(resto["PC1"], resto["PC2"], s=3, color=REJILLA, linewidths=0)
        ax.scatter(este["PC1"], este["PC2"], s=5, color=SERIE[p], linewidths=0)
        ax.set_title(_nombre_perfil(p), loc="left", fontsize=7.5)
        ax.set_xlabel(f"PC1 ({100 * v[0]:.0f} %)", fontsize=8)
        _limpiar(ax, "both")
    ejes[0].set_ylabel(f"PC2 ({100 * v[1]:.0f} %)", fontsize=8)
    sub = "Cada punto es una celda. Cada panel resalta un perfil; en gris, el resto."
    _titulo(fig, "Perfiles en el plano de los dos primeros componentes", sub)
    _guardar(fig, "09_pca_perfiles.png", sub)


def rasgos_por_perfil():
    d = _t("celdas_perfil.csv")
    fig, ejes = plt.subplots(1, 4, figsize=(9.4, 3.7), dpi=200)
    for ax, (col, nombre) in zip(ejes, RASGOS.items()):
        datos = [100 * d.filter(pl.col("perfil") == p)[col].to_numpy() for p in _perfiles()]
        caja = ax.boxplot(datos, patch_artist=True, widths=0.6, showfliers=False,
                          medianprops={"color": TINTA, "linewidth": 1.2}, whiskerprops={"color": TINTA_2},
                          capprops={"color": TINTA_2})
        for parche, p in zip(caja["boxes"], _perfiles()):
            parche.set(facecolor=SERIE[p], edgecolor=SUPERFICIE)
        ax.set_xticks(range(1, len(datos) + 1), [str(p) for p in _perfiles()])
        ax.set_xlabel("Perfil", fontsize=8)
        ax.set_title(nombre, loc="left", fontsize=8.5)
        if col != "volatilidad":
            ax.axhline(0, color=NEUTRO, linewidth=0.8)
        _limpiar(ax)
    ejes[0].set_ylabel("Puntos porcentuales")
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=SERIE[p]) for p in _perfiles()],
               labels=[_nombre_perfil(p) for p in _perfiles()], frameon=False, fontsize=7.5, ncol=3,
               loc="lower center", bbox_to_anchor=(0.5, 0))
    sub = "Celdas sin ponderar; la caja va del cuartil 1 al 3 y los bigotes cubren 1.5 veces ese rango."
    _titulo(fig, "Rasgos por perfil", sub)
    _guardar(fig, "10_rasgos_por_perfil.png", sub, abajo=0.45)


def robustez():
    m, s = _t("robustez_metodos.csv"), _t("sensibilidad_corridas.csv")
    etiquetas = {"ns": "Sin secciones con NS alto", "volatilidad": "Con volatilidad (4 rasgos)",
                 "region": "Por circunscripción", "nacional": "Referencia nacional"}
    filas = ([(f"{r['metodo']}, sin pesos", r["ARI_vs_kmeans"], 1) for r in m.iter_rows(named=True)]
             + [(f"{etiquetas[r['corrida']]} (k={r['k']})", r["ARI_vs_principal"], 2) for r in s.iter_rows(named=True)])
    filas = sorted(filas, key=lambda f: f[1])
    fig, ax = plt.subplots(figsize=(7.4, 3.4), dpi=200)
    barras = ax.barh([f[0] for f in filas], [f[1] for f in filas], color=[SERIE[f[2]] for f in filas], height=0.6)
    for b, f in zip(barras, filas):
        ax.text(f[1] + 0.015, b.get_y() + b.get_height() / 2, f"{f[1]:.2f}", va="center", fontsize=8.5)
    ax.set_xlim(0, 1.08)
    ax.set_xlabel("ARI frente a la asignación principal (1 = idéntica, 0 = al azar)")
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=SERIE[1]), plt.Rectangle((0, 0), 1, 1, color=SERIE[2])],
              labels=["Otro algoritmo, mismos datos", "k-means con otros datos o rasgos"], frameon=False, fontsize=8,
              loc="lower right")
    _limpiar(ax, "x")
    sub = "Corrida principal: k-means ponderado, 3 rasgos, referencia por entidad, k = 5."
    _titulo(fig, "Robustez de los perfiles", sub)
    _guardar(fig, "11_robustez_metodos.png", sub)


def cruces():
    fig, ejes = plt.subplots(1, 2, figsize=(8.4, 3.6), dpi=200)
    for ax, (nombre, titulo) in zip(ejes, [("ward", "k-means frente a Ward"), ("mezcla", "k-means frente a mezcla gaussiana")]):
        d = _t(f"robustez_cruce_{nombre}.csv")
        col = f"grupo_{nombre}"
        k = int(d["perfil_kmeans"].max())
        matriz = np.zeros((k, k))
        for r in d.iter_rows(named=True):
            matriz[r["perfil_kmeans"] - 1, r[col] - 1] = r["LN"]
        matriz = 100 * matriz / matriz.sum(axis=1, keepdims=True)
        ax.imshow(matriz, cmap=SECUENCIAL, vmin=0, vmax=100)
        for i in range(k):
            for j in range(k):
                ax.text(j, i, f"{matriz[i, j]:.0f}", ha="center", va="center", fontsize=8,
                        color="white" if matriz[i, j] > 55 else TINTA)
        ax.set_xticks(range(k), [str(i + 1) for i in range(k)])
        ax.set_yticks(range(k), [str(i + 1) for i in range(k)])
        ax.set_xlabel(f"Grupo del otro método (numerado por nivel)", fontsize=8)
        ax.set_ylabel("Perfil de k-means", fontsize=8)
        ax.set_title(titulo, loc="left", fontsize=9.5)
        ax.tick_params(length=0)
    sub = "Porcentaje de la lista nominal media de cada perfil que el otro método pone en cada grupo (cada fila suma 100)."
    _titulo(fig, "Coincidencia entre métodos", sub)
    _guardar(fig, "12_cruce_metodos.png", sub)


# ---------- (c) Cohortes y distritos ----------

def cohortes_trayectoria():
    d = _t("cohortes_participacion.csv")
    jovenes = ["1986-1990", "1991-1995", "1996-2000", "2001-2005"]
    fig, ax = plt.subplots(figsize=(7.6, 4), dpi=200)
    for c in d["cohorte"].unique().sort().to_list():
        if c in jovenes:
            continue
        s = d.filter(pl.col("cohorte") == c).sort("AELEC")
        ax.plot(s["edad_media"], 100 * s["rel"], color=REJILLA, linewidth=1.2)
    for i, c in enumerate(jovenes, start=1):
        s = d.filter(pl.col("cohorte") == c).sort("AELEC")
        ax.plot(s["edad_media"], 100 * s["rel"], color=SERIE[i], linewidth=2, marker="o", markersize=5,
                markeredgecolor=SUPERFICIE, markeredgewidth=1.2, label=f"Nacidos en {c}")
    ax.axhline(0, color=NEUTRO, linewidth=0.8)
    ax.set_xlabel("Edad media de la cohorte en la elección")
    ax.set_ylabel("Participación relativa a su entidad (pp)")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    _limpiar(ax)
    sub = "Cada línea es una cohorte quinquenal seguida de 2009 a 2024; en gris, las cohortes mayores. Pseudo-panel: no son las mismas personas."
    _titulo(fig, "Trayectoria de las cohortes", sub)
    _guardar(fig, "13_cohortes_trayectoria.png", sub)


def primer_voto():
    d = _t("efecto_primer_voto.csv")
    fig, ax = plt.subplots(figsize=(7.6, 3.8), dpi=200)
    x = d["nacimiento"].to_numpy()
    ax.axhline(0, color=NEUTRO, linewidth=0.8)
    for col, i, etiqueta in [("rel_primera", 1, "Primera elección (18 a 20 años)"), ("rel_siguiente", 2, "Tres años después")]:
        ax.scatter(x, 100 * d[col].cast(pl.Float64).fill_null(np.nan).to_numpy(), color=SERIE[i], s=40, edgecolors=SUPERFICIE, linewidths=1.2,
                   label=etiqueta, zorder=3)
    for r in d.iter_rows(named=True):
        if r["rel_siguiente"] is not None:
            ax.plot([r["nacimiento"]] * 2, [100 * r["rel_primera"], 100 * r["rel_siguiente"]], color=NEUTRO, linewidth=1, zorder=2)
    for r in d.filter(pl.col("edad_primera") == 18).iter_rows(named=True):
        ax.text(r["nacimiento"], 100 * r["rel_primera"] + 1.2, "18", ha="center", fontsize=7, color=TINTA_2)
    ax.set_xticks(x, [str(v) for v in x], rotation=60, fontsize=7.5)
    ax.set_xlabel("Año de nacimiento (aprox.)")
    ax.set_ylabel("Participación relativa a su entidad (pp)")
    ax.legend(frameon=False, fontsize=8, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
    _limpiar(ax)
    sub = "Quien vota por primera vez a los 18 participa por encima de su entidad; tres años después cae por debajo."
    _titulo(fig, "Efecto del primer voto", sub)
    _guardar(fig, "14_efecto_primer_voto.png", sub)


def cohortes_perfil():
    d = _t("cohortes_por_perfil.csv")
    decenio = (pl.col("cohorte").str.slice(0, 4).cast(pl.Int32) // 10 * 10)
    d = (d.with_columns(decenio.clip(lower_bound=1940).alias("dec")).group_by("perfil", "dec").agg(pl.col("pct").sum())
         .sort("perfil", "dec"))
    decs = d["dec"].unique().sort().to_list()
    colores = SECUENCIAL(np.linspace(0.12, 1, len(decs)))
    fig, ax = plt.subplots(figsize=(7.6, 3.9), dpi=200)
    izquierda = np.zeros(len(_perfiles()))
    for dec, color in zip(decs, colores):
        valores = np.array([d.filter((pl.col("perfil") == p) & (pl.col("dec") == dec))["pct"].sum() for p in _perfiles()])
        ax.barh([_nombre_perfil(p) for p in _perfiles()], valores, left=izquierda, color=color, edgecolor=SUPERFICIE,
                linewidth=1.5, label="antes de 1950" if dec == 1940 else f"{dec}s", height=0.65)
        izquierda += valores
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("% de la lista nominal 2024 del perfil")
    ax.legend(frameon=False, fontsize=7.5, ncol=len(decs), loc="upper center", bbox_to_anchor=(0.45, -0.3), title="Década de nacimiento",
              title_fontsize=8)
    _limpiar(ax, "x")
    sub = "Composición generacional de cada perfil en 2024."
    _titulo(fig, "Cohortes que forman cada perfil", sub)
    _guardar(fig, "15_cohortes_por_perfil.png", sub)


def distritos_rasgos():
    d = _t("distritos_trayectoria.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.4, 3.6), dpi=200)
    for ax, (x, y) in zip((a1, a2), [("nivel", "brecha"), ("nivel", "tendencia")]):
        ax.scatter(100 * d[x], 100 * d[y], s=14, color=SERIE[1], alpha=0.75, edgecolors=SUPERFICIE, linewidths=0.4)
        ax.axhline(0, color=NEUTRO, linewidth=0.8)
        ax.axvline(0, color=NEUTRO, linewidth=0.8)
        ax.set_xlabel(f"{RASGOS[x]} (pp)", fontsize=8.5)
        ax.set_ylabel(f"{RASGOS[y]} (pp)", fontsize=8.5)
        _limpiar(ax, "both")
    sub = f"{d.height} distritos federales en el marco 2021, 2009 a 2024. Participación relativa a su entidad."
    _titulo(fig, "Rasgos de participación por distrito", sub)
    _guardar(fig, "16_distritos_rasgos.png", sub)


def distritos_heatmap():
    d = _t("distritos_trayectoria.csv").sort("EDOCVE", "DEF_2021")
    matriz = 100 * d.select([f"rel_{a}" for a in ELECCIONES]).to_numpy()
    fig, ax = plt.subplots(figsize=(6.4, 9.2), dpi=200)
    im = ax.imshow(matriz, cmap=DIVERGENTE, vmin=-12, vmax=12, aspect="auto", interpolation="nearest")
    ax.set_xticks(range(len(ELECCIONES)), ELECCIONES)
    cortes = d.with_row_index("i").group_by("EDOCVE").agg(pl.col("i").min().alias("ini"), pl.col("i").max().alias("fin")).sort("EDOCVE")
    filas = list(cortes.iter_rows(named=True))
    centro = lambda r: (r["ini"] + r["fin"]) / 2
    # Entidades alternadas a la izquierda y a la derecha para que las de pocos distritos no se encimen.
    ax.set_yticks([centro(r) for r in filas[0::2]], [contenido.NOMBRES_ENTIDAD[r["EDOCVE"]] for r in filas[0::2]], fontsize=6.5)
    derecha = ax.secondary_yaxis("right")
    derecha.set_yticks([centro(r) for r in filas[1::2]], [contenido.NOMBRES_ENTIDAD[r["EDOCVE"]] for r in filas[1::2]], fontsize=6.5)
    derecha.tick_params(length=0)
    derecha.spines["right"].set_visible(False)
    for r in filas:
        ax.axhline(r["fin"] + 0.5, color=SUPERFICIE, linewidth=0.8)
    ax.tick_params(length=0)
    barra = fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.6, pad=0.04, aspect=35)
    barra.set_label("Participación relativa a su entidad (pp)", fontsize=8)
    sub = "Una fila por distrito federal (marco 2021), agrupados por entidad. Azul: arriba de su entidad; rojo: abajo."
    _titulo(fig, "Trayectoria de los distritos federales", sub)
    _guardar(fig, "17_distritos_trayectoria.png", sub)


def circunscripciones():
    d = _t("circunscripcion_composicion.csv").sort("circunscripcion")
    etiquetas = [f"{c}. {SEDE_CIRCUNSCRIPCION[c]}" for c in d["circunscripcion"]]
    fig, ax = plt.subplots(figsize=(7.6, 3.4), dpi=200)
    izquierda = np.zeros(d.height)
    for p in _perfiles():
        v = d[f"pct_perfil_{p}"].to_numpy()
        ax.barh(etiquetas, v, left=izquierda, color=SERIE[p], edgecolor=SUPERFICIE, linewidth=1.5, height=0.65, label=_nombre_perfil(p))
        for y, (iz, val) in enumerate(zip(izquierda, v)):
            if val >= 8:
                ax.text(iz + val / 2, y, f"{val:.0f}", ha="center", va="center", fontsize=7.5, color=TINTA)
        izquierda += v
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("% de la lista nominal 2024")
    ax.legend(frameon=False, fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.42, -0.22))
    _limpiar(ax, "x")
    sub = "Circunscripciones del acuerdo INE/CG130/2023 (sede entre paréntesis en el eje)."
    _titulo(fig, "Perfiles por circunscripción", sub)
    _guardar(fig, "18_perfiles_por_circunscripcion.png", sub)


def distritos_dominante():
    d23, d21 = _t("distritos_composicion_2023.csv"), _t("distritos_composicion_2021.csv")
    fig, ax = plt.subplots(figsize=(7.6, 3.2), dpi=200)
    y = np.arange(len(_perfiles()))
    for desplazamiento, d, color, etiqueta in [(-0.18, d23, SERIE[1], "Marco 2023 (vigente)"), (0.18, d21, NEUTRO, "Marco 2021")]:
        conteo = [d.filter(pl.col("perfil_dominante") == p).height for p in _perfiles()]
        barras = ax.barh(y + desplazamiento, conteo, height=0.34, color=color, label=etiqueta)
        for b, c in zip(barras, conteo):
            ax.text(c + 2, b.get_y() + b.get_height() / 2, str(c), va="center", fontsize=7.5)
    ax.set_yticks(y, [_nombre_perfil(p) for p in _perfiles()], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Distritos federales")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    _limpiar(ax, "x")
    sub = "Perfil con mayor peso en la lista nominal 2024 de cada distrito. La mayoría tiene mezcla: ver distritos_composicion_*.csv."
    _titulo(fig, "Perfil de mayor peso por distrito", sub)
    _guardar(fig, "19_distritos_perfil_dominante.png", sub)


FIGURAS = [piramide, participacion_tipo, participacion_entidad, curva_edad, distribucion_ns, distribucion_rasgos,
           seleccion_k, pca_varianza, pca_perfiles, rasgos_por_perfil, robustez, cruces,
           cohortes_trayectoria, primer_voto, cohortes_perfil, distritos_rasgos, distritos_heatmap, circunscripciones,
           distritos_dominante]


def generar_todo() -> list[str]:
    ESTADISTICAS.mkdir(parents=True, exist_ok=True)
    for f in FIGURAS:
        f()
    return sorted(p.name for p in ESTADISTICAS.glob("*.png"))
