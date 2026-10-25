"""Pasos del análisis, de los indicadores a los perfiles. Cada paso lee y escribe en disco.

La corrida principal usa la referencia por entidad (D16b). Las demás corridas de `CORRIDAS` son análisis
de apoyo (spec 001, D16; spec 002, RF-02, RF-13 y D2b) y se comparan con la principal en `paso_comparar_corridas`.
"""
import numpy as np
import polars as pl
from sklearn.metrics import adjusted_rand_score

import calidad
import cohortes as coh
import indicadores as ind
import perfiles as per
import segmentacion as seg
import territorio as ter
from configuracion import (CIRCUNSCRIPCION, ELECCIONES, PROCESADOS, REFERENCIA_PRINCIPAL, SEMILLA, TABLAS, UMBRAL_LN,
                           UMBRAL_NS, rutas)

# referencia: contra qué se mide la participación relativa. territorio: columna territorial de la celda.
# excluir_ns: quita las secciones con NS alto. volatilidad: agrega el cuarto rasgo. indicadores: de qué corrida
# toma la tabla ancha (la variante con volatilidad reutiliza la de la principal).
CORRIDAS = {
    "entidad": {"referencia": "entidad", "territorio": "EDOCVE", "excluir_ns": False, "volatilidad": False, "indicadores": "entidad"},
    "nacional": {"referencia": "nacional", "territorio": "EDOCVE", "excluir_ns": False, "volatilidad": False, "indicadores": "nacional"},
    "ns": {"referencia": "entidad", "territorio": "EDOCVE", "excluir_ns": True, "volatilidad": False, "indicadores": "ns"},
    "volatilidad": {"referencia": "entidad", "territorio": "EDOCVE", "excluir_ns": False, "volatilidad": True, "indicadores": "entidad"},
    "region": {"referencia": "region", "territorio": "REGION", "excluir_ns": False, "volatilidad": False, "indicadores": "region"},
}
ULTIMA = ELECCIONES[-1]


def _nombre(base: str, r: dict) -> str:
    return f"{base}{r['sufijo']}.parquet"


def _csv(df: pl.DataFrame, ruta) -> None:
    """Escribe con 12 cifras significativas: el último dígito de algunos cálculos varía entre corridas (RNF-02)."""
    df.with_columns(pl.col(pl.Float64).round_sig_figs(12)).write_csv(ruta)


def _datos() -> pl.LazyFrame:
    return pl.scan_parquet(sorted(PROCESADOS.glob("ccpc_*.parquet")))


def _secciones_marcadas(datos: pl.LazyFrame) -> pl.DataFrame:
    return calidad.secciones_ns_alto(calidad.ns_por_seccion(datos), UMBRAL_NS).select("AELEC", "EDOCVE", "SECCION")


def paso_indicadores(corrida: str = REFERENCIA_PRINCIPAL) -> dict:
    """Celdas demográficas, exclusión de celdas pequeñas y participación relativa (RF-04 a RF-06)."""
    c, r = CORRIDAS[corrida], rutas(corrida)
    todos = _datos()
    datos = todos
    if c["excluir_ns"]:
        datos = todos.join(_secciones_marcadas(todos).lazy(), on=["AELEC", "EDOCVE", "SECCION"], how="anti")
    territorio = c["territorio"]
    celdas = ind.agrupar_celdas(datos, territorio)
    celdas, excluidas = ind.filtrar_celdas_pequenas(celdas, UMBRAL_LN, territorio=territorio)
    _csv(excluidas, r["tablas"] / "celdas_excluidas.csv")

    largo = ind.participacion_relativa(celdas, c["referencia"])
    chequeo = ind.suma_ponderada_rel(largo, ind.REFERENCIAS[c["referencia"]])
    assert chequeo["suma_ponderada_rel"].abs().max() < 1e-9, "la diferencia relativa ponderada debe sumar 0"

    ancha = ind.pivotar_ancha(largo, territorio)
    largo.write_parquet(r["procesados"] / _nombre("celdas_largo", r))
    ancha.write_parquet(r["procesados"] / _nombre("celdas_ancha", r))
    _csv(ancha, r["tablas"] / "celdas_ancha.csv")
    nacional = ind.tasa_participacion(celdas, ["AELEC"]).rename({"tasa": "tasa_nacional"}).sort("AELEC")
    _csv(nacional, r["tablas"] / "participacion_nacional_filtrada.csv")

    ln_total = todos.select(pl.col("LN").sum().cast(pl.Int64)).collect().item()
    pct_excluida = 100 * (1 - celdas["LN"].sum() / ln_total)
    _csv(pl.DataFrame({"celdas_conservadas": [ancha.height], "celdas_excluidas": [excluidas.height],
                       "pct_ln_excluida": [round(pct_excluida, 3)]}), r["tablas"] / "resumen_indicadores.csv")
    return {"celdas": celdas, "excluidas": excluidas, "ancha": ancha, "nacional": nacional,
            "pct_ln_excluida": pct_excluida, "atipicas": ind.personas_90_o_mas(datos)}


