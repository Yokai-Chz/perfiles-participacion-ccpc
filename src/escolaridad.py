"""Escolaridad del entorno de cada celda, a partir de la ECEG 2020 de INEGI e INE (spec 003).

La ECEG 2020 trae la escolaridad por sección y sexo, sin edad, en el marco seccional del INE de enero de 2021.
Por eso cada celda recibe la escolaridad de las secciones donde vive, ponderada por su lista nominal de 2021:
es un dato del entorno y no de las personas.

Esquema normalizado de la ECEG que esperan estas funciones (una fila por entidad y sección):
EDOCVE, SECCION, GRADO_HOM, GRADO_MUJ (grado promedio escolar de hombres y mujeres),
POSB_HOM, POSB_MUJ (población de 18 años o más con educación posbásica) y P18_HOM, P18_MUJ (población de 18 años o más).
"""
from pathlib import Path

import polars as pl

from indicadores import CLAVE_CELDA, etiquetar_grupo, indice_grupo_edad

CLAVE_SECCION = ["EDOCVE", "SECCION"]
ARCHIVO_SECCION = Path("conjunto_de_datos") / "INE_SECCION_2020.csv"

# Columnas de la ECEG (diccionario oficial). En el INEGI, _F es femenino y _M es masculino.
COLUMNAS_ECEG = {"GRAPROES_M": "GRADO_HOM", "GRAPROES_F": "GRADO_MUJ", "P18YM_PB_M": "POSB_HOM", "P18YM_PB_F": "POSB_MUJ",
                 "P_18YMAS_M": "P18_HOM", "P_18YMAS_F": "P18_MUJ", "P_15YMAS_M": "P15_HOM", "P_15YMAS_F": "P15_MUJ"}


def leer_eceg(carpeta: Path) -> pl.DataFrame:
    """Tabla nacional por sección de la ECEG 2020 con el esquema normalizado de este módulo (RF-01).

    El grado promedio de una sección sin personas de 15 años o más de ese sexo queda nulo: la fuente pone 0.
    """
    d = pl.read_csv(carpeta / ARCHIVO_SECCION, columns=["ENTIDAD", "SECCION", *COLUMNAS_ECEG],
                    schema_overrides={"ENTIDAD": pl.Int8, "SECCION": pl.Int32} | {c: pl.Float64 for c in COLUMNAS_ECEG})
    d = d.rename({"ENTIDAD": "EDOCVE"} | COLUMNAS_ECEG)
    if d.select(CLAVE_SECCION).is_duplicated().any():
        raise ValueError("la ECEG trae secciones repetidas")
    return (d.with_columns(pl.when(pl.col("P15_HOM") > 0).then(pl.col("GRADO_HOM")).alias("GRADO_HOM"),
                           pl.when(pl.col("P15_MUJ") > 0).then(pl.col("GRADO_MUJ")).alias("GRADO_MUJ"))
            .sort(CLAVE_SECCION))


def lista_por_seccion_y_celda(parquet_2021) -> pl.DataFrame:
    """LN de 2021 por sección y celda (entidad, tipo de sección, sexo y grupo de edad). Sin la categoría no binaria."""
    return etiquetar_grupo(
        pl.scan_parquet(parquet_2021).filter(pl.col("SEXO") < 2)
        .with_columns(pl.col("TIPOSEC").cast(pl.Utf8), indice_grupo_edad())
        .group_by("EDOCVE", "SECCION", "TIPOSEC", "SEXO", "g").agg(pl.col("LN").sum().cast(pl.Int64))
        .collect())


