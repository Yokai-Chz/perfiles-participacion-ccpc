import numpy as np
import polars as pl
import pytest
from sklearn.metrics import adjusted_rand_score

import contenido
import experimentos as exp
import figuras
from test_segmentacion import datos_separables


def test_gower_simetrica_diagonal_cero_y_entre_0_y_1():
    rng = np.random.default_rng(0)
    D = exp.gower(rng.normal(size=(30, 4)), rng.integers(0, 15, 30).astype(float), rng.integers(0, 3, (30, 2)))
    assert np.allclose(D, D.T) and np.allclose(np.diag(D), 0)
    assert D.min() >= 0 and D.max() <= 1


def test_gower_caso_a_mano():
    num = np.array([[0.0], [1.0]])
    ordinal = np.array([0.0, 2.0])
    cat = np.array([[0, 1], [0, 2]])
    # continuas: 1/1 + 2/2 = 2; categóricas: una discrepancia de dos; total (2 + 1) / 4
    assert exp.gower(num, ordinal, cat)[0, 1] == pytest.approx(0.75)
    assert exp.gower(num, ordinal, cat, peso_cat=2.0)[0, 1] == pytest.approx((2 + 2) / (2 + 4))


def test_k_medoides_recupera_grupos_separables():
    Z, w = datos_separables()
    verdad = np.repeat(np.arange(4), 40)
    D = np.sqrt(((Z[:, None] - Z[None]) ** 2).sum(-1))
    etq, med = exp.k_medoides(D, 4, w, semilla=3)
    assert adjusted_rand_score(verdad, etq) == pytest.approx(1.0) and len(set(med)) == 4


def test_consenso_en_datos_separables():
    Z, w = datos_separables()
    r = exp.consenso(Z, 4, w, semilla=1, n_por_metodo=5)
    assert adjusted_rand_score(np.repeat(np.arange(4), 40), r["etiquetas"]) == pytest.approx(1.0)
    assert r["PAC"] < 0.01
    assert np.allclose(r["coasociacion"], r["coasociacion"].T)


def test_probabilidades_suman_uno_y_se_alinean_con_la_referencia():
    Z, w = datos_separables()
    verdad = np.repeat(np.arange(1, 5), 40)
    pr = exp.probabilidades(exp.mezcla(Z, 4, w, semilla=2), Z, w, verdad)
    assert np.allclose(pr["prob"].sum(axis=1), 1)
    assert (pr["prob"].argmax(axis=1) + 1 == verdad).all()
    assert pr["pct_LN_transicion"] == pytest.approx(0.0)


def test_metricas_en_datos_separables():
    Z, w = datos_separables()
    m = exp.metricas(Z, np.repeat(np.arange(4), 40), w)
    assert m["silhouette_sin_pesos"] > 0.8 and m["davies_bouldin"] < 0.3
    assert m["pct_LN_perfil_menor"] == pytest.approx(25.0)


def test_evaluar_variante_estable_en_datos_separables():
    Z, w = datos_separables()
    ajustar = lambda k, s, idx: exp.KMeans(k, n_init=5, random_state=s).fit_predict(Z[idx])
    tabla, part = exp.evaluar_variante(ajustar, Z, w, semilla=1, ks=[4], repeticiones=3)
    fila = tabla.row(0, named=True)
    assert fila["ARI_semillas_min"] == pytest.approx(1.0) and fila["ARI_submuestras_min"] == pytest.approx(1.0)
    assert len(part[4]) == len(Z)


def test_compuerta_exige_los_tres_criterios():
    t = pl.DataFrame({"variante": ["principal", "a", "b", "c"],
                      "ARI_semillas_media": [0.9, 0.9, 0.7, 0.9], "ARI_submuestras_media": [0.9, 0.9, 0.9, 0.9],
                      "silhouette_sin_pesos": [0.2, 0.3, 0.3, 0.3], "davies_bouldin": [1.3, 1.2, 1.2, 1.2],
                      "pct_LN_perfil_menor": [10.0, 10.0, 10.0, 3.0]})
    assert exp.compuerta(t)["cumple_1_a_3"].to_list() == [False, True, False, False]