def paso_segmentacion(corrida: str = REFERENCIA_PRINCIPAL) -> dict:
    """Rasgos, selección de k y asignación de perfil a cada celda (RF-07 a RF-09)."""
    c, r = CORRIDAS[corrida], rutas(corrida)
    fuente = rutas(c["indicadores"])
    ancha = pl.read_parquet(fuente["procesados"] / _nombre("celdas_ancha", fuente))
    rasgos = seg.matriz_rasgos(ancha, c["volatilidad"])
    peso = ancha["LN_medio"].to_numpy()
    Z = seg.estandarizar(rasgos)

    seleccion, modelos = seg.evaluar_k(Z, peso, SEMILLA)
    _csv(seleccion, r["tablas"] / "seleccion_k.csv")
    k = seg.elegir_k(seleccion)
    perfil = seg.etiquetas_por_nivel(modelos[k], rasgos, peso)

    clave = ind.clave_celda(c["territorio"])
    asignacion = ancha.select(*clave, "LN_medio", f"LN_{ULTIMA}").with_columns(
        pl.Series("perfil", perfil, dtype=pl.Int8),
        *[pl.Series(n, rasgos[:, i]) for i, n in enumerate(seg.NOMBRES_RASGOS)],
        pl.Series("volatilidad", seg.volatilidad(ancha)))
    asignacion.write_parquet(r["procesados"] / _nombre("celdas_perfil", r))
    _csv(asignacion, r["tablas"] / "celdas_perfil.csv")
    (r["tablas"] / "k_elegido.txt").write_text(str(k))
    return {"k": k, "seleccion": seleccion, "asignacion": asignacion, "correlaciones": np.corrcoef(rasgos.T)}


def paso_perfiles(corrida: str = REFERENCIA_PRINCIPAL) -> dict:
    """Caracterización de cada perfil y composición de las secciones (RF-10).

    La corrida por región no tiene entidad en sus celdas: no calcula composición por entidad ni por sección.
    """
    c, r = CORRIDAS[corrida], rutas(corrida)
    fuente = rutas(c["indicadores"])
    clave = ind.clave_celda(c["territorio"])
    asig = pl.read_parquet(r["procesados"] / _nombre("celdas_perfil", r))
    largo = pl.read_parquet(fuente["procesados"] / _nombre("celdas_largo", fuente))
    t = r["tablas"]

    peso = per.peso_y_rasgos(asig)
    _csv(peso, t / "perfiles_peso_rasgos.csv")
    participacion = per.participacion_por_perfil(largo.join(asig.select(*clave, "perfil"), on=clave))
    _csv(participacion, t / "perfiles_participacion.csv")

    sexo = per.distribucion(asig, "SEXO").rename({"0": "pct_hombres", "1": "pct_mujeres"})
    tipo = per.distribucion(asig, "TIPOSEC")
    edad = per.distribucion_edad(asig)
    mediana = per.grupo_edad_mediano(asig)
    for nombre, tabla in [("sexo", sexo), ("tipo_seccion", tipo), ("edad", edad), ("edad_mediana", mediana)]:
        _csv(tabla, t / f"perfiles_{nombre}.csv")
    salida = {"peso": peso, "participacion": participacion, "sexo": sexo, "tipo": tipo, "edad": edad, "mediana": mediana}
    if c["territorio"] != "EDOCVE":
        return salida

    ent = per.composicion_entidades(asig)
    ent_ancha = per.ancha_por_perfil(ent, "EDOCVE", "pct")
    _csv(ent_ancha, t / "entidades_composicion.csv")
    top = per.top_entidades(ent, peso)
    _csv(top, t / "perfiles_top_entidades.csv")

    comp, sin_perfil, total = per.composicion_secciones(PROCESADOS / f"ccpc_{ULTIMA}.parquet", asig)
    comp.write_parquet(r["procesados"] / _nombre(f"composicion_secciones_{ULTIMA}", r))
    _csv(per.secciones_mayoritarias(comp), t / "perfiles_secciones_mayoritarias.csv")
    k = int(asig["perfil"].max())
    sumas = comp.select(pl.sum_horizontal([f"prop_perfil_{i}" for i in range(1, k + 1)]).alias("s"))["s"]
    assert abs(sumas.min() - 1) < 1e-9 and abs(sumas.max() - 1) < 1e-9, "la composición de cada sección debe sumar 1"
    return salida | {"entidades": ent_ancha, "top": top, "comp": comp, "ln_sin_perfil": sin_perfil, "ln_total": total,
                     "entidades_dominantes": per.entidades_dominantes(ent_ancha)}