def unir_secciones(ln: pl.DataFrame, eceg: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Une la LN 2021 con la ECEG por (entidad, sección) (RF-02).

    Devuelve (LN con escolaridad, resumen de lo que no unió en cada lado, por entidad).
    """
    unida = ln.join(eceg, on=CLAVE_SECCION, how="left")
    sec_ln = ln.group_by(CLAVE_SECCION).agg(pl.col("LN").sum())
    sin_eceg = sec_ln.join(eceg.select(CLAVE_SECCION), on=CLAVE_SECCION, how="anti")
    sin_ln = eceg.select(CLAVE_SECCION).join(sec_ln.select(CLAVE_SECCION), on=CLAVE_SECCION, how="anti")
    resumen = (sec_ln.group_by("EDOCVE").agg(pl.len().alias("secciones_ln"), pl.col("LN").sum().alias("LN_2021"))
               .join(sin_eceg.group_by("EDOCVE").agg(pl.len().alias("secciones_sin_eceg"), pl.col("LN").sum().alias("LN_sin_eceg")),
                     on="EDOCVE", how="left")
               .join(sin_ln.group_by("EDOCVE").agg(pl.len().alias("secciones_eceg_sin_ln")), on="EDOCVE", how="left")
               .with_columns(pl.exclude("EDOCVE").fill_null(0))
               .sort("EDOCVE"))
    return unida, resumen


def por_celda(unida: pl.DataFrame) -> pl.DataFrame:
    """Grado promedio y % con posbásica del entorno de cada celda, de su mismo sexo (RF-03).

    Se pondera por la LN de 2021 de la celda en cada sección; las secciones sin dato no entran al promedio.
    """
    hombre = pl.col("SEXO") == 0
    grado = pl.when(hombre).then(pl.col("GRADO_HOM")).otherwise(pl.col("GRADO_MUJ"))
    posb = pl.when(hombre).then(pl.col("POSB_HOM") / pl.col("P18_HOM")).otherwise(pl.col("POSB_MUJ") / pl.col("P18_MUJ"))
    con = unida.with_columns(grado.alias("grado"), posb.alias("prop_posb"))
    ln_grado = pl.col("LN").filter(pl.col("grado").is_not_null())
    ln_posb = pl.col("LN").filter(pl.col("prop_posb").is_not_null() & pl.col("prop_posb").is_finite())
    return (con.group_by(CLAVE_CELDA)
            .agg(pl.col("LN").sum().alias("LN_2021"), ln_grado.sum().alias("LN_con_dato"),
                 ((pl.col("grado") * pl.col("LN")).filter(pl.col("grado").is_not_null()).sum() / ln_grado.sum()).alias("esc"),
                 ((pl.col("prop_posb") * pl.col("LN")).filter(pl.col("prop_posb").is_not_null() & pl.col("prop_posb").is_finite()).sum()
                  / ln_posb.sum()).alias("prop_posb"))
            .sort(CLAVE_CELDA))


def relativa_a_entidad(celdas: pl.DataFrame) -> pl.DataFrame:
    """`esc_rel` = escolaridad de la celda menos el promedio de su entidad, ponderado por LN con dato (RF-04, D1)."""
    w = pl.col("LN_con_dato").cast(pl.Float64)
    media = ((pl.col("esc") * w).sum() / w.sum()).over("EDOCVE")
    return celdas.with_columns((pl.col("esc") - media).alias("esc_rel"))


def varianza_explicada(celdas: pl.DataFrame, grupo: str) -> float:
    """Fracción de la varianza ponderada de `esc_rel` que explica `grupo` (η²)."""
    d = celdas.drop_nulls("esc_rel").with_columns(pl.col("LN_con_dato").cast(pl.Float64).alias("w"))
    media = (d["esc_rel"] * d["w"]).sum() / d["w"].sum()
    total = (d["w"] * (d["esc_rel"] - media) ** 2).sum()
    dentro = (d.with_columns(((pl.col("esc_rel") * pl.col("w")).sum() / pl.col("w").sum()).over(grupo).alias("m"))
              .select((pl.col("w") * (pl.col("esc_rel") - pl.col("m")) ** 2).sum()).item())
    return float(1 - dentro / total)


def por_perfil(celdas: pl.DataFrame, asig: pl.DataFrame) -> pl.DataFrame:
    """Grado promedio y % con posbásica del entorno de cada perfil, ponderados por LN con dato (RF-07)."""
    w = pl.col("LN_con_dato").cast(pl.Float64)
    return (celdas.join(asig.select(*CLAVE_CELDA, "perfil"), on=CLAVE_CELDA)
            .group_by("perfil")
            .agg(((pl.col("esc") * w).sum() / w.sum()).alias("grado_promedio_entorno"),
                 (100 * (pl.col("prop_posb") * w).sum() / w.sum()).alias("pct_posbasica_entorno"),
                 ((pl.col("esc_rel") * w).sum() / w.sum()).alias("esc_rel"))
            .sort("perfil"))
