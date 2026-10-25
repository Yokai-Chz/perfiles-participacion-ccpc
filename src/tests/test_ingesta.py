import polars as pl
import pytest

import ingesta


def escribir_csv(ruta, columnas=None, filas=None):
    columnas = columnas or ingesta.ESQUEMA
    filas = filas or [[2021, "2021-06-06", 6, "COLIMA", 1, "ARMERIA", 1, "U", 1, 1, 0, 30, 10, 6, 3, 1]]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(",".join(columnas) + "\n" + "\n".join(",".join(map(str, f)) for f in filas) + "\n", encoding="utf-8")


def test_lee_un_csv_y_deja_las_columnas_con_tipos_compactos(tmp_path):
    ruta = tmp_path / "conteoscensales2021_col.csv"
    escribir_csv(ruta)
    df = ingesta.leer_entidad(ruta)
    assert df.columns == list(ingesta.TIPOS) + ["TIPOSEC"]
    assert df.schema["EDOCVE"] == pl.Int8


def test_un_esquema_distinto_falla_con_error_explicito(tmp_path):
    ruta = tmp_path / "conteoscensales2021_x.csv"
    escribir_csv(ruta, columnas=ingesta.ESQUEMA[:-1], filas=[[1] * 15])
    with pytest.raises(ValueError, match="Esquema distinto"):
        ingesta.leer_entidad(ruta)


def test_agrupa_por_anio_buscando_en_subcarpetas(tmp_path):
    escribir_csv(tmp_path / "conteoscensales2018_col.csv")
    escribir_csv(tmp_path / "anidada" / "conteoscensales2021_col.csv")
    assert sorted(ingesta.listar_por_anio(tmp_path)) == [2018, 2021]


def test_escribe_un_parquet_por_anio_con_la_columna_de_eleccion(tmp_path):
    escribir_csv(tmp_path / "crudos" / "conteoscensales2021_col.csv")
    destino = tmp_path / "salida"
    destino.mkdir()
    ingesta.escribir_parquet_por_anio(ingesta.listar_por_anio(tmp_path / "crudos"), destino)
    assert pl.read_parquet(destino / "ccpc_2021.parquet")["AELEC"].to_list() == [2021]


def test_solo_se_listan_los_csv_de_los_conteos(tmp_path):
    (tmp_path / "ccpc").mkdir()
    (tmp_path / "ccpc" / "datosabiertos_deceyec_conteoscensales2021_ags.csv").write_text("x")
    (tmp_path / "eceg_2020").mkdir()
    (tmp_path / "eceg_2020" / "INE_SECCION_2020.csv").write_text("x")
    assert {a: [r.name for r in rs] for a, rs in ingesta.listar_por_anio(tmp_path).items()} == {
        2021: ["datosabiertos_deceyec_conteoscensales2021_ags.csv"]}
