"""Variantes de segmentación de la spec 004: rasgos ampliados, Gower, K-Prototypes, consenso y mezcla gaussiana."""
from collections.abc import Callable

import numpy as np
import polars as pl
from kmodes.kprototypes import KPrototypes
from scipy.optimize import linear_sum_assignment, nnls
from scipy.spatial.distance import pdist, squareform
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture

import segmentacion as seg
from configuracion import RANGO_K

RASGOS_BASE = seg.NOMBRES_RASGOS_VOLATILIDAD   # D1
MINIMO_LN_ANCLA = 5000   # D11: lista nominal media mínima para que una celda pueda anclar un arquetipo
CODIGO_TIPOSEC = {"U": 0, "M": 1, "R": 2}


def matriz_mixta(ancha: pl.DataFrame) -> dict:
    """Bloques de las distancias mixtas (D3): 4 rasgos, edad ordinal (grupo 0 a 14) y categóricas (sexo, tipo de sección)."""
    return {"num": seg.matriz_rasgos(ancha, con_volatilidad=True),
            "ordinal": ancha["g"].to_numpy().astype(float),
            "cat": np.column_stack([ancha["SEXO"].to_numpy(),
                                    ancha["TIPOSEC"].replace_strict(CODIGO_TIPOSEC, return_dtype=pl.Int8).to_numpy()]),
            "peso": ancha["LN_medio"].to_numpy().astype(float)}


def rasgos_pca_r(ancha: pl.DataFrame, peso: np.ndarray, varianza: float = 0.90) -> tuple[np.ndarray, PCA]:
    """Componentes principales ponderadas de los 6 valores de participación relativa, más la volatilidad.

    Todo queda en puntos de participación y no se estandariza: estandarizar igualaría el peso de cada componente.
    """
    r = seg.rel(ancha)
    centrada = r - np.average(r, axis=0, weights=peso)
    modelo = PCA(svd_solver="full").fit(centrada * np.sqrt(peso / peso.mean())[:, None])
    n = int(np.searchsorted(np.cumsum(modelo.explained_variance_ratio_), varianza) + 1)
    return np.column_stack([centrada @ modelo.components_[:n].T, r.std(axis=1)]), modelo


def gower(num: np.ndarray, ordinal: np.ndarray, cat: np.ndarray, peso_cat: float = 1.0) -> np.ndarray:
    """Distancia de Gower (n × n) entre 0 y 1. Continuas y ordinal: |xi - xj| / rango; categóricas: 0 si coinciden, 1 si no.

    `peso_cat` escala el bloque categórico (D5).
    """
    cont = np.column_stack([num, ordinal])
    rango = np.ptp(cont, axis=0)
    rango[rango == 0] = 1.0
    d_cont = pdist(cont / rango, "cityblock")
    d_cat = pdist(cat, "hamming") * cat.shape[1]
    return squareform((d_cont + peso_cat * d_cat) / (cont.shape[1] + peso_cat * cat.shape[1]))


def k_medoides(D: np.ndarray, k: int, peso: np.ndarray, semilla: int, n_init: int = 5, iter_max: int = 100):
    """k-medoides ponderado: inicio tipo k-means++ e iteración alterna. Devuelve (etiquetas, medoides) de menor costo."""
    rng = np.random.default_rng(semilla)
    p0 = peso / peso.sum()
    mejor_costo, mejor = np.inf, None
    for _ in range(n_init):
        med = [int(rng.choice(len(D), p=p0))]
        for _ in range(k - 1):
            p = peso * D[:, med].min(axis=1) ** 2
            med.append(int(rng.choice(len(D), p=p / p.sum())))
        med = np.array(med)
        for _ in range(iter_max):
            etq = D[:, med].argmin(axis=1)
            nuevos = med.copy()
            for c in range(k):
                idx = np.flatnonzero(etq == c)
                if len(idx):
                    nuevos[c] = idx[np.argmin(D[np.ix_(idx, idx)] @ peso[idx])]
            if (nuevos == med).all():
                break
            med = nuevos
        costo = float(D[:, med].min(axis=1) @ peso)
        if costo < mejor_costo:
            mejor_costo, mejor = costo, (D[:, med].argmin(axis=1), med)
    return mejor


