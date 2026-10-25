import polars as pl
import pytest

import territorio as ter


def _filas(anio, secciones, defs, ln=100):
    return pl.DataFrame({"AELEC": [anio] * len(secciones), "EDOCVE": [1] * len(secciones), "SECCION": secciones,
                         "DEF": defs, "TIPOSEC": ["U"] * len(secciones), "LN": [ln] * len(secciones),
                         "SV": [60] * len(secciones), "NV": [40] * len(secciones), "NS": [0] * len(secciones)},
                        schema_overrides={"DEF": pl.Int16})


@pytest.fixture
def escenario(tmp_path):
    # 2021 en marco 2021; 2024 en marco 2023 con una sección nueva (12); 2009 con una sección que ya no existe (9).
    a2009 = _filas(2009, [9, 10, 11], [None, 1, 2])
    a2021 = _filas(2021, [10, 11], [1, 2])
    a2024 = _filas(2024, [10, 11, 12], [3, 3, 3])
    a2021.write_parquet(tmp_path / "ccpc_2021.parquet")
    a2024.write_parquet(tmp_path / "ccpc_2024.parquet")
    datos = pl.concat([a2009, a2021, a2024]).lazy()
    eq = ter.equivalencia_secciones(tmp_path / "ccpc_2021.parquet", tmp_path / "ccpc_2024.parquet")
    return datos, eq


def test_la_equivalencia_usa_el_distrito_de_2021_y_deja_nula_la_seccion_nueva(escenario):
    _, eq = escenario
    assert eq["DEF_2021"].to_list() == [1, 2, None]
    assert eq["DEF_2023"].to_list() == [3, 3, 3]


def test_la_lista_nominal_se_conserva_y_se_reporta_la_sin_distrito(escenario):
    datos, eq = escenario
    largo = ter.distritos_largo(datos, eq)
    cons = ter.conservacion(largo, datos)
    assert cons["cuadra"].all()
    assert cons.filter(pl.col("AELEC") == 2024)["LN_sin_distrito"].item() == 100
    assert cons.filter(pl.col("AELEC") == 2009)["LN_sin_distrito"].item() == 100
