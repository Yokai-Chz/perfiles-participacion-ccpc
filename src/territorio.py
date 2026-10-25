"""Distritos electorales federales en el tiempo (spec 002, RF-09 a RF-12).

En 2009 a 2021, `DEF` viene en el marco cartográfico DERFE 2021, así que el distrito de cada fila ya es comparable.
En 2024, `DEF` viene en el marco 2023. Para comparar en el tiempo, cada sección de 2024 recibe el distrito
que tenía en 2021 (misma entidad y sección). Las secciones sin equivalencia no se imputan (D4).
"""
from pathlib import Path

import polars as pl

from configuracion import ELECCIONES
from indicadores import tasa_fila

ULTIMA = ELECCIONES[-1]
SUMAS = ["LN", "SV", "NV", "NS"]


def equivalencia_secciones(parquet_2021: Path, parquet_ultima: Path) -> pl.DataFrame:
    """(EDOCVE, SECCION) de la última elección → distrito en el marco 2021 y en el marco 2023 (RF-09)."""
    def distritos(ruta, nombre):
        return (pl.scan_parquet(ruta).select("EDOCVE", "SECCION", "DEF").unique()
                .collect().rename({"DEF": nombre}))
    return (distritos(parquet_ultima, "DEF_2023")
            .join(distritos(parquet_2021, "DEF_2021"), on=["EDOCVE", "SECCION"], how="left")
            .sort("EDOCVE", "SECCION"))


def con_distrito_2021(datos: pl.LazyFrame, equivalencia: pl.DataFrame) -> pl.LazyFrame:
    """Agrega `DEF_2021`: el `DEF` original antes de la última elección, la equivalencia en la última."""
    eq = equivalencia.lazy().select("EDOCVE", "SECCION", pl.col("DEF_2021").alias("_def_eq"))
    return (datos.join(eq, on=["EDOCVE", "SECCION"], how="left")
            .with_columns(pl.when(pl.col("AELEC") == ULTIMA).then(pl.col("_def_eq")).otherwise(pl.col("DEF")).alias("DEF_2021"))
            .drop("_def_eq"))


def distritos_largo(datos: pl.LazyFrame, equivalencia: pl.DataFrame) -> pl.DataFrame:
    """Sumas, tasa, participación relativa a la entidad, % NS y % urbano por distrito (marco 2021) y elección (RF-10).

    Las filas sin distrito quedan con `DEF_2021` nulo para poder comprobar la conservación (RF-12).
    """
    d = con_distrito_2021(datos, equivalencia)
    urbana = pl.col("LN").filter(pl.col("TIPOSEC").cast(pl.Utf8) == "U").sum().cast(pl.Int64)
    largo = (d.group_by("AELEC", "EDOCVE", "DEF_2021")
             .agg(*[pl.col(c).sum().cast(pl.Int64) for c in SUMAS], urbana.alias("LN_urbana"))
             .collect())
    ref = (largo.group_by("AELEC", "EDOCVE").agg(pl.col("SV").sum(), pl.col("NV").sum())
           .with_columns(tasa_fila().alias("tasa_entidad")).select("AELEC", "EDOCVE", "tasa_entidad"))
    return (largo.join(ref, on=["AELEC", "EDOCVE"])
            .with_columns(tasa_fila().alias("tasa"),
                          (pl.col("NS") / pl.col("LN")).alias("prop_NS"),
                          (pl.col("LN_urbana") / pl.col("LN")).alias("prop_urbana"))
            .with_columns((pl.col("tasa") - pl.col("tasa_entidad")).alias("rel"))
            .sort("AELEC", "EDOCVE", "DEF_2021", nulls_last=True))


def conservacion(largo: pl.DataFrame, datos: pl.LazyFrame) -> pl.DataFrame:
    """LN por elección: con distrito, sin distrito y total de la fuente. Deben cuadrar (RF-12)."""
    total = datos.group_by("AELEC").agg(pl.col("LN").sum().cast(pl.Int64).alias("LN_fuente")).collect()
    return (largo.group_by("AELEC")
            .agg(pl.col("LN").filter(pl.col("DEF_2021").is_not_null()).sum().alias("LN_con_distrito"),
                 pl.col("LN").filter(pl.col("DEF_2021").is_null()).sum().alias("LN_sin_distrito"))
            .join(total, on="AELEC")
            .with_columns((pl.col("LN_con_distrito") + pl.col("LN_sin_distrito") == pl.col("LN_fuente")).alias("cuadra"),
                          (100 * pl.col("LN_sin_distrito") / pl.col("LN_fuente")).round(3).alias("pct_sin_distrito"))
            .sort("AELEC"))


