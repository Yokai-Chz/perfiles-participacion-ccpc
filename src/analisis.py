"""Pasos del análisis, de los indicadores a los perfiles. Cada paso lee y escribe en disco.

La corrida principal usa la referencia por entidad (D16b). El notebook repite los pasos con la
referencia nacional (D4a original) como análisis de apoyo.
"""
import numpy as np
import polars as pl

import indicadores as ind
import perfiles as per
import segmentacion as seg
from configuracion import ELECCIONES, PROCESADOS, REFERENCIA_PRINCIPAL, SEMILLA, UMBRAL_LN, rutas


def _nombre(base: str, r: dict) -> str:
    return f"{base}{r['sufijo']}.parquet"


def paso_indicadores(referencia: str = REFERENCIA_PRINCIPAL) -> dict:
    """Celdas demográficas, exclusión de celdas pequeñas y participación relativa (RF-04 a RF-06)."""
    r = rutas(referencia)
    datos = pl.scan_parquet(sorted(PROCESADOS.glob("ccpc_*.parquet")))
    celdas = ind.agrupar_celdas(datos)
    celdas, excluidas = ind.filtrar_celdas_pequenas(celdas, UMBRAL_LN)
    excluidas.write_csv(r["tablas"] / "celdas_excluidas.csv")

    largo = ind.participacion_relativa(celdas, referencia)
    por = ["AELEC", "EDOCVE"] if referencia == "entidad" else ["AELEC"]
    chequeo = ind.suma_ponderada_rel(largo, por)
    assert chequeo["suma_ponderada_rel"].abs().max() < 1e-9, "la diferencia relativa ponderada debe sumar 0"

    ancha = ind.pivotar_ancha(largo)
    largo.write_parquet(r["procesados"] / _nombre("celdas_largo", r))
    ancha.write_parquet(r["procesados"] / _nombre("celdas_ancha", r))
    ancha.write_csv(r["tablas"] / "celdas_ancha.csv")
    nacional = ind.tasa_participacion(celdas, ["AELEC"]).rename({"tasa": "tasa_nacional"}).sort("AELEC")
    nacional.write_csv(r["tablas"] / "participacion_nacional_filtrada.csv")

    ln_total = datos.select(pl.col("LN").sum().cast(pl.Int64)).collect().item()
    pct_excluida = 100 * (1 - celdas["LN"].sum() / ln_total)
    pl.DataFrame({"celdas_conservadas": [ancha.height], "celdas_excluidas": [excluidas.height],
                  "pct_ln_excluida": [round(pct_excluida, 3)]}).write_csv(r["tablas"] / "resumen_indicadores.csv")
    return {"celdas": celdas, "excluidas": excluidas, "ancha": ancha, "nacional": nacional,
            "pct_ln_excluida": pct_excluida,
            "atipicas": ind.personas_90_o_mas(datos)}


def paso_segmentacion(referencia: str = REFERENCIA_PRINCIPAL) -> dict:
    """Rasgos, selección de k y asignación de perfil a cada celda (RF-07 a RF-09)."""
    r = rutas(referencia)
    ancha = pl.read_parquet(r["procesados"] / _nombre("celdas_ancha", r))
    rasgos = seg.matriz_rasgos(ancha)
    peso = ancha["LN_medio"].to_numpy()
    Z = seg.estandarizar(rasgos)

    seleccion, modelos = seg.evaluar_k(Z, peso, SEMILLA)
    seleccion.write_csv(r["tablas"] / "seleccion_k.csv")
    k = seg.elegir_k(seleccion)
    perfil = seg.etiquetas_por_nivel(modelos[k], rasgos, peso)

    asignacion = ancha.select(*ind.CLAVE_CELDA, "LN_medio", f"LN_{ELECCIONES[-1]}").with_columns(
        pl.Series("perfil", perfil, dtype=pl.Int8),
        *[pl.Series(n, rasgos[:, i]) for i, n in enumerate(seg.NOMBRES_RASGOS)])
    asignacion.write_parquet(r["procesados"] / _nombre("celdas_perfil", r))
    asignacion.write_csv(r["tablas"] / "celdas_perfil.csv")
    (r["tablas"] / "k_elegido.txt").write_text(str(k))
    return {"k": k, "seleccion": seleccion, "asignacion": asignacion, "correlaciones": np.corrcoef(rasgos.T)}


def paso_perfiles(referencia: str = REFERENCIA_PRINCIPAL) -> dict:
    """Caracterización de cada perfil y composición de las secciones (RF-10)."""
    r = rutas(referencia)
    asig = pl.read_parquet(r["procesados"] / _nombre("celdas_perfil", r))
    largo = pl.read_parquet(r["procesados"] / _nombre("celdas_largo", r))
    t = r["tablas"]

    peso = per.peso_y_rasgos(asig)
    peso.write_csv(t / "perfiles_peso_rasgos.csv")
    participacion = per.participacion_por_perfil(largo.join(asig.select(*ind.CLAVE_CELDA, "perfil"), on=ind.CLAVE_CELDA))
    participacion.write_csv(t / "perfiles_participacion.csv")

    sexo = per.distribucion(asig, "SEXO").rename({"0": "pct_hombres", "1": "pct_mujeres"})
    tipo = per.distribucion(asig, "TIPOSEC")
    edad = per.distribucion_edad(asig)
    mediana = per.grupo_edad_mediano(asig)
    for nombre, tabla in [("sexo", sexo), ("tipo_seccion", tipo), ("edad", edad), ("edad_mediana", mediana)]:
        tabla.write_csv(t / f"perfiles_{nombre}.csv")

    ent = per.composicion_entidades(asig)
    ent_ancha = ent.pivot(on="perfil", index="EDOCVE", values="pct").sort("EDOCVE").fill_null(0.0)
    ent_ancha.write_csv(t / "entidades_composicion.csv")
    top = per.top_entidades(ent, peso)
    top.write_csv(t / "perfiles_top_entidades.csv")

    comp, sin_perfil, total = per.composicion_secciones(PROCESADOS / f"ccpc_{ELECCIONES[-1]}.parquet", asig)
    comp.write_parquet(r["procesados"] / _nombre("composicion_secciones_2024", r))
    per.secciones_mayoritarias(comp).write_csv(t / "perfiles_secciones_mayoritarias.csv")
    k = int(asig["perfil"].max())
    sumas = comp.select(pl.sum_horizontal([f"prop_perfil_{i}" for i in range(1, k + 1)]).alias("s"))["s"]
    assert abs(sumas.min() - 1) < 1e-9 and abs(sumas.max() - 1) < 1e-9, "la composición de cada sección debe sumar 1"
    return {"peso": peso, "participacion": participacion, "sexo": sexo, "tipo": tipo, "edad": edad, "mediana": mediana,
            "entidades": ent_ancha, "top": top, "comp": comp, "ln_sin_perfil": sin_perfil, "ln_total": total,
            "entidades_dominantes": per.entidades_dominantes(ent_ancha)}

