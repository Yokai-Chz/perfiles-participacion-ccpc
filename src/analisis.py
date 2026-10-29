"""Pasos del análisis, de los indicadores a los perfiles. Cada paso lee y escribe en disco.

La corrida principal usa la referencia por entidad (D16b). Las demás corridas de `CORRIDAS` son análisis
de apoyo (spec 001, D16; spec 002, RF-02, RF-13 y D2b) y se comparan con la principal en `paso_comparar_corridas`.
"""
import numpy as np
import polars as pl
from sklearn.metrics import adjusted_rand_score

import calidad
import cohortes as coh
import contenido
import escolaridad as esc
import experimentos as exp
import figuras
import indicadores as ind
import perfiles as per
import segmentacion as seg
import territorio as ter
from configuracion import (CIRCUNSCRIPCION, ECEG, ELECCIONES, ESTADISTICAS, PROCESADOS, REFERENCIA_PRINCIPAL, SEMILLA, TABLAS, UMBRAL_LN,
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
    # Spec 003: la tabla ancha de la principal más la escolaridad del entorno relativa a la entidad.
    "escolaridad": {"referencia": "entidad", "territorio": "EDOCVE", "excluir_ns": False, "volatilidad": False, "indicadores": "entidad",
                    "extras": ("esc_rel",)},
}
ULTIMA = ELECCIONES[-1]


def _nombre(base: str, r: dict) -> str:
    return f"{base}{r['sufijo']}.parquet"


def _csv(df: pl.DataFrame, ruta) -> None:
    """Escribe con 10 cifras significativas (RNF-02).

    Las sumas en paralelo cambian el último dígito entre corridas; con 12 cifras ese ruido a veces cruzaba el redondeo.
    """
    df.with_columns(pl.col(pl.Float64).round_sig_figs(10)).write_csv(ruta)


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
    extras = c.get("extras", ())
    if extras:
        datos_extra = pl.read_parquet(PROCESADOS / "escolaridad_celdas.parquet").select(*ind.CLAVE_CELDA, *extras)
        ancha = ancha.join(datos_extra, on=ind.CLAVE_CELDA, how="inner")   # celdas sin dato quedan fuera y se reportan
    rasgos = seg.matriz_rasgos(ancha, c["volatilidad"], extras)
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
    n_secciones = (pl.scan_parquet(PROCESADOS / f"ccpc_{ULTIMA}.parquet").select("EDOCVE", "SECCION").unique()
                   .select(pl.len()).collect().item())
    _csv(per.secciones_mayoritarias(comp, n_secciones), t / "perfiles_secciones_mayoritarias.csv")
    k = int(asig["perfil"].max())
    sumas = comp.select(pl.sum_horizontal([f"prop_perfil_{i}" for i in range(1, k + 1)]).alias("s"))["s"]
    assert abs(sumas.min() - 1) < 1e-9 and abs(sumas.max() - 1) < 1e-9, "la composición de cada sección debe sumar 1"
    return salida | {"entidades": ent_ancha, "top": top, "comp": comp, "ln_sin_perfil": sin_perfil, "ln_total": total,
                     "entidades_dominantes": per.entidades_dominantes(ent_ancha)}


def paso_comparar_corridas(corridas=None) -> pl.DataFrame:
    """k, ARI frente a la principal y celdas comparadas de cada corrida de apoyo (spec 002, RF-02 y RF-13; spec 003, RF-06).

    En la corrida por región, cada celda de entidad recibe el perfil de la celda de región que la contiene.
    Por omisión compara todas las corridas de apoyo que ya tienen asignación. Escribe además la tabla de cruce
    (lista nominal 2024 por perfil principal y perfil de la corrida) de cada una.
    """
    if corridas is None:
        corridas = [c for c in CORRIDAS if c != REFERENCIA_PRINCIPAL
                    and (PROCESADOS / _nombre("celdas_perfil", rutas(c))).exists()]
    principal = pl.read_parquet(PROCESADOS / "celdas_perfil.parquet")
    filas = []
    for corrida in corridas:
        r = rutas(corrida)
        otra = pl.read_parquet(r["procesados"] / _nombre("celdas_perfil", r)).select(*ind.clave_celda(CORRIDAS[corrida]["territorio"]), pl.col("perfil").alias("perfil_otra"))
        base = principal
        if CORRIDAS[corrida]["territorio"] == "REGION":
            base = ind.con_region(principal)
        cruce = base.join(otra, on=[col for col in otra.columns if col != "perfil_otra"])
        _csv(cruce.group_by("perfil", "perfil_otra").agg(pl.col(f"LN_{ULTIMA}").sum()).sort("perfil", "perfil_otra"),
             TABLAS / f"sensibilidad_cruce_{corrida}.csv")
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
    _csv(coh.resumen_primer_voto(primer), TABLAS / "efecto_primer_voto_resumen.csv")
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


