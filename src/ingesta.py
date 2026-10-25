"""Lectura de los CSV del CCPC y escritura de un Parquet por elección (RF-01, RF-03)."""
from pathlib import Path

import polars as pl

ESQUEMA = ["AELEC", "FELECCION", "EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM", "SECCION", "TIPOSEC",
           "DEF", "DEL", "SEXO", "EDAD", "LN", "SV", "NV", "NS"]

# Tipos compactos (RNF-04). DEF llega hasta 300, por eso Int16.
TIPOS = {"AELEC": pl.Int16, "EDOCVE": pl.Int8, "MPIOCVE": pl.Int16, "SECCION": pl.Int32,
         "DEF": pl.Int16, "DEL": pl.Int16, "SEXO": pl.Int8, "EDAD": pl.Int16,
         "LN": pl.Int32, "SV": pl.Int32, "NV": pl.Int32, "NS": pl.Int32}


def listar_por_anio(carpeta: Path) -> dict[int, list[Path]]:
    """Agrupa los CSV de los CCPC por año de elección, buscando en subcarpetas (2021 viene anidado)."""
    por_anio: dict[int, list[Path]] = {}
    for ruta in sorted(carpeta.rglob("*conteoscensales*.csv")):   # otras fuentes en datasets/ (p. ej. eceg_2020) no entran
        anio = int(ruta.stem.split("conteoscensales")[1][:4])
        por_anio.setdefault(anio, []).append(ruta)
    return por_anio


def leer_entidad(ruta: Path) -> pl.DataFrame:
    """Lee el CSV de una entidad; falla con error explícito si el esquema difiere.

    Se descartan FELECCION, EDONOM y MPIONOM (texto repetido); la clave es EDOCVE y MPIOCVE.
    """
    df = pl.read_csv(ruta, schema_overrides={c: pl.Int64 for c in TIPOS} | {"TIPOSEC": pl.Utf8})
    if df.columns != ESQUEMA:
        raise ValueError(f"Esquema distinto en {ruta.name}: {df.columns}")
    return df.select(list(TIPOS) + ["TIPOSEC"]).cast(TIPOS)


def catalogo_entidades(rutas: list[Path]) -> pl.DataFrame:
    """Clave y nombre de cada entidad, leídos de la primera fila de sus CSV."""
    filas = [pl.read_csv(r, n_rows=1, columns=["EDOCVE", "EDONOM"]) for r in rutas]
    return pl.concat(filas).unique().sort("EDOCVE")


def escribir_parquet_por_anio(por_anio: dict[int, list[Path]], destino: Path, regenerar: bool = False) -> None:
    for anio, rutas in sorted(por_anio.items()):
        salida = destino / f"ccpc_{anio}.parquet"
        if salida.exists() and not regenerar:
            print(anio, "ya existe, se omite")
            continue
        df = pl.concat([leer_entidad(r) for r in rutas]).with_columns(pl.col("TIPOSEC").cast(pl.Categorical))
        df.write_parquet(salida, compression="zstd")
        print(f"{anio}: {df.height:,} filas en {salida.name}")
