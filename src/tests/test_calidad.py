import polars as pl

import calidad


def tabla_base(**cambios):
    df = pl.DataFrame({"AELEC": [2021, 2021], "EDOCVE": [1, 2], "SECCION": [1, 1], "SEXO": [0, 0], "EDAD": [30, 95],
                       "LN": [10, 20], "SV": [5, 10], "NV": [4, 8], "NS": [1, 2]})
    return df.with_columns(**{k: pl.Series(v) for k, v in cambios.items()})


def test_se_reporta_la_fila_con_ln_distinto_de_la_suma():
    datos = tabla_base(LN=[10, 99]).lazy()
    assert calidad.desbalance(datos)["filas_con_desbalance"].to_list() == [1]


def test_tabla_sin_desbalance_no_reporta_filas():
    assert calidad.desbalance(tabla_base().lazy()).height == 0


def test_una_clave_repetida_se_detecta():
    repetida = pl.concat([tabla_base(), tabla_base().head(1)])
    assert calidad.duplicadas(repetida).height == 1
    assert calidad.duplicadas(tabla_base()).height == 0


def test_tabla_de_calidad_totales_y_edades_atipicas():
    t = calidad.tabla(tabla_base().lazy())
    fila = t.filter(pl.col("EDOCVE") == 2).row(0, named=True)
    assert (fila["LN"], fila["edad_max"], fila["LN_90_o_mas"]) == (20, 95, 20)
    assert fila["pct_NS"] == 10.0


def test_participacion_nacional_es_cociente_de_sumas():
    t = calidad.nacional(calidad.tabla(tabla_base().lazy()))
    assert t["part_SV_sobre_SV_NV"][0] == round(100 * 15 / 27, 2)
