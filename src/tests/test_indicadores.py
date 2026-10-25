import polars as pl
import pytest

import indicadores as ind
from configuracion import ELECCIONES


def celdas_sinteticas(**cambios):
    """Dos entidades × dos elecciones, una celda por entidad; permite cambiar columnas."""
    filas = [{"AELEC": a, "EDOCVE": e, "TIPOSEC": "U", "SEXO": 0, "g": 3, "grupo_edad": "30-34",
              "LN": 1000, "SV": sv, "NV": nv, "NS": 0}
             for a in (2012, 2018) for e, sv, nv in [(1, 600, 400), (2, 300, 700)]]
    return pl.DataFrame(filas).with_columns(**{k: pl.lit(v) for k, v in cambios.items()})


def test_edades_89_90_y_125_caen_en_su_grupo():
    df = pl.DataFrame({"EDAD": [18, 19, 20, 89, 90, 125]}).with_columns(ind.indice_grupo_edad())
    df = ind.etiquetar_grupo(df)
    assert df["grupo_edad"].to_list() == ["18-19", "18-19", "20-24", "80-89", "90+", "90+"]


def test_la_tasa_es_cociente_de_sumas_y_no_promedio_de_tasas():
    df = pl.DataFrame({"x": [1, 1], "SV": [1, 90], "NV": [9, 10]})   # tasas 0.10 y 0.90, promedio simple 0.50
    tasa = ind.tasa_participacion(df, ["x"])["tasa"][0]
    assert tasa == pytest.approx(91 / 110)
    assert tasa != pytest.approx(0.5)


def test_denominador_cero_no_divide():
    df = pl.DataFrame({"x": [1], "SV": [0], "NV": [0]})
    assert ind.tasa_participacion(df, ["x"])["tasa"][0] is None


@pytest.mark.parametrize("referencia,por", [("nacional", ["AELEC"]), ("entidad", ["AELEC", "EDOCVE"])])
def test_la_diferencia_relativa_ponderada_suma_cero(referencia, por):
    largo = ind.participacion_relativa(celdas_sinteticas(), referencia)
    assert ind.suma_ponderada_rel(largo, por)["suma_ponderada_rel"].abs().max() < 1e-12


def test_referencia_por_entidad_no_mezcla_entidades():
    largo = ind.participacion_relativa(celdas_sinteticas(), "entidad")
    assert largo["rel"].abs().max() < 1e-12   # una sola celda por entidad: igual a su propia tasa


def test_filtro_de_celdas_pequenas_las_excluye_y_las_reporta():
    base = []
    for e, ln in [(1, 500), (2, 50)]:
        for a in ELECCIONES:
            base.append({"AELEC": a, "EDOCVE": e, "TIPOSEC": "U", "SEXO": 0, "g": 3, "grupo_edad": "30-34",
                         "LN": ln, "SV": 1, "NV": 1, "NS": 0})
    conservadas, excluidas = ind.filtrar_celdas_pequenas(pl.DataFrame(base), umbral=100)
    assert conservadas["EDOCVE"].unique().to_list() == [1]
    assert excluidas["EDOCVE"].to_list() == [2]


def test_la_misma_seccion_en_dos_entidades_no_se_mezcla():
    df = pl.DataFrame({"EDOCVE": [1, 2], "SECCION": [7, 7], "SV": [10, 90], "NV": [90, 10]})
    por_clave = ind.tasa_participacion(df, ["EDOCVE", "SECCION"]).sort("EDOCVE")["tasa"].to_list()
    assert por_clave == [0.1, 0.9]
