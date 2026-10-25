import numpy as np
import polars as pl
import pytest

import segmentacion as seg
from configuracion import ELECCIONES


def datos_separables(n=40, grupos=4, semilla=0):
    rng = np.random.default_rng(semilla)
    centros = np.array([[0, 0, 0], [6, 0, 0], [0, 6, 0], [0, 0, 6]])[:grupos]
    Z = np.vstack([c + rng.normal(0, 0.3, (n, 3)) for c in centros])
    return Z, np.ones(len(Z))


def test_misma_semilla_da_las_mismas_etiquetas():
    Z, w = datos_separables()
    a = seg.segmentar(Z, 4, 7, w).labels_
    b = seg.segmentar(Z, 4, 7, w).labels_
    assert (a == b).all()


@pytest.mark.parametrize("k", [3, 7])
def test_k_fuera_de_4_a_6_falla(k):
    Z, w = datos_separables()
    with pytest.raises(ValueError):
        seg.segmentar(Z, k, 1, w)


def test_estabilidad_alta_en_datos_separables():
    Z, w = datos_separables()
    tabla, _ = seg.evaluar_k(Z, w, semilla=1, ks=[4], repeticiones=3)
    fila = tabla.row(0, named=True)
    assert fila["silhouette_sin_pesos"] > 0.8
    assert fila["ARI_semillas_min"] > 0.99 and fila["ARI_submuestras_min"] > 0.99


def test_elegir_k_prefiere_el_estable_aunque_otro_tenga_mas_silhouette():
    sel = pl.DataFrame({"k": [4, 5], "silhouette_sin_pesos": [0.2, 0.3],
                        "ARI_semillas_media": [0.95, 0.95], "ARI_submuestras_media": [0.9, 0.5]})
    assert seg.elegir_k(sel) == 4


def test_matriz_de_rasgos_forma_y_sin_nulos():
    columnas = {f"rel_{e}": [0.1 * i, -0.05] for i, e in enumerate(ELECCIONES)}
    m = seg.matriz_rasgos(pl.DataFrame(columnas))
    assert m.shape == (2, 3) and not np.isnan(m).any()


def test_rasgos_separan_brecha_de_nivel():
    # Presidenciales (2012, 2018, 2024) +0.1 e intermedias -0.1: nivel 0, brecha 0.2
    rel = {f"rel_{e}": [0.1 if e in (2012, 2018, 2024) else -0.1] for e in ELECCIONES}
    nivel, brecha, _ = seg.matriz_rasgos(pl.DataFrame(rel))[0]
    assert nivel == pytest.approx(0) and brecha == pytest.approx(0.2)


def test_perfiles_se_numeran_por_nivel_ascendente():
    Z, w = datos_separables()
    modelo = seg.segmentar(Z, 4, 3, w)
    perfil = seg.etiquetas_por_nivel(modelo, Z, w)
    niveles = [Z[perfil == i, 0].mean() for i in range(1, 5)]
    assert niveles == sorted(niveles)
