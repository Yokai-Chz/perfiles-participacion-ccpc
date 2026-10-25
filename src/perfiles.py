"""Caracterización de los perfiles y composición de cada sección (RF-10)."""
from pathlib import Path

import polars as pl

from indicadores import CLAVE_CELDA, ETIQUETAS_EDAD, indice_grupo_edad, tasa_fila

RASGOS_PONDERADOS = ["nivel", "brecha", "tendencia"]


def peso_y_rasgos(asig: pl.DataFrame) -> pl.DataFrame:
    total = asig["LN_2024"].sum()
    return (asig.group_by("perfil")
            .agg(pl.len().alias("celdas"), pl.col("LN_2024").sum(),
                 *[((pl.col(n) * pl.col("LN_medio")).sum() / pl.col("LN_medio").sum()).alias(n) for n in RASGOS_PONDERADOS])
            .with_columns((100 * pl.col("LN_2024") / total).round(2).alias("pct_lista_nominal_2024"))
            .sort("perfil"))


def participacion_por_perfil(largo_con_perfil: pl.DataFrame) -> pl.DataFrame:
    """Participación absoluta por elección dentro de cada perfil, columnas en orden cronológico."""
    t = (largo_con_perfil.group_by("perfil", "AELEC").agg(pl.col("SV").sum(), pl.col("NV").sum())
         .with_columns(tasa_fila().round(4).alias("participacion")))
    ancha = t.pivot(on="AELEC", index="perfil", values="participacion")
    return ancha.select("perfil", *sorted((c for c in ancha.columns if c != "perfil"), key=int)).sort("perfil")


def distribucion(asig: pl.DataFrame, columna: str) -> pl.DataFrame:
    """Porcentaje de la lista nominal 2024 de cada perfil que cae en cada valor de `columna`. Huecos en 0."""
    t = (asig.group_by("perfil", columna).agg(pl.col("LN_2024").sum())
         .with_columns((100 * pl.col("LN_2024") / pl.col("LN_2024").sum().over("perfil")).round(2).alias("pct")))
    return t.pivot(on=columna, index="perfil", values="pct").sort("perfil").with_columns(pl.exclude("perfil").fill_null(0.0))


def distribucion_edad(asig: pl.DataFrame) -> pl.DataFrame:
    """Distribución por grupo de edad con columnas en orden de edad."""
    d = distribucion(asig, "grupo_edad")
    return d.select("perfil", *[e for e in ETIQUETAS_EDAD if e in d.columns])


def grupo_edad_mediano(asig: pl.DataFrame) -> pl.DataFrame:
    """Grupo de edad que contiene la mediana de la lista nominal 2024 de cada perfil.

    Se acumula por grupo (no por celda) y se usa la mediana porque los tramos tienen anchos distintos.
    """
    por_grupo = (asig.group_by("perfil", "g").agg(pl.col("LN_2024").sum()).sort("perfil", "g")
                 .with_columns((pl.col("LN_2024").cum_sum().over("perfil") / pl.col("LN_2024").sum().over("perfil")).alias("acum")))
    return (por_grupo.filter(pl.col("acum") >= 0.5).group_by("perfil").agg(pl.col("g").min())
            .with_columns(pl.col("g").replace_strict(dict(enumerate(ETIQUETAS_EDAD)), return_dtype=pl.Utf8).alias("grupo_edad_mediano"))
            .select("perfil", "grupo_edad_mediano").sort("perfil"))


def composicion_entidades(asig: pl.DataFrame) -> pl.DataFrame:
    """Porcentaje de la lista nominal 2024 de cada entidad que pertenece a cada perfil."""
    ent = (asig.group_by("EDOCVE", "perfil").agg(pl.col("LN_2024").sum())
           .with_columns((100 * pl.col("LN_2024") / pl.col("LN_2024").sum().over("EDOCVE")).round(2).alias("pct")))
    return ent


def entidades_dominantes(composicion_ancha: pl.DataFrame, umbral: float = 80.0) -> int:
    """Cuántas entidades tienen más de `umbral` % de su lista en un solo perfil."""
    columnas = [c for c in composicion_ancha.columns if c != "EDOCVE"]
    return int((composicion_ancha.select(pl.max_horizontal(columnas)).to_series() > umbral).sum())


def top_entidades(ent: pl.DataFrame, peso: pl.DataFrame, n: int = 5) -> pl.DataFrame:
    """Entidades donde cada perfil está más sobrerrepresentado frente a su peso nacional."""
    nac = peso.select("perfil", "pct_lista_nominal_2024")
    sobre = (ent.join(nac, on="perfil")
             .with_columns((pl.col("pct") / pl.col("pct_lista_nominal_2024")).alias("indice_exacto"))
             .sort("perfil", "indice_exacto", "EDOCVE", descending=[False, True, False])   # EDOCVE desempata
             .with_columns(pl.col("indice_exacto").round(2).alias("indice")).drop("indice_exacto"))
    return sobre.group_by("perfil", maintain_order=True).head(n)


def secciones_mayoritarias(comp: pl.DataFrame, umbral: float = 0.5) -> pl.DataFrame:
    """Número de secciones donde cada perfil reúne `umbral` o más de la lista nominal, y total de secciones."""
    columnas = [c for c in comp.columns if c.startswith("prop_perfil_")]
    return pl.DataFrame({"perfil": [int(c.rsplit("_", 1)[1]) for c in columnas],
                         "secciones_mayoritarias": [int((comp[c] >= umbral).sum()) for c in columnas],
                         "secciones_total": [comp.height] * len(columnas)})


def composicion_secciones(parquet_ultima_eleccion: Path, asig: pl.DataFrame) -> tuple[pl.DataFrame, int, int]:
    """Proporción de la lista nominal de cada sección (entidad, sección) que pertenece a cada perfil (RF-03, RF-10).

    Devuelve (composición, LN sin perfil por celdas excluidas, LN total).
    """
    sec = (pl.scan_parquet(parquet_ultima_eleccion)
           .with_columns(pl.col("TIPOSEC").cast(pl.Utf8), indice_grupo_edad())
           .group_by("EDOCVE", "SECCION", "TIPOSEC", "SEXO", "g").agg(pl.col("LN").sum().cast(pl.Int64))
           .collect()
           .join(asig.select("EDOCVE", "TIPOSEC", "SEXO", "g", "perfil"), on=["EDOCVE", "TIPOSEC", "SEXO", "g"], how="left"))
    sin_perfil = int(sec.filter(pl.col("perfil").is_null())["LN"].sum())
    total = int(sec["LN"].sum())
    k = int(asig["perfil"].max())
    comp = (sec.drop_nulls("perfil").group_by("EDOCVE", "SECCION", "perfil").agg(pl.col("LN").sum())
            .with_columns((pl.col("LN").cast(pl.Float64) / pl.col("LN").sum().over("EDOCVE", "SECCION").cast(pl.Float64)).alias("prop"))
            .pivot(on="perfil", index=["EDOCVE", "SECCION"], values="prop").fill_null(0.0))
    comp = comp.rename({str(i): f"prop_perfil_{i}" for i in range(1, k + 1) if str(i) in comp.columns})
    return comp, sin_perfil, total
