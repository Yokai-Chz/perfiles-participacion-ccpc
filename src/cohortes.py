"""Cohortes de nacimiento como pseudo-panel y efecto del primer voto (spec 002, RF-06 a RF-08 y RF-15).

Una cohorte agrupa a quienes nacieron el mismo año (o quinquenio) y se observa en cada elección.
No sigue a las mismas personas: cambia por migración, defunciones y altas en el padrón.
El año de nacimiento es aproximado (año de la elección menos edad, ±1 año por la fecha de la jornada).
"""
import polars as pl

from configuracion import ELECCIONES
from indicadores import indice_grupo_edad, tasa_fila

EDAD_MAXIMA = 89            # 90+ queda fuera: edades atípicas (D6 de la 001)
PRIMER_VOTO = (18, 20)      # edad en la primera elección observada de la cohorte


def etiqueta_quinquenio(nacimiento: pl.Expr) -> pl.Expr:
    """Quinquenios que terminan en 0 y 5 (1986-1990, 1991-1995, ...). La última cohorte puede quedar incompleta."""
    inicio = nacimiento - (nacimiento - 1) % 5
    return pl.format("{}-{}", inicio, inicio + 4)


def por_edad_exacta(datos: pl.LazyFrame) -> pl.DataFrame:
    """Participación por elección, entidad, sexo, tipo de sección y edad exacta, con su referencia de entidad."""
    base = (datos.filter(pl.col("EDAD") <= EDAD_MAXIMA)
            .group_by("AELEC", "EDOCVE", "SEXO", "TIPOSEC", "EDAD")
            .agg(*[pl.col(c).sum().cast(pl.Int64) for c in ["LN", "SV", "NV"]])
            .with_columns(pl.col("TIPOSEC").cast(pl.Utf8), (pl.col("AELEC") - pl.col("EDAD")).alias("nacimiento"))
            .collect())
    # Referencia D16b: tasa de toda la entidad en esa elección, con las mismas filas.
    ref = (base.group_by("AELEC", "EDOCVE").agg(pl.col("SV").sum(), pl.col("NV").sum())
           .with_columns(tasa_fila().alias("tasa_ref")).select("AELEC", "EDOCVE", "tasa_ref"))
    return (base.join(ref, on=["AELEC", "EDOCVE"])
            .with_columns(tasa_fila().alias("tasa"))
            .with_columns((pl.col("tasa") - pl.col("tasa_ref")).alias("rel")))


def _resumir(df: pl.DataFrame, por: list[str]) -> pl.DataFrame:
    """Tasa como cociente de sumas y participación relativa ponderada por votantes más no votantes."""
    w = (pl.col("SV") + pl.col("NV")).cast(pl.Float64)
    return (df.group_by(por)
            .agg(pl.col("LN").sum(), pl.col("SV").sum(), pl.col("NV").sum(),
                 ((pl.col("rel") * w).sum() / w.sum()).alias("rel"),
                 ((pl.col("EDAD") * pl.col("LN")).sum() / pl.col("LN").sum()).alias("edad_media"))
            .with_columns(tasa_fila().alias("tasa"))
            .sort(por))


def curva_por_edad(exacta: pl.DataFrame) -> pl.DataFrame:
    """Tasa y participación relativa nacional por edad exacta en cada elección."""
    return _resumir(exacta, ["AELEC", "EDAD"]).select("AELEC", "EDAD", "LN", "tasa", "rel")


def cohortes_quinquenales(exacta: pl.DataFrame, por: tuple[str, ...] = ()) -> pl.DataFrame:
    """Cohortes de cinco años × elección (D5b), opcionalmente por sexo o tipo de sección."""
    df = exacta.with_columns(etiqueta_quinquenio(pl.col("nacimiento")).alias("cohorte"))
    return _resumir(df, ["cohorte", *por, "AELEC"]).select("cohorte", *por, "AELEC", "edad_media", "LN", "tasa", "rel")


def efecto_primer_voto(exacta: pl.DataFrame) -> pl.DataFrame:
    """Participación relativa de cada cohorte anual en su primera elección (18 a 20 años) y después (RF-07).

    Se usa la participación relativa a la entidad para no confundir el cambio con el tipo de elección.
    """
    anual = _resumir(exacta, ["nacimiento", "AELEC"]).with_columns((pl.col("AELEC") - pl.col("nacimiento")).alias("edad"))
    primera = (anual.filter(pl.col("edad") >= PRIMER_VOTO[0]).sort("nacimiento", "AELEC")
               .group_by("nacimiento", maintain_order=True).first()
               .filter(pl.col("edad") <= PRIMER_VOTO[1])
               .select("nacimiento", pl.col("AELEC").alias("primera_eleccion"), pl.col("edad").alias("edad_primera"),
                       pl.col("rel").alias("rel_primera"), pl.col("LN").alias("LN_primera")))
    siguiente = anual.select("nacimiento", "AELEC", "rel")
    salida = primera
    for nombre, salto in [("siguiente", 3), ("seis_anios", 6)]:
        salida = salida.join(
            siguiente.rename({"AELEC": "eleccion", "rel": f"rel_{nombre}"}).with_columns((pl.col("eleccion") - salto).alias("primera_eleccion")),
            on=["nacimiento", "primera_eleccion"], how="left").drop("eleccion")
        salida = salida.with_columns((pl.col(f"rel_{nombre}") - pl.col("rel_primera")).alias(f"cambio_{nombre}"))
    return salida.sort("nacimiento")


def resumen_primer_voto(efecto: pl.DataFrame) -> pl.DataFrame:
    """Promedios simples entre cohortes que votaron por primera vez a los 18 años.

    Las cifras «con seguimiento» usan solo las cohortes que tienen elección tres años después, para comparar
    los mismos grupos antes y después. Se reporta también la media de todas las cohortes de 18 años.
    """
    a18 = efecto.filter(pl.col("edad_primera") == PRIMER_VOTO[0])
    con = a18.drop_nulls("rel_siguiente")
    return pl.DataFrame({
        "cohortes_con_seguimiento": [con.height],
        "nacimiento_desde": [con["nacimiento"].min()], "nacimiento_hasta": [con["nacimiento"].max()],
        "rel_a_los_18": [con["rel_primera"].mean()], "rel_tres_anios_despues": [con["rel_siguiente"].mean()],
        "cohortes_de_18_total": [a18.height], "rel_a_los_18_todas": [a18["rel_primera"].mean()],
    })


def cohortes_por_perfil(datos_ultima: pl.LazyFrame, asig: pl.DataFrame) -> pl.DataFrame:
    """Porcentaje de la lista nominal de la última elección de cada perfil que pertenece a cada cohorte quinquenal (RF-08)."""
    ultima = ELECCIONES[-1]
    filas = (datos_ultima.filter(pl.col("EDAD") <= EDAD_MAXIMA)
             .with_columns(pl.col("TIPOSEC").cast(pl.Utf8), indice_grupo_edad(),
                           etiqueta_quinquenio(pl.lit(ultima) - pl.col("EDAD")).alias("cohorte"))
             .group_by("EDOCVE", "TIPOSEC", "SEXO", "g", "cohorte").agg(pl.col("LN").sum().cast(pl.Int64))
             .collect()
             .join(asig.select("EDOCVE", "TIPOSEC", "SEXO", "g", "perfil"), on=["EDOCVE", "TIPOSEC", "SEXO", "g"]))
    return (filas.group_by("perfil", "cohorte").agg(pl.col("LN").sum())
            .with_columns((100 * pl.col("LN") / pl.col("LN").sum().over("perfil")).alias("pct"))
            .sort("perfil", "cohorte"))