def paso_comparar_corridas(corridas=("nacional", "ns", "volatilidad", "region")) -> pl.DataFrame:
    """k, ARI frente a la principal y celdas comparadas de cada corrida de apoyo (spec 002, RF-02 y RF-13).

    En la corrida por región, cada celda de entidad recibe el perfil de la celda de región que la contiene.
    """
    principal = pl.read_parquet(PROCESADOS / "celdas_perfil.parquet")
    filas = []
    for corrida in corridas:
        r = rutas(corrida)
        otra = pl.read_parquet(r["procesados"] / _nombre("celdas_perfil", r)).select(*ind.clave_celda(CORRIDAS[corrida]["territorio"]), pl.col("perfil").alias("perfil_otra"))
        base = principal
        if CORRIDAS[corrida]["territorio"] == "REGION":
            base = ind.con_region(principal)
        cruce = base.join(otra, on=[col for col in otra.columns if col != "perfil_otra"])
        filas.append({"corrida": corrida, "k": int(otra["perfil_otra"].max()), "celdas_principal": principal.height,
                      "celdas_comparadas": cruce.height,
                      "pct_LN_comparada": 100 * cruce[f"LN_{ULTIMA}"].sum() / principal[f"LN_{ULTIMA}"].sum(),
                      "ARI_vs_principal": adjusted_rand_score(cruce["perfil"], cruce["perfil_otra"])})
    tabla = pl.DataFrame(filas)
    _csv(tabla, TABLAS / "sensibilidad_corridas.csv")
    return tabla


def paso_calidad_ns() -> dict:
    """Secciones con NS alto, su resumen y la distribución de NS por sección (spec 002, RF-01)."""
    por_seccion = calidad.ns_por_seccion(_datos())
    marcadas = calidad.secciones_ns_alto(por_seccion, UMBRAL_NS)
    resumen = calidad.resumen_ns_alto(por_seccion, UMBRAL_NS)
    distribucion = calidad.distribucion_ns(por_seccion)
    _csv(marcadas, TABLAS / "secciones_ns_alto.csv")
    _csv(resumen, TABLAS / "resumen_ns_alto.csv")
    _csv(distribucion, TABLAS / "distribucion_ns.csv")
    return {"marcadas": marcadas, "resumen": resumen, "distribucion": distribucion}


def paso_robustez() -> dict:
    """PCA y comparación de k-means con Ward y con una mezcla gaussiana sobre la corrida principal (RF-04, RF-05)."""
    ancha = pl.read_parquet(PROCESADOS / "celdas_ancha.parquet")
    asig = pl.read_parquet(PROCESADOS / "celdas_perfil.parquet")
    rasgos = seg.matriz_rasgos(ancha)
    peso = ancha["LN_medio"].to_numpy()
    Z = seg.estandarizar(rasgos)
    etiquetas = asig["perfil"].to_numpy()
    k = int(etiquetas.max())

    p = seg.pca(Z, seg.NOMBRES_RASGOS)
    _csv(p["varianza"], TABLAS / "pca_varianza.csv")
    _csv(p["cargas"], TABLAS / "pca_cargas.csv")
    coords = asig.select(*ind.CLAVE_CELDA, "perfil", "LN_medio").with_columns(
        pl.Series("PC1", p["coordenadas"][:, 0]), pl.Series("PC2", p["coordenadas"][:, 1]))
    _csv(coords, TABLAS / "celdas_pca.csv")

    comparacion, bic, otros = seg.comparar_metodos(Z, etiquetas, k, SEMILLA)
    _csv(comparacion, TABLAS / "robustez_metodos.csv")
    _csv(bic, TABLAS / "robustez_bic_mezcla.csv")
    for nombre, etq in otros.items():
        numerada = seg.numerar_por_nivel(etq, rasgos[:, 0], peso)
        _csv(seg.cruce(etiquetas, numerada, peso, "perfil_kmeans", f"grupo_{nombre}"), TABLAS / f"robustez_cruce_{nombre}.csv")
    return {"pca": p, "comparacion": comparacion, "bic": bic}


