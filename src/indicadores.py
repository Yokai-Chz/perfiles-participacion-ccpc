"""Grupos de edad, tasa de participación y participación relativa (RF-04 a RF-06)."""
import polars as pl

from configuracion import CIRCUNSCRIPCION, ELECCIONES, UMBRAL_LN

LIMITES_EDAD = [18, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90]
ETIQUETAS_EDAD = [f"{ini}-{fin - 1}" for ini, fin in zip(LIMITES_EDAD, LIMITES_EDAD[1:])] + ["90+"]


def clave_celda(territorio: str = "EDOCVE") -> list[str]:
    """Columnas que identifican una celda. `territorio` es EDOCVE (entidad) o REGION (circunscripción)."""
    return [territorio, "TIPOSEC", "SEXO", "g", "grupo_edad"]


CLAVE_CELDA = clave_celda()
REFERENCIAS = {"nacional": ["AELEC"], "entidad": ["AELEC", "EDOCVE"], "region": ["AELEC", "REGION"]}
SUMAS = ["LN", "SV", "NV", "NS"]


def indice_grupo_edad(columna: str = "EDAD") -> pl.Expr:
    """Índice del tramo de edad. Todo lo que pasa de 90 cae en «90+» (D6, RF-04)."""
    superados = [(pl.col(columna) >= lim).cast(pl.Int8) for lim in LIMITES_EDAD]
    return (pl.sum_horizontal(superados) - 1).clip(lower_bound=0).cast(pl.Int8).alias("g")


def etiquetar_grupo(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(pl.col("g").replace_strict(dict(enumerate(ETIQUETAS_EDAD)), return_dtype=pl.Utf8).alias("grupo_edad"))


def tasa_fila() -> pl.Expr:
    """SV / (SV + NV) de una fila ya agregada. Denominador 0 da nulo."""
    denominador = (pl.col("SV") + pl.col("NV")).cast(pl.Float64)
    return pl.when(denominador > 0).then(pl.col("SV").cast(pl.Float64) / denominador)


def tasa_participacion(df: pl.DataFrame, por: list[str]) -> pl.DataFrame:
    """Cociente de sumas SV / (SV + NV), nunca promedio de tasas (D1, RF-05)."""
    return (df.group_by(por).agg(pl.col("SV").sum(), pl.col("NV").sum())
            .with_columns(tasa_fila().alias("tasa")).drop("SV", "NV"))


def con_region(datos):
    """Agrega la columna REGION (circunscripción 2023) a partir de EDOCVE."""
    return datos.with_columns(pl.col("EDOCVE").replace_strict(CIRCUNSCRIPCION, return_dtype=pl.Int8).alias("REGION"))


def agrupar_celdas(datos: pl.LazyFrame, territorio: str = "EDOCVE") -> pl.DataFrame:
    """Celda = grupo de edad × sexo × tipo de sección × territorio, por elección (D2b)."""
    if territorio == "REGION":
        datos = con_region(datos)
    return etiquetar_grupo(
        datos.with_columns(indice_grupo_edad())
        .group_by("AELEC", territorio, "TIPOSEC", "SEXO", "g")
        .agg(*[pl.col(c).sum().cast(pl.Int64) for c in SUMAS])
        .with_columns(pl.col("TIPOSEC").cast(pl.Utf8))
        .collect()
    )


def personas_90_o_mas(datos: pl.LazyFrame) -> pl.DataFrame:
    """Personas afectadas por el agrupamiento «90+», por elección (RF-04)."""
    return (datos.filter(pl.col("EDAD") >= 90).group_by("AELEC")
            .agg(pl.col("LN").sum().cast(pl.Int64).alias("LN_90_o_mas")).sort("AELEC").collect())


def filtrar_celdas_pequenas(celdas: pl.DataFrame, umbral: int = UMBRAL_LN, n_elecciones: int = len(ELECCIONES),
                            territorio: str = "EDOCVE"):
    """Conserva las celdas presentes en todas las elecciones con LN >= umbral en todas (D7).

    Devuelve (celdas conservadas, claves de las excluidas, ordenadas).
    """
    clave = clave_celda(territorio)
    todas = celdas.select(clave).unique()
    completas = (celdas.group_by(clave).agg(pl.len().alias("n"), pl.col("LN").min().alias("LN_min"))
                 .filter((pl.col("n") == n_elecciones) & (pl.col("LN_min") >= umbral)))
    excluidas = todas.join(completas.select(clave), on=clave, how="anti").sort(clave)
    return celdas.join(completas.select(clave), on=clave, how="inner"), excluidas


def participacion_relativa(celdas: pl.DataFrame, referencia: str = "entidad") -> pl.DataFrame:
    """Añade `tasa`, `tasa_ref` y `rel = tasa - tasa_ref` por celda y elección.

    referencia="entidad": tasa de la propia entidad en esa elección (D16b, corrida principal). Deja solo
    las diferencias entre grupos demográficos dentro de una entidad.
    referencia="nacional": promedio nacional de la elección (D4a original, análisis de apoyo).
    referencia="region": tasa de la circunscripción (spec 002, RF-13); las celdas deben traer REGION.
    """
    por_ref = REFERENCIAS[referencia]
    ref = tasa_participacion(celdas, por_ref).rename({"tasa": "tasa_ref"})
    return (celdas.join(ref, on=por_ref)
            .with_columns(tasa_fila().alias("tasa"))
            .with_columns((pl.col("tasa") - pl.col("tasa_ref")).alias("rel")))


def suma_ponderada_rel(largo: pl.DataFrame, por: list[str]) -> pl.DataFrame:
    """Comprobación RF-06: la diferencia relativa ponderada por votantes + no votantes suma 0 en cada grupo de referencia."""
    peso = (pl.col("SV") + pl.col("NV")).cast(pl.Float64)
    return (largo.group_by(por).agg(((pl.col("rel") * peso).sum() / peso.sum()).alias("suma_ponderada_rel")).sort(por))


def pivotar_ancha(largo: pl.DataFrame, territorio: str = "EDOCVE") -> pl.DataFrame:
    """Una fila por celda, una columna `rel_AAAA` por elección, más pesos de lista nominal."""
    clave = clave_celda(territorio)
    ancha = largo.pivot(on="AELEC", index=clave, values="rel").rename({str(e): f"rel_{e}" for e in ELECCIONES})
    pesos = largo.group_by(clave).agg(
        pl.col("LN").mean().alias("LN_medio"),
        pl.col("LN").filter(pl.col("AELEC") == ELECCIONES[-1]).first().alias(f"LN_{ELECCIONES[-1]}"))
    # El pivote no garantiza el orden de filas ni de columnas; se fija para que la corrida sea reproducible (RF-14).
    columnas = clave + [f"rel_{e}" for e in ELECCIONES] + ["LN_medio", f"LN_{ELECCIONES[-1]}"]
    return ancha.join(pesos, on=clave).select(columnas).sort(clave)