def kprototipos(mixta: dict, k: int, semilla: int, gamma: float | None = None, n_init: int = 3) -> np.ndarray:
    """K-Prototypes: 4 rasgos y edad estandarizados como numéricas; sexo y tipo de sección como categóricas.

    `gamma` (peso de las categóricas) queda en el valor de kmodes si es None: la mitad de la desviación estándar numérica.
    """
    num = seg.estandarizar(np.column_stack([mixta["num"], mixta["ordinal"]]))
    X = np.column_stack([num, mixta["cat"]]).astype(object)
    modelo = KPrototypes(n_clusters=k, init="Huang", n_init=n_init, gamma=gamma, random_state=semilla, n_jobs=1)
    return modelo.fit_predict(X, categorical=[num.shape[1], num.shape[1] + 1], sample_weight=mixta["peso"])


def consenso(Z: np.ndarray, k: int, peso: np.ndarray, semilla: int, n_por_metodo: int = 100, fraccion: float = 0.8) -> dict:
    """Co-asociación de n_por_metodo particiones de k-means, Ward y mezcla gaussiana, y partición final por enlace promedio.

    Cada partición usa una submuestra elegida con probabilidad proporcional a la lista nominal: así Ward y la mezcla,
    que no aceptan pesos, varían entre corridas y quedan ponderados.
    """
    n = len(Z)
    rng = np.random.default_rng(semilla)
    juntos = np.zeros((n, n), np.float32)
    vistos = np.zeros((n, n), np.float32)
    p = peso / peso.sum()
    for metodo in ("kmeans", "ward", "gmm"):
        for _ in range(n_por_metodo):
            idx = np.sort(rng.choice(n, size=int(fraccion * n), replace=False, p=p))
            s = int(rng.integers(1_000_000))
            if metodo == "kmeans":
                e = KMeans(k, n_init=1, random_state=s).fit_predict(Z[idx], sample_weight=peso[idx])
            elif metodo == "ward":
                e = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(Z[idx])
            else:
                e = GaussianMixture(k, covariance_type="full", random_state=s).fit_predict(Z[idx])
            juntos[np.ix_(idx, idx)] += e[:, None] == e[None, :]
            vistos[np.ix_(idx, idx)] += 1
    C = np.divide(juntos, vistos, out=np.zeros_like(juntos), where=vistos > 0)
    np.fill_diagonal(C, 1.0)
    etq = AgglomerativeClustering(n_clusters=k, metric="precomputed", linkage="average").fit_predict(1.0 - C)
    triu = C[np.triu_indices(n, 1)]
    return {"etiquetas": etq, "coasociacion": C, "PAC": float(((triu > 0.1) & (triu < 0.9)).mean())}


def mezcla(Z: np.ndarray, k: int, peso: np.ndarray, semilla: int, n_init: int = 5) -> GaussianMixture:
    """Mezcla gaussiana de covarianza completa ajustada sobre un remuestreo proporcional a la lista nominal."""
    idx = np.random.default_rng(semilla).choice(len(Z), size=len(Z), replace=True, p=peso / peso.sum())
    return GaussianMixture(k, covariance_type="full", n_init=n_init, random_state=semilla).fit(Z[idx])


def probabilidades(modelo: GaussianMixture, Z: np.ndarray, peso: np.ndarray, referencia: np.ndarray) -> dict:
    """Probabilidad de pertenencia de cada celda, con la componente j alineada al perfil j de `referencia` (1..k).

    La alineación maximiza la lista nominal compartida (algoritmo húngaro).
    """
    prob = modelo.predict_proba(Z)
    k = prob.shape[1]
    compartida = np.array([[peso[referencia == r + 1] @ prob[referencia == r + 1, c] for c in range(k)] for r in range(k)])
    _, orden = linear_sum_assignment(-compartida)
    prob = prob[:, orden]
    pmax = prob.max(axis=1)
    entropia = -(prob * np.log(np.clip(prob, 1e-12, 1))).sum(axis=1) / np.log(k)
    return {"prob": prob, "pmax": pmax, "entropia": entropia,
            "pct_LN_transicion": float(100 * peso[pmax < 0.6].sum() / peso.sum())}