def paso_escolaridad() -> dict | None:
    """Escolaridad del entorno por celda y por perfil a partir de la ECEG 2020 (spec 003). Sin datos, avisa y no hace nada."""
    if not ECEG.exists() or not any(ECEG.iterdir()):
        print(f"No hay datos de la ECEG 2020 en {ECEG}; se omite la escolaridad (spec 003, D5).")
        return None
    eceg = esc.leer_eceg(ECEG)
    ln = esc.lista_por_seccion_y_celda(PROCESADOS / "ccpc_2021.parquet")
    unida, union = esc.unir_secciones(ln, eceg)
    _csv(union, TABLAS / "escolaridad_union.csv")
    cobertura = float(100 * union["LN_sin_eceg"].sum() / union["LN_2021"].sum())
    assert cobertura < 5, f"{cobertura:.1f} % de la LN 2021 sin escolaridad: se detiene (spec 003, criterio de finalización)"

    celdas = esc.relativa_a_entidad(esc.por_celda(unida))
    celdas.write_parquet(PROCESADOS / "escolaridad_celdas.parquet")
    _csv(celdas, TABLAS / "escolaridad_celdas.csv")
    asig = pl.read_parquet(PROCESADOS / "celdas_perfil.parquet")
    perfil = esc.por_perfil(celdas, asig)
    _csv(perfil, TABLAS / "escolaridad_por_perfil.csv")
    w = celdas["LN_con_dato"].cast(pl.Float64)
    nacional = float((celdas["esc"] * w).sum() / w.sum())
    resumen = pl.DataFrame({"pct_LN_2021_sin_dato": [cobertura], "grado_promedio_nacional_LN": [nacional],
                            "eta2_tipo_seccion": [esc.varianza_explicada(celdas, "TIPOSEC")]})
    _csv(resumen, TABLAS / "escolaridad_resumen.csv")
    return {"resumen": resumen, "union": union, "pct_sin_dato": cobertura, "celdas": celdas, "por_perfil": perfil, "grado_nacional": nacional}


EXPERIMENTOS = TABLAS / "experimentos"
# Repeticiones de estabilidad por variante: un consenso tarda unos 40 s y K-Prototypes unos 2 s por ajuste.
REPETICIONES = {"consenso": 3, "kproto": 5}


def paso_experimentos(variantes=None, repeticiones: int = 10) -> dict:
    """Variantes de segmentación, métricas comunes, compuerta D4, descripción y gráficas (spec 004). Tarda unos 8 minutos."""
    EXPERIMENTOS.mkdir(parents=True, exist_ok=True)
    ancha = pl.read_parquet(PROCESADOS / "celdas_ancha.parquet")
    largo = pl.read_parquet(PROCESADOS / "celdas_largo.parquet")
    principal = pl.read_parquet(PROCESADOS / "celdas_perfil.parquet")
    clave = ind.CLAVE_CELDA
    assert ancha.select(clave).equals(principal.select(clave)), "la tabla ancha y la principal deben tener las mismas celdas en el mismo orden"
    mixta = exp.matriz_mixta(ancha)
    peso, nivel = mixta["peso"], mixta["num"][:, 0]
    Z4 = seg.estandarizar(mixta["num"])
    ajustes = exp.ajustadores(ancha)
    variantes = variantes or list(ajustes)

    filas, etiquetas = [], {}
    for v in variantes:
        ks = [5] if v == "consenso" else range(4, 7)
        seleccion, particiones = exp.evaluar_variante(ajustes[v], Z4, peso, SEMILLA, ks, REPETICIONES.get(v, repeticiones))
        _csv(seleccion, EXPERIMENTOS / f"seleccion_k_{v}.csv")
        k = seg.elegir_k(seleccion)
        etiquetas[v] = seg.numerar_por_nivel(particiones[k], nivel, peso)
        fila = seleccion.filter(pl.col("k") == k).row(0, named=True)
        filas.append({"variante": v, **fila,
                      "ARI_vs_principal": adjusted_rand_score(principal["perfil"].to_numpy(), etiquetas[v])})
    tabla = exp.compuerta(pl.DataFrame(filas))
    _csv(tabla, EXPERIMENTOS / "metricas_variantes.csv")

    salida = {"metricas": tabla, "etiquetas": etiquetas, "descripcion": {}}
    for v, etq in etiquetas.items():
        salida["descripcion"][v] = _describir_variante(v, etq, ancha, largo, Z4, peso)

    if "consenso" in etiquetas:
        pac = exp.consenso(Z4, 5, peso, SEMILLA)["PAC"]
        salida["PAC"] = pac
        _csv(pl.DataFrame({"k": [5], "particiones": [300], "PAC": [pac]}), EXPERIMENTOS / "consenso_pac.csv")
    if "gmm" in etiquetas:
        salida["gmm"] = _probabilidades_gmm(etiquetas["gmm"], ancha, Z4, peso)
    if "gower" in etiquetas:
        salida["gower_gamma"] = _sensibilidad_gower(etiquetas["gower"], mixta)
    return salida


