"""Rasgos de comportamiento, k-means ponderado, selección de k y estabilidad (RF-07 a RF-09)."""
import numpy as np
import polars as pl
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from configuracion import ELECCIONES, INTERMEDIAS, PRESIDENCIALES, RANGO_K

NOMBRES_RASGOS = ["nivel", "brecha", "tendencia"]
NOMBRES_RASGOS_VOLATILIDAD = NOMBRES_RASGOS + ["volatilidad"]   # variante, spec 002 D2b


def _rel(ancha: pl.DataFrame) -> np.ndarray:
    return np.column_stack([ancha[f"rel_{e}"].to_numpy() for e in ELECCIONES])


def volatilidad(ancha: pl.DataFrame) -> np.ndarray:
    """Desviación estándar de la participación relativa entre las elecciones (spec 002, RF-03)."""
    return _rel(ancha).std(axis=1)


def matriz_rasgos(ancha: pl.DataFrame, con_volatilidad: bool = False) -> np.ndarray:
    """Tres rasgos que separan el nivel de la forma en el tiempo (RF-07), y la volatilidad si se pide.

    nivel: participación relativa media. brecha: media en presidenciales menos media en intermedias.
    tendencia: pendiente de la participación relativa por elección.
    """
    rel = _rel(ancha)
    pres = [ELECCIONES.index(e) for e in PRESIDENCIALES]
    inter = [ELECCIONES.index(e) for e in INTERMEDIAS]
    x = np.arange(len(ELECCIONES)) - (len(ELECCIONES) - 1) / 2
    columnas = [rel.mean(axis=1), rel[:, pres].mean(axis=1) - rel[:, inter].mean(axis=1), rel @ x / (x ** 2).sum()]
    if con_volatilidad:
        columnas.append(rel.std(axis=1))
    return np.column_stack(columnas)


def estandarizar(rasgos: np.ndarray) -> np.ndarray:
    return StandardScaler().fit_transform(rasgos)


def segmentar(Z: np.ndarray, k: int, semilla: int, peso: np.ndarray) -> KMeans:
    """K-means ponderado por lista nominal. Mismos datos y misma semilla dan las mismas etiquetas (RF-08)."""
    if not RANGO_K[0] <= k <= RANGO_K[1]:
        raise ValueError(f"k debe estar entre {RANGO_K[0]} y {RANGO_K[1]}, se recibió {k}")
    return KMeans(n_clusters=k, n_init=20, random_state=semilla).fit(Z, sample_weight=peso)


def evaluar_k(Z: np.ndarray, peso: np.ndarray, semilla: int, ks=range(RANGO_K[0], RANGO_K[1] + 1),
              repeticiones: int = 10) -> tuple[pl.DataFrame, dict[int, KMeans]]:
    """Silhouette (sin pesos: scikit-learn no los admite) y estabilidad por semillas y submuestras (RF-09)."""
    filas, modelos = [], {}
    rng = np.random.default_rng(semilla)
    for k in ks:
        ref = segmentar(Z, k, semilla, peso)
        modelos[k] = ref
        ari_semillas = [adjusted_rand_score(ref.labels_, segmentar(Z, k, s, peso).labels_)
                        for s in range(1, repeticiones + 1)]
        ari_sub = []
        for _ in range(repeticiones):
            idx = rng.choice(len(Z), size=int(0.8 * len(Z)), replace=False)
            sub = segmentar(Z[idx], k, int(rng.integers(1_000_000)), peso[idx])
            ari_sub.append(adjusted_rand_score(ref.labels_, sub.predict(Z)))
        filas.append({"k": k, "inercia": ref.inertia_, "silhouette_sin_pesos": silhouette_score(Z, ref.labels_),
                      "ARI_semillas_media": float(np.mean(ari_semillas)), "ARI_semillas_min": float(np.min(ari_semillas)),
                      "ARI_submuestras_media": float(np.mean(ari_sub)), "ARI_submuestras_min": float(np.min(ari_sub))})
    return pl.DataFrame(filas), modelos