def metricas(Z4: np.ndarray, etq: np.ndarray, peso: np.ndarray) -> dict:
    """Métricas en el espacio común (D2). Davies-Bouldin: menor es mejor; las otras, mayor."""
    share = np.array([peso[etq == c].sum() for c in np.unique(etq)]) / peso.sum()
    return {"silhouette_sin_pesos": float(silhouette_score(Z4, etq)), "davies_bouldin": float(davies_bouldin_score(Z4, etq)),
            "calinski_harabasz": float(calinski_harabasz_score(Z4, etq)), "pct_LN_perfil_menor": float(100 * share.min())}


Ajuste = Callable[[int, int, np.ndarray], np.ndarray]


def evaluar_variante(ajustar: Ajuste, Z4: np.ndarray, peso: np.ndarray, semilla: int, ks=range(RANGO_K[0], RANGO_K[1] + 1),
                     repeticiones: int = 10) -> tuple[pl.DataFrame, dict[int, np.ndarray]]:
    """Estabilidad y métricas de una variante para cada k (RF-03, RF-04).

    `ajustar(k, semilla, idx)` devuelve las etiquetas de las celdas `idx`. Las submuestras se comparan con la partición
    completa en las celdas que comparten, porque no todos los métodos pueden asignar celdas nuevas.
    """
    n = len(Z4)
    todas = np.arange(n)
    rng = np.random.default_rng(semilla)
    filas, particiones = [], {}
    for k in ks:
        ref = ajustar(k, semilla, todas)
        particiones[k] = ref
        ari_sem = [adjusted_rand_score(ref, ajustar(k, s, todas)) for s in range(1, repeticiones + 1)]
        ari_sub = []
        for _ in range(repeticiones):
            idx = np.sort(rng.choice(n, size=int(0.8 * n), replace=False))
            ari_sub.append(adjusted_rand_score(ref[idx], ajustar(k, int(rng.integers(1_000_000)), idx)))
        filas.append({"k": k, **metricas(Z4, ref, peso),
                      "ARI_semillas_media": float(np.mean(ari_sem)), "ARI_semillas_min": float(np.min(ari_sem)),
                      "ARI_submuestras_media": float(np.mean(ari_sub)), "ARI_submuestras_min": float(np.min(ari_sub))})
    return pl.DataFrame(filas), particiones


def ajustadores(ancha: pl.DataFrame, n_consenso: int = 100) -> dict[str, Ajuste]:
    """Función de ajuste de cada variante de RF-02, más la principal actual (`principal`) como base de comparación."""
    mixta = matriz_mixta(ancha)
    peso = mixta["peso"]
    Z3 = seg.estandarizar(seg.matriz_rasgos(ancha))
    Z4 = seg.estandarizar(mixta["num"])
    Xp, _ = rasgos_pca_r(ancha, peso)
    D = gower(mixta["num"], mixta["ordinal"], mixta["cat"])

    def sub(m: dict, idx: np.ndarray) -> dict:
        return {c: v[idx] for c, v in m.items()}

    return {
        "principal": lambda k, s, idx: seg.segmentar(Z3[idx], k, s, peso[idx]).labels_,
        "km4": lambda k, s, idx: seg.segmentar(Z4[idx], k, s, peso[idx]).labels_,
        "pca_r": lambda k, s, idx: seg.segmentar(Xp[idx], k, s, peso[idx]).labels_,
        "gower": lambda k, s, idx: k_medoides(D[np.ix_(idx, idx)], k, peso[idx], s)[0],
        "kproto": lambda k, s, idx: kprototipos(sub(mixta, idx), k, s),
        "consenso": lambda k, s, idx: consenso(Z4[idx], k, peso[idx], s, n_consenso)["etiquetas"],
        "gmm": lambda k, s, idx: mezcla(Z4[idx], k, peso[idx], s).predict(Z4[idx]),
    }


