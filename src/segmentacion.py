"""Rasgos de comportamiento, k-means ponderado, selección de k y estabilidad (RF-07 a RF-09)."""
import numpy as np
import polars as pl
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from configuracion import ELECCIONES, INTERMEDIAS, PRESIDENCIALES, RANGO_K

NOMBRES_RASGOS = ["nivel", "brecha", "tendencia"]


def matriz_rasgos(ancha: pl.DataFrame) -> np.ndarray:
    """Tres rasgos que separan el nivel de la forma en el tiempo (RF-07).

    nivel: participación relativa media. brecha: media en presidenciales menos media en intermedias.
    tendencia: pendiente de la participación relativa por elección.
    """
    rel = np.column_stack([ancha[f"rel_{e}"].to_numpy() for e in ELECCIONES])
    pres = [ELECCIONES.index(e) for e in PRESIDENCIALES]
    inter = [ELECCIONES.index(e) for e in INTERMEDIAS]
    x = np.arange(len(ELECCIONES)) - (len(ELECCIONES) - 1) / 2
    return np.column_stack([rel.mean(axis=1), rel[:, pres].mean(axis=1) - rel[:, inter].mean(axis=1), rel @ x / (x ** 2).sum()])


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


def etiquetas_por_nivel(modelo: KMeans, rasgos: np.ndarray, peso: np.ndarray) -> np.ndarray:
    """Numera los perfiles 1..k por nivel medio ascendente, para que la numeración sea estable y legible."""
    k = modelo.n_clusters
    nivel = {c: np.average(rasgos[modelo.labels_ == c, 0], weights=peso[modelo.labels_ == c]) for c in range(k)}
    orden = {c: i + 1 for i, c in enumerate(sorted(nivel, key=nivel.get))}
    return np.array([orden[c] for c in modelo.labels_])