def elegir_k(seleccion: pl.DataFrame, minimo_ari: float = 0.80) -> int:
    """Entre los k estables (ARI medio >= mínimo), el de mayor silhouette. Si ninguno lo es, se evalúan todos."""
    estables = seleccion.filter((pl.col("ARI_semillas_media") >= minimo_ari) & (pl.col("ARI_submuestras_media") >= minimo_ari))
    candidatos = estables if estables.height else seleccion
    return int(candidatos.sort("silhouette_sin_pesos", descending=True)["k"][0])


def numerar_por_nivel(etiquetas: np.ndarray, nivel: np.ndarray, peso: np.ndarray) -> np.ndarray:
    """Renumera los grupos 1..k por nivel medio ponderado ascendente, para que la numeración sea estable y legible."""
    medias = {c: np.average(nivel[etiquetas == c], weights=peso[etiquetas == c]) for c in np.unique(etiquetas)}
    orden = {c: i + 1 for i, c in enumerate(sorted(medias, key=medias.get))}
    return np.array([orden[c] for c in etiquetas])


def etiquetas_por_nivel(modelo: KMeans, rasgos: np.ndarray, peso: np.ndarray) -> np.ndarray:
    """Numera los perfiles de k-means 1..k por nivel medio ascendente."""
    return numerar_por_nivel(modelo.labels_, rasgos[:, 0], peso)


def pca(Z: np.ndarray, nombres: list[str]) -> dict:
    """Componentes principales de los rasgos estandarizados (spec 002, RF-04).

    El signo de cada componente se fija para que su carga de mayor valor absoluto sea positiva.
    """
    modelo = PCA(n_components=Z.shape[1]).fit(Z)
    cargas = modelo.components_.copy()
    signo = np.sign(cargas[np.arange(len(cargas)), np.abs(cargas).argmax(axis=1)])
    cargas *= signo[:, None]
    coords = (Z - modelo.mean_) @ cargas.T
    componentes = [f"PC{i + 1}" for i in range(len(cargas))]
    varianza = pl.DataFrame({"componente": componentes, "varianza_explicada": modelo.explained_variance_ratio_,
                             "acumulada": np.cumsum(modelo.explained_variance_ratio_)})
    tabla_cargas = pl.DataFrame({"rasgo": nombres, **{c: cargas[i] for i, c in enumerate(componentes)}})
    return {"varianza": varianza, "cargas": tabla_cargas, "coordenadas": coords}


def comparar_metodos(Z: np.ndarray, etiquetas: np.ndarray, k: int, semilla: int,
                     ks=range(RANGO_K[0], RANGO_K[1] + 1)) -> tuple[pl.DataFrame, pl.DataFrame, dict]:
    """ARI de k-means frente a Ward y a una mezcla gaussiana con el mismo k, y BIC de la mezcla por k (RF-05).

    Ward y la mezcla gaussiana de scikit-learn no aceptan pesos: se ajustan sin ponderar por lista nominal.
    Devuelve (comparación, BIC por k, etiquetas de cada método).
    """
    ward = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(Z)
    mezclas = {kk: GaussianMixture(n_components=kk, covariance_type="full", n_init=5, random_state=semilla).fit(Z) for kk in ks}
    gmm = mezclas[k].predict(Z)
    comparacion = pl.DataFrame({
        "metodo": ["Ward (jerárquico)", "Mezcla gaussiana"],
        "k": [k, k],
        "usa_pesos": [False, False],
        "ARI_vs_kmeans": [adjusted_rand_score(etiquetas, ward), adjusted_rand_score(etiquetas, gmm)],
    })
    bic = pl.DataFrame({"k": list(ks), "BIC_mezcla": [mezclas[kk].bic(Z) for kk in ks]})
    return comparacion, bic, {"ward": ward, "mezcla": gmm}


def cruce(a: np.ndarray, b: np.ndarray, peso: np.ndarray, nombre_a: str, nombre_b: str) -> pl.DataFrame:
    """Lista nominal compartida entre los grupos de dos asignaciones (tabla de contingencia ponderada)."""
    return (pl.DataFrame({nombre_a: a, nombre_b: b, "LN": peso})
            .group_by(nombre_a, nombre_b).agg(pl.col("LN").sum()).sort(nombre_a, nombre_b))