def test_centroides_ponderados_y_lectura():
    Z = np.array([[1.0, 0, 0, 0], [3.0, 0, 0, 0], [-1.0, 0, 0, -2]])
    c = exp.centroides_z(Z, np.array([1, 1, 2]), np.array([3.0, 1.0, 1.0]))
    assert c.filter(pl.col("perfil") == 1)["nivel"].item() == pytest.approx(1.5)
    assert exp.lectura_centroide(c.row(1, named=True)) == "nivel bajo, volatilidad bajo"


@pytest.mark.parametrize("edad, tipo, centroide, esperado", [
    ({"20-24": 40.0, "25-29": 30.0}, {"U": 90.0, "R": 5.0, "M": 5.0},
     {"nivel": -1.0, "brecha": 0.8, "tendencia": 0.1, "volatilidad": 0.0}, "Jóvenes urbanos de baja participación y de coyuntura presidencial"),
    ({"65-69": 40.0, "70-74": 30.0}, {"U": 40.0, "R": 35.0, "M": 25.0},
     {"nivel": 0.2, "brecha": 0.0, "tendencia": 1.2, "volatilidad": 0.1}, "Mayores en ascenso"),
    ({"45-49": 50.0}, {"R": 70.0, "U": 20.0, "M": 10.0},
     {"nivel": 0.3, "brecha": -0.9, "tendencia": 0.0, "volatilidad": 0.6}, "Adultez rural con participación sostenida en intermedias y de participación intermitente"),
])
def test_sugerir_nombre(edad, tipo, centroide, esperado):
    assert contenido.sugerir_nombre(centroide, edad, tipo) == esperado


def test_radar_y_mapa_escriben_archivo(tmp_path):
    c = pl.DataFrame({"perfil": [1, 2], "nivel": [0.5, -0.5], "brecha": [1.0, -1.0], "tendencia": [0.0, 0.2], "volatilidad": [-0.3, 0.3]})
    nombres = {1: "Uno", 2: "Dos"}
    figuras.radar_centroides(c, tmp_path / "radar.png", nombres)
    figuras.mapa_centroides(c, tmp_path / "mapa.png", nombres)
    assert (tmp_path / "radar.png").stat().st_size > 0 and (tmp_path / "mapa.png").stat().st_size > 0


def test_nnls_simplex_recupera_una_mezcla_conocida():
    M = np.array([[0.0, 4.0, 0.0], [0.0, 0.0, 4.0]])
    pesos = exp._nnls_simplex(M, M @ np.array([0.5, 0.3, 0.2]))
    assert (pesos >= 0).all() and pesos.sum() == pytest.approx(1.0)
    assert pesos == pytest.approx([0.5, 0.3, 0.2], abs=1e-3)


def triangulo(n=200, semilla=0):
    V = np.array([[0.0, 0.0], [4.0, 0.0], [0.0, 4.0]])
    P = np.random.default_rng(semilla).dirichlet([1, 1, 1], n)
    return np.vstack([V, P @ V]), V


def test_arquetipos_recupera_los_vertices_de_un_triangulo():
    X, V = triangulo()
    r = exp.arquetipos(X, 3, np.ones(len(X)), semilla=1, n_init=3)
    dist = np.linalg.norm(V[:, None] - r["Z"][None], axis=2)
    assert dist.min(axis=1).max() < 0.05
    assert np.allclose(r["A"].sum(axis=1), 1) and (r["A"] >= 0).all()
    assert np.allclose(r["B"].sum(axis=1), 1) and r["varianza_explicada"] > 0.99


def test_arquetipos_duplicar_una_celda_equivale_a_peso_2():
    X, _ = triangulo(n=60, semilla=3)
    peso = np.ones(len(X))
    peso[10] = 2.0
    a = exp.arquetipos(X, 3, peso, semilla=1, n_init=3)
    b = exp.arquetipos(np.vstack([X, X[10]]), 3, np.ones(len(X) + 1), semilla=1, n_init=3)
    ordenar = lambda Z: Z[np.lexsort(Z.T)]
    assert np.allclose(ordenar(a["Z"]), ordenar(b["Z"]), atol=1e-3)
    assert a["varianza_explicada"] == pytest.approx(b["varianza_explicada"], abs=1e-4)