def compuerta(tabla: pl.DataFrame, minimo_ari: float = 0.80, minimo_pct: float = 5.0) -> pl.DataFrame:
    """Criterios 1 a 3 de D4 para cada variante frente a la fila `principal`. El criterio 4 lo decide el equipo."""
    base = tabla.filter(pl.col("variante") == "principal").row(0, named=True)
    return tabla.with_columns(
        ((pl.col("ARI_semillas_media") >= minimo_ari) & (pl.col("ARI_submuestras_media") >= minimo_ari)).alias("c1_estable"),
        ((pl.col("silhouette_sin_pesos") >= base["silhouette_sin_pesos"])
         & (pl.col("davies_bouldin") <= base["davies_bouldin"])).alias("c2_mejor_separacion"),
        (pl.col("pct_LN_perfil_menor") >= minimo_pct).alias("c3_tamano"),
    ).with_columns((pl.col("c1_estable") & pl.col("c2_mejor_separacion") & pl.col("c3_tamano")
                    & (pl.col("variante") != "principal")).alias("cumple_1_a_3"))


def centroides_z(Z4: np.ndarray, etq: np.ndarray, peso: np.ndarray) -> pl.DataFrame:
    """Centroide ponderado en z-score de cada perfil (insumo del radar)."""
    filas = [{"perfil": int(c), **{r: float(np.average(Z4[etq == c, i], weights=peso[etq == c])) for i, r in enumerate(RASGOS_BASE)}}
             for c in np.unique(etq)]
    return pl.DataFrame(filas).sort("perfil")


def lectura_centroide(fila: dict, umbral: float = 0.5) -> str:
    """Rasgos del centroide con |z| >= umbral, como «nivel alto, tendencia baja»."""
    partes = [f"{r} {'alto' if fila[r] > 0 else 'bajo'}" for r in RASGOS_BASE if abs(fila[r]) >= umbral]
    return ", ".join(partes) if partes else "cerca del promedio"


def _nnls_simplex(M: np.ndarray, y: np.ndarray, castigo: float = 200.0) -> np.ndarray:
    """Pesos no negativos que suman 1 tales que M @ pesos ≈ y. Una fila extra con peso alto fuerza la suma (Cutler y Breiman)."""
    coef, _ = nnls(np.vstack([M, castigo * np.ones(M.shape[1])]), np.r_[y, castigo], maxiter=50 * M.shape[1])
    total = coef.sum()
    return coef / total if total > 0 else np.full(len(coef), 1 / len(coef))


def _furthest_sum(X: np.ndarray, k: int, rng: np.random.Generator) -> list[int]:
    """Inicio de Mørup y Hansen: puntos lejanos entre sí. El primero, elegido al azar, se descarta al final."""
    elegidos = [int(rng.integers(len(X)))]
    suma = np.linalg.norm(X - X[elegidos[0]], axis=1)
    for _ in range(k):
        suma[elegidos] = -np.inf
        nuevo = int(np.argmax(suma))
        elegidos.append(nuevo)
        suma += np.linalg.norm(X - X[nuevo], axis=1)
    return elegidos[1:]


def arquetipos(X: np.ndarray, k: int, peso: np.ndarray, semilla: int, candidatas: np.ndarray | None = None,
               n_init: int = 10, iter_max: int = 200, tol: float = 1e-6) -> dict:
    """Análisis de arquetipos ponderado (Cutler y Breiman): X ≈ A·Z con Z = B·X; filas de A y B no negativas y con suma 1.

    Alterna: A por NNLS de cada celda; Z por mínimos cuadrados ponderados; B proyectando Z al casco convexo de las
    celdas `candidatas` (todas si es None; D11 las limita a celdas grandes para que una celda chica no sea un polo).
    Devuelve Z, A, B (k × n, cero fuera de las candidatas), la suma de cuadrados ponderada y la varianza explicada.
    """
    rng = np.random.default_rng(semilla)
    w = peso / peso.mean()
    total = float(w @ ((X - np.average(X, axis=0, weights=w)) ** 2).sum(axis=1))
    idx_c = np.arange(len(X)) if candidatas is None else np.flatnonzero(candidatas)
    Xc = X[idx_c]
    mejor = None
    for _ in range(n_init):
        Bc = np.zeros((k, len(Xc)))
        Bc[np.arange(k), _furthest_sum(Xc, k, rng)] = 1.0
        Z = Bc @ Xc
        A = np.array([_nnls_simplex(Z.T, x) for x in X])
        anterior = np.inf
        for _ in range(iter_max):
            Zw, *_ = np.linalg.lstsq(A.T @ (A * w[:, None]), A.T @ (X * w[:, None]), rcond=None)
            Bc = np.array([_nnls_simplex(Xc.T, z) for z in Zw])
            Z = Bc @ Xc
            A = np.array([_nnls_simplex(Z.T, x) for x in X])
            rss = float(w @ ((X - A @ Z) ** 2).sum(axis=1))
            if anterior - rss < tol * anterior:
                break
            anterior = rss
        if mejor is None or rss < mejor["rss"]:
            B = np.zeros((k, len(X)))
            B[:, idx_c] = Bc
            mejor = {"Z": Z, "A": A, "B": B, "rss": rss}
    return mejor | {"varianza_explicada": 1 - mejor["rss"] / total}


