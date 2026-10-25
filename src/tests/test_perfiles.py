import polars as pl
import pytest

import perfiles as per


def asignacion(filas):
    """filas: (perfil, g, grupo_edad, LN_2024)."""
    return pl.DataFrame(filas, schema=["perfil", "g", "grupo_edad", "LN_2024"], orient="row").with_columns(
        pl.lit("U").alias("TIPOSEC"), pl.lit(0).alias("SEXO"), pl.lit(1).alias("EDOCVE"))


def test_el_grupo_de_edad_mediano_usa_el_grupo_completo_y_no_la_celda_mayor():
    # Una celda grande de 20-24 (g=1) pero el grupo 50-54 (g=7) suma más y contiene la mediana
    filas = [(1, 1, "20-24", 50)] + [(1, 7, "50-54", 30)] * 3 + [(1, 8, "55-59", 20)]
    mediano = per.grupo_edad_mediano(asignacion(filas))
    assert mediano["grupo_edad_mediano"].to_list() == ["50-54"]


def test_la_distribucion_suma_100_y_rellena_huecos_con_cero():
    filas = [(1, 1, "20-24", 60), (1, 7, "50-54", 40), (2, 1, "20-24", 100)]
    d = per.distribucion_edad(asignacion(filas))
    assert d.filter(pl.col("perfil") == 2)["50-54"][0] == 0.0
    assert d.filter(pl.col("perfil") == 1).drop("perfil").sum_horizontal()[0] == pytest.approx(100)


def test_la_participacion_por_perfil_sale_en_orden_cronologico():
    largo = pl.DataFrame({"perfil": [1] * 3, "AELEC": [2015, 2009, 2012], "SV": [1, 1, 1], "NV": [1, 1, 1]})
    assert per.participacion_por_perfil(largo).columns == ["perfil", "2009", "2012", "2015"]


def test_las_entidades_dominantes_se_cuentan_por_umbral():
    comp = pl.DataFrame({"EDOCVE": [1, 2], "1": [95.0, 50.0], "2": [5.0, 50.0]})
    assert per.entidades_dominantes(comp, umbral=80) == 1


def test_la_composicion_de_cada_seccion_suma_uno(tmp_path):
    datos = pl.DataFrame({"EDOCVE": [1, 1, 1, 2], "SECCION": [5, 5, 5, 5], "TIPOSEC": ["U"] * 4,
                          "SEXO": [0, 1, 0, 0], "EDAD": [20, 20, 60, 20], "LN": [10, 30, 60, 100]})
    ruta = tmp_path / "ccpc.parquet"
    datos.write_parquet(ruta)
    asig = pl.DataFrame({"EDOCVE": [1, 1, 1, 2], "TIPOSEC": ["U"] * 4, "SEXO": [0, 1, 0, 0],
                         "g": [1, 1, 9, 1], "perfil": [1, 2, 2, 1]}).with_columns(pl.col("g").cast(pl.Int8))
    comp, sin_perfil, total = per.composicion_secciones(ruta, asig)
    props = comp.drop("EDOCVE", "SECCION").sum_horizontal().to_list()
    assert props == pytest.approx([1.0, 1.0]) and sin_perfil == 0 and total == 200
    # La sección 5 de la entidad 1 y la de la entidad 2 no se mezclan (RF-03)
    assert comp.height == 2
