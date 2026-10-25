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


def ns_por_seccion(datos: pl.LazyFrame) -> pl.DataFrame:
    """LN, NS y proporción de NS de cada (elección, entidad, sección) (spec 002, RF-01)."""
    return (datos.group_by("AELEC", "EDOCVE", "SECCION")
            .agg(pl.col("LN").sum().cast(pl.Int64), pl.col("NS").sum().cast(pl.Int64))
            .with_columns(pl.when(pl.col("LN") > 0).then(pl.col("NS") / pl.col("LN")).otherwise(0.0).alias("prop_NS"))
            .sort("AELEC", "EDOCVE", "SECCION").collect())


def secciones_ns_alto(por_seccion: pl.DataFrame, umbral: float) -> pl.DataFrame:
    """Secciones cuyo NS supera `umbral` (proporción de su lista) en esa elección. NS no es abstención."""
    return por_seccion.filter(pl.col("prop_NS") > umbral)


def resumen_ns_alto(por_seccion: pl.DataFrame, umbral: float) -> pl.DataFrame:
    """Secciones marcadas y su lista nominal, por elección, con el porcentaje que representan."""
    marca = pl.col("prop_NS") > umbral
    return (por_seccion.group_by("AELEC")
            .agg(pl.len().alias("secciones"), marca.sum().alias("secciones_marcadas"),
                 pl.col("LN").sum().alias("LN"), pl.col("LN").filter(marca).sum().alias("LN_marcada"))
            .with_columns((100 * pl.col("secciones_marcadas") / pl.col("secciones")).round(2).alias("pct_secciones"),
                          (100 * pl.col("LN_marcada") / pl.col("LN")).round(2).alias("pct_LN"))
            .sort("AELEC"))


def distribucion_ns(por_seccion: pl.DataFrame, ancho: float = 0.05) -> pl.DataFrame:
    """Histograma de la proporción de NS por sección: secciones por intervalo de `ancho`, por elección."""
    n = int(round(1 / ancho))
    return (por_seccion.with_columns((pl.col("prop_NS") / ancho).floor().clip(upper_bound=n - 1).cast(pl.Int16).alias("i"))
            .group_by("AELEC", "i").agg(pl.len().alias("secciones"))
            .with_columns((pl.col("i") * ancho).round(2).alias("desde"), ((pl.col("i") + 1) * ancho).round(2).alias("hasta"))
            .with_columns((100 * pl.col("secciones") / pl.col("secciones").sum().over("AELEC")).round(3).alias("pct_secciones"))
            .select("AELEC", "desde", "hasta", "secciones", "pct_secciones").sort("AELEC", "desde"))