def paso_cohortes() -> dict:
    """Curva por edad, cohortes quinquenales, efecto primer voto y cohortes por perfil (RF-06 a RF-08)."""
    exacta = coh.por_edad_exacta(_datos())
    curva = coh.curva_por_edad(exacta)
    quinq = coh.cohortes_quinquenales(exacta)
    quinq_sexo = coh.cohortes_quinquenales(exacta, ("SEXO",))
    primer = coh.efecto_primer_voto(exacta)
    asig = pl.read_parquet(PROCESADOS / "celdas_perfil.parquet")
    por_perfil = coh.cohortes_por_perfil(pl.scan_parquet(PROCESADOS / f"ccpc_{ULTIMA}.parquet"), asig)
    for nombre, tabla in [("cohortes_curva_edad", curva), ("cohortes_participacion", quinq), ("cohortes_sexo", quinq_sexo),
                          ("efecto_primer_voto", primer), ("cohortes_por_perfil", por_perfil)]:
        _csv(tabla, TABLAS / f"{nombre}.csv")
    return {"curva": curva, "quinquenales": quinq, "sexo": quinq_sexo, "primer_voto": primer, "por_perfil": por_perfil}


def paso_territorio() -> dict:
    """Equivalencia de secciones, trayectoria y composición por distrito federal (RF-09 a RF-12)."""
    datos = _datos()
    p2021, pult = PROCESADOS / "ccpc_2021.parquet", PROCESADOS / f"ccpc_{ULTIMA}.parquet"
    eq = ter.equivalencia_secciones(p2021, pult)
    eq.write_parquet(PROCESADOS / "equivalencia_secciones.parquet")
    sin = ter.sin_correspondencia(eq, pult)
    _csv(sin, TABLAS / "distritos_sin_correspondencia.csv")

    largo = ter.distritos_largo(datos, eq)
    cons = ter.conservacion(largo, datos)
    assert cons["cuadra"].all(), "la lista nominal por distrito no cuadra con el total"
    _csv(cons, TABLAS / "distritos_conservacion.csv")
    _csv(largo, TABLAS / "distritos_largo.csv")

    ancha = ter.ancha_distritos(largo)
    rasgos = seg.matriz_rasgos(ancha, con_volatilidad=True)
    tray = ancha.with_columns(*[pl.Series(n, rasgos[:, i]) for i, n in enumerate(seg.NOMBRES_RASGOS_VOLATILIDAD)],
                              pl.col("EDOCVE").replace_strict(CIRCUNSCRIPCION, return_dtype=pl.Int8).alias("circunscripcion"))
    _csv(tray, TABLAS / "distritos_trayectoria.csv")

    comp = pl.read_parquet(PROCESADOS / f"composicion_secciones_{ULTIMA}.parquet")
    salidas = {}
    for marco in ["DEF_2023", "DEF_2021"]:
        salidas[marco] = ter.composicion_distritos(comp, pult, eq, marco)
        _csv(salidas[marco], TABLAS / f"distritos_composicion_{marco[-4:]}.csv")
    circ = per.composicion_circunscripcion(salidas["DEF_2023"])
    _csv(circ, TABLAS / "circunscripcion_composicion.csv")
    return {"equivalencia": eq, "sin_correspondencia": sin, "conservacion": cons, "largo": largo,
            "trayectoria": tray, "composicion": salidas, "circunscripcion": circ}


def paso_descriptivas() -> dict:
    """Tablas de estadísticas descriptivas de los datos para las figuras de apoyo (spec 002, RF-16)."""
    datos = _datos()
    piramide = (datos.filter(pl.col("AELEC") == ULTIMA).with_columns(ind.indice_grupo_edad())
                .group_by("g", "SEXO").agg(pl.col("LN").sum().cast(pl.Int64)).collect())
    piramide = ind.etiquetar_grupo(piramide).sort("g", "SEXO")
    por_tipo = (datos.with_columns(pl.col("TIPOSEC").cast(pl.Utf8))
                .group_by("AELEC", "TIPOSEC").agg(pl.col("LN").sum().cast(pl.Int64), pl.col("SV").sum().cast(pl.Int64),
                                                  pl.col("NV").sum().cast(pl.Int64))
                .collect().with_columns(ind.tasa_fila().alias("tasa")).sort("AELEC", "TIPOSEC"))
    por_entidad = (datos.group_by("AELEC", "EDOCVE").agg(pl.col("SV").sum().cast(pl.Int64), pl.col("NV").sum().cast(pl.Int64))
                   .collect().with_columns(ind.tasa_fila().alias("tasa")).sort("AELEC", "EDOCVE"))
    for nombre, tabla in [("descriptiva_piramide_2024", piramide), ("descriptiva_participacion_tipo", por_tipo),
                          ("descriptiva_participacion_entidad", por_entidad)]:
        _csv(tabla, TABLAS / f"{nombre}.csv")
    return {"piramide": piramide, "tipo": por_tipo, "entidad": por_entidad}
