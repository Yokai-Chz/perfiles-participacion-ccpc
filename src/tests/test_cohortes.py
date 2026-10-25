import polars as pl
import pytest

import cohortes as coh


def test_quinquenios_terminan_en_0_y_5():
    df = pl.DataFrame({"n": [1986, 1990, 1991, 2006]}).with_columns(coh.etiqueta_quinquenio(pl.col("n")).alias("q"))
    assert df["q"].to_list() == ["1986-1990", "1986-1990", "1991-1995", "2006-2010"]


def test_la_cohorte_se_sigue_entre_elecciones_y_se_mide_contra_su_entidad():
    # Nacidos en 1991: 18 años en 2009 y 21 en 2012. La otra fila completa la entidad.
    datos = pl.DataFrame({"AELEC": [2009, 2009, 2012, 2012], "EDOCVE": [1] * 4, "SEXO": [0] * 4, "TIPOSEC": ["U"] * 4,
                          "EDAD": [18, 40, 21, 43], "LN": [100] * 4, "SV": [70, 50, 40, 60], "NV": [30, 50, 60, 40]})
    exacta = coh.por_edad_exacta(datos.lazy())
    jovenes = exacta.filter(pl.col("nacimiento") == 1991).sort("AELEC")
    assert jovenes["EDAD"].to_list() == [18, 21]
    assert jovenes["rel"].to_list() == pytest.approx([0.70 - 0.60, 0.40 - 0.50])


def _exacta(filas):
    return pl.DataFrame([{"nacimiento": n, "AELEC": a, "EDAD": a - n, "LN": 100, "SV": 50, "NV": 50, "rel": r} for n, a, r in filas])


def test_efecto_primer_voto_compara_con_3_y_6_anios_despues():
    exacta = _exacta([(1991, 2009, 0.05), (1991, 2012, -0.10), (1991, 2015, -0.12),
                      (1985, 2009, -0.08), (1985, 2012, -0.09)])   # 1985 tenía 24 en 2009: no es primer voto
    e = coh.efecto_primer_voto(exacta)
    assert e["nacimiento"].to_list() == [1991]
    fila = e.row(0, named=True)
    assert fila["edad_primera"] == 18
    assert fila["cambio_siguiente"] == pytest.approx(-0.15)
    assert fila["cambio_seis_anios"] == pytest.approx(-0.17)


def test_sin_eleccion_posterior_el_cambio_queda_nulo():
    e = coh.efecto_primer_voto(_exacta([(2006, 2024, 0.02)]))
    assert e["rel_siguiente"].to_list() == [None]


def test_el_resumen_del_primer_voto_solo_promedia_cohortes_con_seguimiento():
    efecto = pl.DataFrame({"nacimiento": [1991, 1994, 2006, 1990], "edad_primera": [18, 18, 18, 19],
                           "rel_primera": [0.04, 0.02, 0.01, -0.05], "rel_siguiente": [-0.08, -0.10, None, -0.09]})
    r = coh.resumen_primer_voto(efecto).row(0, named=True)
    assert r["cohortes_con_seguimiento"] == 2 and (r["nacimiento_desde"], r["nacimiento_hasta"]) == (1991, 1994)
    assert r["rel_a_los_18"] == pytest.approx(0.03)
    assert r["rel_tres_anios_despues"] == pytest.approx(-0.09)
    assert r["rel_a_los_18_todas"] == pytest.approx(0.07 / 3)
