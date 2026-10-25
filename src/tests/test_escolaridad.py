import polars as pl
import pytest

import escolaridad as esc


def _ln(filas):
    """filas: (entidad, sección, sexo, LN) de una sola celda de edad 30-34 en sección urbana."""
    return pl.DataFrame([{"EDOCVE": e, "SECCION": s, "TIPOSEC": "U", "SEXO": x, "g": 3, "grupo_edad": "30-34", "LN": ln}
                         for e, s, x, ln in filas])


def _eceg(filas):
    """filas: (entidad, sección, grado hombres, grado mujeres)."""
    return pl.DataFrame([{"EDOCVE": e, "SECCION": s, "GRADO_HOM": gh, "GRADO_MUJ": gm, "POSB_HOM": 10, "POSB_MUJ": 20, "P18_HOM": 100, "P18_MUJ": 100}
                         for e, s, gh, gm in filas])


def test_la_celda_promedia_su_mismo_sexo_ponderado_por_lista_nominal():
    ln = _ln([(1, 1, 1, 100), (1, 2, 1, 300)])               # mujeres en dos secciones
    eceg = _eceg([(1, 1, 7.0, 8.0), (1, 2, 7.0, 12.0)])
    unida, _ = esc.unir_secciones(ln, eceg)
    c = esc.por_celda(unida).row(0, named=True)
    assert c["esc"] == pytest.approx((100 * 8 + 300 * 12) / 400)   # usa el grado de mujeres, no el de hombres
    assert c["prop_posb"] == pytest.approx(0.20)


def test_la_seccion_sin_dato_no_entra_al_promedio_y_se_reporta():
    ln = _ln([(1, 1, 0, 100), (1, 9, 0, 50)])                # la sección 9 no está en la ECEG
    eceg = _eceg([(1, 1, 9.0, 9.0), (1, 5, 10.0, 10.0)])      # la sección 5 no tiene lista nominal
    unida, resumen = esc.unir_secciones(ln, eceg)
    c = esc.por_celda(unida).row(0, named=True)
    assert c["esc"] == pytest.approx(9.0)
    assert (c["LN_2021"], c["LN_con_dato"]) == (150, 100)
    r = resumen.row(0, named=True)
    assert (r["secciones_sin_eceg"], r["LN_sin_eceg"], r["secciones_eceg_sin_ln"]) == (1, 50, 1)


def test_la_escolaridad_relativa_suma_cero_en_cada_entidad():
    celdas = pl.DataFrame({"EDOCVE": [1, 1, 2], "esc": [8.0, 11.0, 9.0], "LN_con_dato": [100, 200, 50]})
    r = esc.relativa_a_entidad(celdas)
    suma = r.group_by("EDOCVE").agg((pl.col("esc_rel") * pl.col("LN_con_dato")).sum().alias("s"))
    assert suma["s"].abs().max() == pytest.approx(0)
    assert r.filter(pl.col("EDOCVE") == 2)["esc_rel"].item() == pytest.approx(0)


def test_la_varianza_explicada_es_1_si_el_grupo_lo_determina_todo():
    celdas = pl.DataFrame({"TIPOSEC": ["U", "U", "R"], "esc_rel": [1.0, 1.0, -2.0], "LN_con_dato": [100, 100, 100]})
    assert esc.varianza_explicada(celdas, "TIPOSEC") == pytest.approx(1)


def test_el_lector_asigna_masculino_a_hombres_y_anula_secciones_sin_poblacion(tmp_path):
    carpeta = tmp_path / "conjunto_de_datos"
    carpeta.mkdir()
    (carpeta / "INE_SECCION_2020.csv").write_text(
        "ENTIDAD,SECCION,GRAPROES_M,GRAPROES_F,P18YM_PB_M,P18YM_PB_F,P_18YMAS_M,P_18YMAS_F,P_15YMAS_M,P_15YMAS_F\n"
        "1,10,12.5,8.25,5,6,50,60,55,65\n"
        "1,11,0,0,0,0,0,0,0,0\n", encoding="utf-8")
    e = esc.leer_eceg(tmp_path)
    fila = e.filter(pl.col("SECCION") == 10).row(0, named=True)
    assert (fila["GRADO_HOM"], fila["GRADO_MUJ"]) == (12.5, 8.25)   # en el INEGI, _M es masculino
    vacia = e.filter(pl.col("SECCION") == 11).row(0, named=True)
    assert vacia["GRADO_HOM"] is None and vacia["GRADO_MUJ"] is None