def numerar_arquetipos(r: dict) -> dict:
    """Ordena los arquetipos por nivel (primera columna de Z) ascendente para que la numeración 1..k sea estable."""
    orden = np.argsort(r["Z"][:, 0], kind="stable")
    return r | {"Z": r["Z"][orden], "A": r["A"][:, orden], "B": r["B"][orden]}


def seleccion_arquetipos(X: np.ndarray, peso: np.ndarray, semilla: int, candidatas: np.ndarray | None = None, ks=range(3, 7)):
    """Varianza explicada por número de arquetipos y k del codo (D8): donde más cae la mejora marginal. Devuelve (tabla, k, ajustes).

    La mejora de k es lo que gana frente a k - 1; la caída de k es su mejora menos la de k + 1. Se evalúan los k interiores del rango.
    """
    ks = list(ks)
    ajustes = {k: numerar_arquetipos(arquetipos(X, k, peso, semilla, candidatas)) for k in ks}
    var = [ajustes[k]["varianza_explicada"] for k in ks]
    mejora = [np.nan] + [var[i] - var[i - 1] for i in range(1, len(ks))]
    caida = [np.nan] + [mejora[i] - mejora[i + 1] for i in range(1, len(ks) - 1)] + [np.nan]
    tabla = pl.DataFrame({"k": ks, "varianza_explicada": var, "mejora_frente_a_k_menos_1": mejora, "caida_de_la_mejora": caida})
    k = ks[int(np.nanargmax(caida))]
    return tabla, k, ajustes


def estabilidad_arquetipos(X: np.ndarray, peso: np.ndarray, referencia: np.ndarray, semilla: int, candidatas: np.ndarray | None = None,
                           repeticiones: int = 10, fraccion: float = 0.8) -> pl.DataFrame:
    """Distancia (en z) entre cada arquetipo de referencia y su pareja en submuestras, emparejados con el algoritmo húngaro."""
    rng = np.random.default_rng(semilla)
    k = len(referencia)
    filas = []
    for rep in range(repeticiones):
        idx = np.sort(rng.choice(len(X), size=int(fraccion * len(X)), replace=False))
        cand = None if candidatas is None else candidatas[idx]
        Z = arquetipos(X[idx], k, peso[idx], int(rng.integers(1_000_000)), cand, n_init=5)["Z"]
        dist = np.linalg.norm(referencia[:, None] - Z[None], axis=2)
        fila_ref, col = linear_sum_assignment(dist)
        filas += [{"submuestra": rep + 1, "arquetipo": int(j + 1), "distancia_z": float(dist[j, c])} for j, c in zip(fila_ref, col)]
    return pl.DataFrame(filas)


def mezcla_por_grupo(A: np.ndarray, grupos: np.ndarray, peso: np.ndarray) -> pl.DataFrame:
    """Mezcla media de arquetipos de cada grupo, ponderada por `peso`. Las filas suman 1."""
    filas = [{"grupo": int(g), **{f"arq_{j + 1}": float(np.average(A[grupos == g, j], weights=peso[grupos == g]))
                                   for j in range(A.shape[1])}} for g in np.unique(grupos)]
    return pl.DataFrame(filas).sort("grupo")