def _describir_variante(v: str, etq, ancha, largo, Z4, peso) -> dict:
    """Centroides, composición, tasa absoluta y nombre sugerido de cada perfil de una variante (RF-06 a RF-08)."""
    clave = ind.CLAVE_CELDA
    asig = ancha.select(*clave, "LN_medio", f"LN_{ULTIMA}").with_columns(pl.Series("perfil", etq, dtype=pl.Int8))
    centroides = exp.centroides_z(Z4, etq, peso)
    sexo = per.distribucion(asig, "SEXO").rename({"0": "pct_hombres", "1": "pct_mujeres"})
    tipo = per.distribucion(asig, "TIPOSEC")
    edad = per.distribucion_edad(asig)
    mediana = per.grupo_edad_mediano(asig)
    tasa = per.participacion_por_perfil(largo.join(asig.select(*clave, "perfil"), on=clave))
    nombres = {}
    for fila in centroides.iter_rows(named=True):
        p = fila["perfil"]
        uno = lambda t: {c: x for c, x in t.filter(pl.col("perfil") == p).row(0, named=True).items() if c != "perfil"}
        nombres[p] = contenido.sugerir_nombre(fila, uno(edad), uno(tipo))
    lectura = centroides.with_columns(
        pl.Series("nombre_sugerido", [nombres[p] for p in centroides["perfil"]]),
        pl.Series("lectura", [exp.lectura_centroide(f) for f in centroides.iter_rows(named=True)]),
        pl.Series("pct_LN_2024", [float(100 * asig.filter(pl.col("perfil") == p)[f"LN_{ULTIMA}"].sum() / asig[f"LN_{ULTIMA}"].sum())
                                  for p in centroides["perfil"]]))
    composicion = (lectura.join(sexo, on="perfil").join(tipo, on="perfil").join(mediana, on="perfil")
                   .join(tasa.rename({c: f"tasa_{c}" for c in tasa.columns if c != "perfil"}), on="perfil"))
    _csv(composicion, EXPERIMENTOS / f"perfiles_{v}.csv")
    _csv(edad, EXPERIMENTOS / f"perfiles_edad_{v}.csv")
    figuras.radar_centroides(centroides, ESTADISTICAS / f"experimentos_radar_{v}.png", nombres)
    figuras.mapa_centroides(centroides, ESTADISTICAS / f"experimentos_centroides_{v}.png", nombres)
    return {"perfiles": composicion, "edad": edad, "nombres": nombres}


def _probabilidades_gmm(etq, ancha, Z4, peso) -> dict:
    """Probabilidad de pertenencia por celda y celdas en transición (probabilidad máxima < 0.6) por perfil (RF-05)."""
    k = int(etq.max())
    pr = exp.probabilidades(exp.mezcla(Z4, k, peso, SEMILLA), Z4, peso, etq)
    celdas = ancha.select(*ind.CLAVE_CELDA, "LN_medio").with_columns(
        pl.Series("perfil", etq, dtype=pl.Int8),
        *[pl.Series(f"prob_{j + 1}", pr["prob"][:, j]) for j in range(k)],
        pl.Series("prob_max", pr["pmax"]), pl.Series("entropia", pr["entropia"]))
    _csv(celdas, EXPERIMENTOS / "gmm_probabilidades.csv")
    por_perfil = (celdas.group_by("perfil")
                  .agg(((pl.col("prob_max") * pl.col("LN_medio")).sum() / pl.col("LN_medio").sum()).alias("prob_max_media"),
                       (100 * pl.col("LN_medio").filter(pl.col("prob_max") < 0.6).sum() / pl.col("LN_medio").sum())
                       .alias("pct_LN_transicion"))
                  .sort("perfil"))
    total = pl.DataFrame({"perfil": [0], "prob_max_media": [float(np.average(pr["pmax"], weights=peso))],
                          "pct_LN_transicion": [pr["pct_LN_transicion"]]}).cast(por_perfil.schema)
    resumen = pl.concat([por_perfil, total])
    _csv(resumen, EXPERIMENTOS / "gmm_transicion.csv")
    return {"celdas": celdas, "resumen": resumen}