def test_arquetipos_solo_usan_celdas_candidatas():
    X, _ = triangulo()
    candidatas = np.ones(len(X), bool)
    candidatas[:3] = False   # los vértices exactos no pueden ser ancla
    r = exp.arquetipos(X, 3, np.ones(len(X)), semilla=1, candidatas=candidatas, n_init=3)
    assert np.allclose(r["B"][:, :3], 0) and np.allclose(r["B"].sum(axis=1), 1)


def test_seleccion_arquetipos_elige_el_codo():
    X, _ = triangulo()
    tabla, k, _ = exp.seleccion_arquetipos(X, np.ones(len(X)), semilla=1, ks=[2, 3, 4])
    assert k == 3 and tabla["k"].to_list() == [2, 3, 4]


def test_mezcla_por_grupo_pondera_y_suma_uno():
    A = np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])
    m = exp.mezcla_por_grupo(A, np.array([1, 1, 2]), np.array([3.0, 1.0, 1.0]))
    assert m.row(0, named=True) == {"grupo": 1, "arq_1": 0.75, "arq_2": 0.25}
    assert m.select(pl.sum_horizontal("arq_1", "arq_2")).to_series().to_list() == pytest.approx([1.0, 1.0])


def test_mezcla_secciones_promedia_por_lista_nominal(tmp_path):
    import perfiles as per
    filas = pl.DataFrame({"EDOCVE": [1, 1, 1], "SECCION": [10, 10, 11], "TIPOSEC": ["U", "U", "U"], "SEXO": [0, 1, 0],
                          "EDAD": [25, 25, 40], "LN": [300, 100, 50]})
    filas.write_parquet(tmp_path / "ccpc.parquet")
    celdas = pl.DataFrame({"EDOCVE": [1, 1, 1], "TIPOSEC": ["U", "U", "U"], "SEXO": [0, 1, 0], "g": [2, 2, 5],
                           "arq_1": [1.0, 0.0, 0.2], "arq_2": [0.0, 1.0, 0.8]}).with_columns(pl.col("g").cast(pl.Int8))
    mezcla, sin_dato = per.mezcla_secciones(tmp_path / "ccpc.parquet", celdas, ["arq_1", "arq_2"])
    s10 = mezcla.filter(pl.col("SECCION") == 10).row(0, named=True)
    assert s10["arq_1"] == pytest.approx(0.75) and s10["arq_2"] == pytest.approx(0.25) and sin_dato == 0


def test_mezcla_por_perfil_escribe_archivo(tmp_path):
    m = pl.DataFrame({"grupo": [1, 2], "arq_1": [0.7, 0.2], "arq_2": [0.3, 0.8]})
    figuras.mezcla_por_perfil(m, tmp_path / "mezcla.png", {1: "Uno", 2: "Dos"}, {1: "Polo A", 2: "Polo B"})
    assert (tmp_path / "mezcla.png").stat().st_size > 0


def test_nombrar_polos_por_firma_y_no_por_numero():
    z = {1: {"nivel": 0.9, "brecha": 0.1, "tendencia": 0.0, "volatilidad": -2.0},
         2: {"nivel": -1.5, "brecha": 1.8, "tendencia": -0.3, "volatilidad": -0.4},
         3: {"nivel": 0.5, "brecha": 0.9, "tendencia": 3.0, "volatilidad": 2.5},
         4: {"nivel": 0.0, "brecha": -2.0, "tendencia": -1.9, "volatilidad": 1.8}}
    assert contenido.nombrar_polos(z) == {2: "Voto presidencial", 4: "Voto parejo que baja", 3: "Voto que crece", 1: "Voto firme"}


def test_nombrar_polos_falla_si_dos_firmas_coinciden():
    z = {i: {"nivel": 0.0, "brecha": 0.0, "tendencia": 0.0, "volatilidad": 0.0} for i in range(1, 5)}
    z[1] |= {"brecha": 2.0, "tendencia": 3.0}   # el mismo arquetipo tendría la mayor brecha y la mayor tendencia
    z[2] |= {"tendencia": -2.0}
    z[3] |= {"volatilidad": -2.0}
    with pytest.raises(ValueError):
        contenido.nombrar_polos(z)
    with pytest.raises(ValueError):
        contenido.nombrar_polos({1: z[1]})