def ancha_distritos(largo: pl.DataFrame) -> pl.DataFrame:
    """Una fila por distrito con `rel_AAAA` y `tasa_AAAA`; solo distritos presentes en todas las elecciones."""
    con = largo.drop_nulls("DEF_2021")
    completos = con.group_by("EDOCVE", "DEF_2021").agg(pl.len().alias("n")).filter(pl.col("n") == len(ELECCIONES))
    con = con.join(completos.select("EDOCVE", "DEF_2021"), on=["EDOCVE", "DEF_2021"])
    clave = ["EDOCVE", "DEF_2021"]
    rel = con.pivot(on="AELEC", index=clave, values="rel").rename({str(e): f"rel_{e}" for e in ELECCIONES})
    tasa = con.pivot(on="AELEC", index=clave, values="tasa").rename({str(e): f"tasa_{e}" for e in ELECCIONES})
    extra = con.group_by(clave).agg(
        pl.col("prop_NS").mean().alias("prop_NS_media"),
        pl.col("prop_NS").max().alias("prop_NS_max"),
        pl.col("prop_urbana").filter(pl.col("AELEC") == ULTIMA).first().alias(f"prop_urbana_{ULTIMA}"),
        pl.col("LN").filter(pl.col("AELEC") == ULTIMA).first().alias(f"LN_{ULTIMA}"))
    columnas = clave + [f"rel_{e}" for e in ELECCIONES] + [f"tasa_{e}" for e in ELECCIONES]
    return rel.join(tasa, on=clave).join(extra, on=clave).select(*columnas, *extra.columns[2:]).sort(clave)


def composicion_distritos(comp_secciones: pl.DataFrame, parquet_ultima: Path, equivalencia: pl.DataFrame,
                          marco: str) -> pl.DataFrame:
    """Porcentaje de la lista nominal de la última elección de cada distrito que pertenece a cada perfil (RF-11).

    `marco` es "DEF_2023" (distritos vigentes) o "DEF_2021" (comparables en el tiempo).
    """
    ln = (pl.scan_parquet(parquet_ultima).group_by("EDOCVE", "SECCION").agg(pl.col("LN").sum().cast(pl.Int64)).collect())
    props = [c for c in comp_secciones.columns if c.startswith("prop_perfil_")]
    base = (comp_secciones.join(ln, on=["EDOCVE", "SECCION"]).join(equivalencia, on=["EDOCVE", "SECCION"])
            .drop_nulls(marco))
    salida = (base.group_by("EDOCVE", marco)
              .agg(pl.col("LN").sum(), *[((pl.col(c) * pl.col("LN")).sum() / pl.col("LN").sum() * 100).alias(c.replace("prop_", "pct_")) for c in props])
              .rename({marco: "DEF"}).sort("EDOCVE", "DEF"))
    pcts = [c.replace("prop_", "pct_") for c in props]
    dominante = salida.select(pcts).to_numpy().argmax(axis=1) + 1
    return salida.with_columns(pl.Series("perfil_dominante", dominante, dtype=pl.Int8))


def sin_correspondencia(equivalencia: pl.DataFrame, parquet_ultima: Path) -> pl.DataFrame:
    """Secciones de la última elección que no existen en el marco 2021, con su lista nominal, por entidad (D4)."""
    ln = (pl.scan_parquet(parquet_ultima).group_by("EDOCVE", "SECCION").agg(pl.col("LN").sum().cast(pl.Int64)).collect())
    return (equivalencia.filter(pl.col("DEF_2021").is_null()).join(ln, on=["EDOCVE", "SECCION"])
            .group_by("EDOCVE").agg(pl.len().alias("secciones"), pl.col("LN").sum()).sort("EDOCVE"))