def _sensibilidad_gower(etq, mixta) -> pl.DataFrame:
    """ARI de k-medoides sobre Gower con peso categórico 0.5 y 2 frente a peso 1 (RF-09, D5)."""
    k = int(etq.max())
    filas = []
    for gamma in (0.5, 1.0, 2.0):
        D = exp.gower(mixta["num"], mixta["ordinal"], mixta["cat"], gamma)
        otra = exp.k_medoides(D, k, mixta["peso"], SEMILLA)[0]
        filas.append({"peso_categorico": gamma, "k": k, "ARI_vs_peso_1": adjusted_rand_score(etq, otra)})
    tabla = pl.DataFrame(filas)
    _csv(tabla, EXPERIMENTOS / "gower_sensibilidad.csv")
    return tabla


def paso_arquetipos(repeticiones: int = 10) -> dict:
    """Arquetipos ponderados como lectura complementaria de los perfiles (spec 004, RF-10, RF-11, D8 a D11). Tarda unos 5 minutos."""
    EXPERIMENTOS.mkdir(parents=True, exist_ok=True)
    ancha = pl.read_parquet(PROCESADOS / "celdas_ancha.parquet")
    principal = pl.read_parquet(PROCESADOS / "celdas_perfil.parquet")
    clave = ind.CLAVE_CELDA
    assert ancha.select(clave).equals(principal.select(clave)), "la tabla ancha y la principal deben tener las mismas celdas en el mismo orden"
    rasgos = seg.matriz_rasgos(ancha, con_volatilidad=True)
    Z4 = seg.estandarizar(rasgos)
    peso = ancha["LN_medio"].to_numpy().astype(float)
    ln = ancha[f"LN_{ULTIMA}"].to_numpy().astype(float)

    candidatas = peso >= exp.MINIMO_LN_ANCLA
    seleccion, k, ajustes = exp.seleccion_arquetipos(Z4, peso, SEMILLA, candidatas)
    _csv(seleccion, EXPERIMENTOS / "arquetipos_seleccion.csv")
    r = ajustes[k]
    A, B = r["A"], r["B"]
    estabilidad = exp.estabilidad_arquetipos(Z4, peso, r["Z"], SEMILLA, candidatas, repeticiones)
    _csv(estabilidad, EXPERIMENTOS / "arquetipos_estabilidad.csv")
    columnas = [f"arq_{j + 1}" for j in range(k)]

    # Demografía de cada arquetipo: cada celda aporta su lista nominal multiplicada por su peso en ese arquetipo.
    base = ancha.select(*clave, "LN_medio", f"LN_{ULTIMA}")
    repartida = pl.concat([base.with_columns(pl.lit(j + 1, dtype=pl.Int8).alias("perfil"),
                                             (pl.col(f"LN_{ULTIMA}") * A[:, j]).alias(f"LN_{ULTIMA}")) for j in range(k)])
    sexo = per.distribucion(repartida, "SEXO").rename({"0": "pct_hombres", "1": "pct_mujeres"})
    tipo = per.distribucion(repartida, "TIPOSEC")
    edad = per.distribucion_edad(repartida)
    mediana = per.grupo_edad_mediano(repartida)
    _csv(edad, EXPERIMENTOS / "arquetipos_edad.csv")

    celdas = ancha.select(clave).to_dicts()
    def ancla(j: int) -> str:
        top = np.argsort(-B[j], kind="stable")[:3]
        return "; ".join(f"{contenido.NOMBRES_ENTIDAD[celdas[i]['EDOCVE']]} {celdas[i]['TIPOSEC']} "
                         f"{'mujeres' if celdas[i]['SEXO'] == 1 else 'hombres'} {celdas[i]['grupo_edad']} ({B[j, i]:.2f})"
                         for i in top if B[j, i] > 0.01)

    zs = {j + 1: dict(zip(exp.RASGOS_BASE, r["Z"][j])) for j in range(k)}
    nombres = contenido.nombrar_polos(zs)
    filas = []
    for j in range(k):
        z = zs[j + 1]
        uno = lambda t: {c: x for c, x in t.filter(pl.col("perfil") == j + 1).row(0, named=True).items() if c != "perfil"}
        filas.append({"arquetipo": j + 1, "nombre": nombres[j + 1], **{f"{n}_z": v for n, v in z.items()},
                      **dict(zip(exp.RASGOS_BASE, B[j] @ rasgos)),
                      "nombre_sugerido": contenido.sugerir_nombre(z, uno(edad), uno(tipo)),
                      "lectura": exp.lectura_centroide(z), "pct_LN_2024": float(100 * (ln @ A[:, j]) / ln.sum()),
                      "celdas_ancla": ancla(j)})
    tabla = (pl.DataFrame(filas).join(sexo.rename({"perfil": "arquetipo"}), on="arquetipo")
             .join(tipo.rename({"perfil": "arquetipo"}), on="arquetipo").join(mediana.rename({"perfil": "arquetipo"}), on="arquetipo"))
    _csv(tabla, EXPERIMENTOS / "arquetipos.csv")

    mezcla_celdas = base.with_columns(pl.Series("perfil", principal["perfil"]), *[pl.Series(c, A[:, j]) for j, c in enumerate(columnas)],
                                      pl.Series("peso_max", A.max(axis=1)))
    _csv(mezcla_celdas, EXPERIMENTOS / "arquetipos_mezcla_celdas.csv")
    mezcla_perfiles = exp.mezcla_por_grupo(A, principal["perfil"].to_numpy(), ln)
    _csv(mezcla_perfiles.rename({"grupo": "perfil"}), EXPERIMENTOS / "arquetipos_mezcla_perfiles.csv")

    secciones, sin_dato = per.mezcla_secciones(PROCESADOS / f"ccpc_{ULTIMA}.parquet", mezcla_celdas, columnas)
    sumas = secciones.select(pl.sum_horizontal(columnas).alias("s"))["s"]
    assert abs(sumas.min() - 1) < 1e-6 and abs(sumas.max() - 1) < 1e-6, "la mezcla de cada sección debe sumar 1"
    secciones.write_parquet(PROCESADOS / f"arquetipos_mezcla_secciones_{ULTIMA}.parquet")
    # 4 decimales en lugar de 10 cifras: son 70 mil secciones y así la tabla pesa la mitad.
    secciones.with_columns(pl.col(columnas).round(4)).write_csv(EXPERIMENTOS / f"arquetipos_mezcla_secciones_{ULTIMA}.csv")

    cerca = A.max(axis=1) >= 0.6
    resumen = pl.DataFrame({
        "k": [k], "varianza_explicada": [r["varianza_explicada"]], "minimo_LN_ancla": [exp.MINIMO_LN_ANCLA],
        "celdas_candidatas_ancla": [int(candidatas.sum())],
        "pct_LN_cerca_de_un_polo": [float(100 * ln[cerca].sum() / ln.sum())],
        "distancia_z_media_submuestras": [float(estabilidad["distancia_z"].mean())],
        "distancia_z_max_submuestras": [float(estabilidad["distancia_z"].max())],
        "secciones": [secciones.height],
        "secciones_con_arquetipo_mayoritario": [int((secciones.select(pl.max_horizontal(columnas)).to_series() >= 0.5).sum())],
        "LN_sin_dato_secciones": [sin_dato]})
    _csv(resumen, EXPERIMENTOS / "arquetipos_resumen.csv")

    centroides = pl.DataFrame({"perfil": list(range(1, k + 1)), **{n: r["Z"][:, i] for i, n in enumerate(exp.RASGOS_BASE)}})
    figuras.radar_centroides(centroides, ESTADISTICAS / "arquetipos_radar.png", nombres,
                             "Arquetipos en z-score (línea punteada: promedio de las celdas)")
    figuras.mezcla_por_perfil(mezcla_perfiles, ESTADISTICAS / "arquetipos_mezcla_perfiles.png", contenido.NOMBRES, nombres)
    return {"seleccion": seleccion, "k": k, "arquetipos": tabla, "estabilidad": estabilidad, "mezcla_perfiles": mezcla_perfiles,
            "secciones": secciones, "resumen": resumen, "nombres": nombres}
