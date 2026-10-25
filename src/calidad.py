"""Validaciones de integridad (RF-02) y tabla de calidad (RF-15)."""
from pathlib import Path

import polars as pl

CLAVE = ["AELEC", "EDOCVE", "SECCION", "SEXO", "EDAD"]   # RF-03: la sección sola no es única


def desbalance(datos: pl.LazyFrame) -> pl.DataFrame:
    """Filas donde LN != SV + NV + NS, por elección. Se reportan, no se descartan."""
    return (datos.filter(pl.col("LN") != pl.col("SV") + pl.col("NV") + pl.col("NS"))
            .group_by("AELEC").agg(pl.len().alias("filas_con_desbalance")).sort("AELEC").collect())


def duplicadas(datos: pl.LazyFrame | pl.DataFrame) -> pl.DataFrame:
    """Claves (elección, entidad, sección, sexo, edad) repetidas."""
    lazy = datos.lazy()
    return (lazy.group_by(CLAVE).agg(pl.len().alias("n")).filter(pl.col("n") > 1).collect())


def duplicadas_por_archivo(archivos: list[Path]) -> pl.DataFrame:
    """Igual que `duplicadas`, una elección a la vez para no cargar todo en memoria."""
    return pl.concat([duplicadas(pl.scan_parquet(a)) for a in archivos])


def tabla(datos: pl.LazyFrame) -> pl.DataFrame:
    """Filas, totales, NS y edades atípicas por elección y entidad."""
    return (
        datos.group_by("AELEC", "EDOCVE")
        .agg(pl.len().alias("filas"),
             # Int64: con Int32, 100 * SV desbordaría al calcular porcentajes nacionales.
             *[pl.col(c).sum().cast(pl.Int64).alias(c) for c in ["LN", "SV", "NV", "NS"]],
             pl.col("EDAD").max().alias("edad_max"),
             pl.col("LN").filter(pl.col("EDAD") >= 90).sum().cast(pl.Int64).alias("LN_90_o_mas"))
        .with_columns((100 * pl.col("NS") / pl.col("LN")).round(2).alias("pct_NS"))
        .sort("AELEC", "EDOCVE").collect()
    )


def nacional(tabla_calidad: pl.DataFrame) -> pl.DataFrame:
    """Participación nacional por elección como cociente de sumas (RF-05), con las dos definiciones de D1."""
    return (
        tabla_calidad.group_by("AELEC")
        .agg(*[pl.col(c).sum() for c in ["LN", "SV", "NV", "NS"]])
        .with_columns((100 * pl.col("SV") / pl.col("LN")).round(2).alias("part_SV_sobre_LN"),
                      (100 * pl.col("SV") / (pl.col("SV") + pl.col("NV"))).round(2).alias("part_SV_sobre_SV_NV"),
                      (100 * pl.col("NS") / pl.col("LN")).round(2).alias("pct_NS"))
        .sort("AELEC")
    )
