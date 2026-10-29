"""Nombres, narrativa y estrategias de los perfiles. Borrador para revisión del equipo.

Toda cifra de los textos se calcula aquí desde las tablas de `entrega/tablas/` (RNF-06). Los nombres
y las estrategias son propuestas de redacción: la validación institucional corresponde al equipo.
"""
import polars as pl

from configuracion import ELECCIONES, INTERMEDIAS, PRESIDENCIALES, TABLAS

NOMBRES_ENTIDAD = {
    1: "Aguascalientes", 2: "Baja California", 3: "Baja California Sur", 4: "Campeche", 5: "Coahuila",
    6: "Colima", 7: "Chiapas", 8: "Chihuahua", 9: "Ciudad de México", 10: "Durango", 11: "Guanajuato",
    12: "Guerrero", 13: "Hidalgo", 14: "Jalisco", 15: "Estado de México", 16: "Michoacán", 17: "Morelos",
    18: "Nayarit", 19: "Nuevo León", 20: "Oaxaca", 21: "Puebla", 22: "Querétaro", 23: "Quintana Roo",
    24: "San Luis Potosí", 25: "Sinaloa", 26: "Sonora", 27: "Tabasco", 28: "Tamaulipas", 29: "Tlaxcala",
    30: "Veracruz", 31: "Yucatán", 32: "Zacatecas",
}

# Quién + cómo vota, en lenguaje ciudadano e incluyente (cambio del 2026-10-29).
NOMBRES = {1: "Población urbana que vota en presidenciales", 2: "Juventud rural que vota cada vez menos",
           3: "Personas adultas de ciudad con voto constante", 4: "Personas mayores que votan cada vez más",
           5: "Personas adultas y mayores que votan en toda elección"}

# Estrategia por perfil: objetivo, acciones propuestas, indicador de seguimiento, prioridad.
ESTRATEGIAS = {
    1: {"prioridad": "Alta",
        "objetivo": "Reducir la brecha entre elecciones presidenciales e intermedias.",
        "acciones": ["Campaña digital en el año intermedio con mensajes sobre lo que se decide a nivel local.",
                     "Alianzas con instituciones de educación superior y centros de trabajo urbanos.",
                     "Recordatorio de fecha y casilla por sección, enviado antes de la jornada."],
        "indicador": "Participación de las personas de 20 a 34 años en la elección intermedia de 2027 frente a 2021."},
    2: {"prioridad": "Alta",
        "objetivo": "Entender y frenar la caída sostenida de participación.",
        "acciones": ["Trabajo de campo de las Juntas Locales para identificar causas antes de diseñar la campaña.",
                     "Información de casilla y fecha en comunidades, con autoridades locales y radio comunitaria.",
                     "Prueba piloto en las entidades donde el perfil pesa más y evaluación posterior."],
        "indicador": "Participación del perfil en 2027 y 2030 frente a 2024."},
    3: {"prioridad": "Media",
        "objetivo": "Conservar la participación y convertirla en un recurso cívico.",
        "acciones": ["Invitar a ser funcionarias y funcionarios de casilla y a la observación electoral.",
                     "Mensajes de corresponsabilidad que lleguen a sus familias jóvenes (perfil 1).",
                     "Medir si la invitación aumenta la aceptación en secciones donde el perfil pesa más."],
        "indicador": "Aceptación de la invitación como funcionaria o funcionario de casilla."},
    4: {"prioridad": "Media",
        "objetivo": "Sostener el aumento de participación facilitando el acceso.",
        "acciones": ["Revisar la accesibilidad de las casillas en las secciones con más personas del perfil.",
                     "Información impresa y presencial, porque el canal digital llega menos a este grupo.",
                     "Reconocimiento público de la participación de las personas mayores."],
        "indicador": "Participación del perfil en 2027 frente a 2021 y casillas con acceso revisado."},
    5: {"prioridad": "Mantener",
        "objetivo": "Mantener la participación más alta y apoyarse en sus redes comunitarias.",
        "acciones": ["Reconocer a las comunidades con alta participación como promotoras cívicas.",
                     "Apoyo logístico de rutina; los recursos adicionales se destinan a los perfiles 1 y 2.",
                     "Vigilar que la participación no baje en las próximas elecciones."],
        "indicador": "Participación del perfil en 2027 frente a 2021."},
}


def _t(nombre):
    return pl.read_csv(TABLAS / nombre)


def _pct(x):
    return f"{x:.0f} %"


def metricas() -> dict[int, dict]:
    """Cifras de cada perfil, leídas de las tablas generadas por el análisis."""
    peso, part = _t("perfiles_peso_rasgos.csv"), _t("perfiles_participacion.csv")
    sexo, tipo = _t("perfiles_sexo.csv"), _t("perfiles_tipo_seccion.csv")
    edad, mediana = _t("perfiles_edad.csv"), _t("perfiles_edad_mediana.csv")
    top, cat = _t("perfiles_top_entidades.csv"), _t("entidades_catalogo.csv")
    jovenes = ["18-19", "20-24", "25-29", "30-34"]
    mayores = ["60-64", "65-69", "70-74", "75-79", "80-89", "90+"]
    salida = {}
    for p in peso["perfil"]:
        f = lambda t: t.filter(pl.col("perfil") == p).row(0, named=True)
        e, pa, ti = f(edad), f(part), f(tipo)
        anio = {a: pa[str(a)] for a in ELECCIONES}
        salida[p] = {
            "nombre": NOMBRES[p], "pct_lista": f(peso)["pct_lista_nominal_2024"], "personas_2024": f(peso)["LN_2024"],
            "mediana_edad": f(mediana)["grupo_edad_mediano"],
            "pct_18_34": sum(e[c] for c in jovenes), "pct_60_mas": sum(e[c] for c in mayores),
            "pct_mujeres": f(sexo)["pct_mujeres"], "pct_hombres": f(sexo)["pct_hombres"],
            "pct_urbana": ti["U"], "pct_mixta": ti["M"], "pct_rural": ti["R"],
            "part": anio,
            "part_pres": sum(anio[a] for a in PRESIDENCIALES) / len(PRESIDENCIALES),
            "part_inter": sum(anio[a] for a in INTERMEDIAS) / len(INTERMEDIAS),
            "cambio_pres": 100 * (anio[2024] - anio[2012]), "cambio_inter": 100 * (anio[2021] - anio[2009]),
            "top_entidades": [NOMBRES_ENTIDAD[c] for c in top.filter(pl.col("perfil") == p)["EDOCVE"].to_list()[:3]],
        }
        salida[p]["brecha_pp"] = 100 * (salida[p]["part_pres"] - salida[p]["part_inter"])
    assert set(cat["EDOCVE"]) == set(NOMBRES_ENTIDAD), "el catálogo de entidades no coincide con los nombres"
    return salida


def narrativa(p: int, m: dict) -> str:
    """Descripción de un perfil en lenguaje llano, con las cifras de `m`."""
    x = m[p]
    sexo = (f"{_pct(x['pct_mujeres'])} son mujeres" if x["pct_mujeres"] >= 50 else f"{_pct(x['pct_hombres'])} son hombres")
    territorio = (f"{_pct(x['pct_urbana'])} vive en secciones urbanas" if x["pct_urbana"] >= 50
                  else f"{_pct(x['pct_rural'] + x['pct_mixta'])} vive en secciones rurales o mixtas")
    edad = (f"{_pct(x['pct_18_34'])} tiene entre 18 y 34 años" if x["pct_18_34"] >= 50
            else f"{_pct(x['pct_60_mas'])} tiene 60 años o más" if x["pct_60_mas"] >= 40
            else f"la edad mediana está en el tramo de {x['mediana_edad']} años")
    forma = {
        1: f"Participa mucho más en las elecciones presidenciales ({_pct(100 * x['part_pres'])} en promedio) que en las intermedias ({_pct(100 * x['part_inter'])}): una brecha de {x['brecha_pp']:.0f} puntos.",
        2: f"Su participación cayó de {_pct(100 * x['part'][2012])} en 2012 a {_pct(100 * x['part'][2024])} en 2024, la mayor baja entre los perfiles.",
        3: f"Participa de forma estable: {_pct(100 * x['part_inter'])} en intermedias y {_pct(100 * x['part_pres'])} en presidenciales.",
        4: f"Su participación en elecciones intermedias subió de {_pct(100 * x['part'][2009])} en 2009 a {_pct(100 * x['part'][2021])} en 2021 y en 2024 llegó a {_pct(100 * x['part'][2024])}.",
        5: f"Tiene la participación más alta del conjunto: {_pct(100 * x['part'][2009])} en 2009 y {_pct(100 * x['part'][2024])} en 2024.",
    }[p]
    donde = ", ".join(x["top_entidades"])
    return (f"Representa {_pct(x['pct_lista'])} de la lista nominal de 2024. {edad.capitalize()}; {sexo} y {territorio}. "
            f"{forma} Frente a su peso nacional, destaca en {donde}.")


def distritos_prioritarios(p: int, n: int = 3) -> list[str]:
    """Distritos federales vigentes (marco 2023) con más personas del perfil en la lista nominal 2024."""
    d = (_t("distritos_composicion_2023.csv")
         .with_columns((pl.col("LN") * pl.col(f"pct_perfil_{p}") / 100).alias("personas"))
         .sort("personas", "EDOCVE", "DEF", descending=[True, False, False]).head(n))   # EDOCVE y DEF desempatan
    return [f"{NOMBRES_ENTIDAD[r['EDOCVE']]} {r['DEF']} ({r['personas'] / 1000:.0f} mil, {_pct(r[f'pct_perfil_{p}'])})"
            for r in d.iter_rows(named=True)]



# Spec 004, D7. Frases sin flexión de género para que combinen con cualquier sujeto.
EDAD_JOVEN = ["18-19", "20-24", "25-29", "30-34"]
EDAD_MAYOR = ["60-64", "65-69", "70-74", "75-79", "80-89", "90+"]
FRASE_RASGO = {("nivel", 1): "de alta participación", ("nivel", -1): "de baja participación",
               ("brecha", 1): "de coyuntura presidencial", ("brecha", -1): "con participación sostenida en intermedias",
               ("tendencia", 1): "en ascenso", ("tendencia", -1): "en retirada",
               ("volatilidad", 1): "de participación intermitente", ("volatilidad", -1): "de participación estable"}
TERRITORIO = {"U": ("urbanos", "urbana"), "R": ("del campo", "rural"), "M": ("de secciones mixtas", "de secciones mixtas")}


def sugerir_nombre(centroide: dict, edad: dict, tipo: dict, umbral_pct: float = 60.0, umbral_z: float = 0.5) -> str:
    """Nombre sugerido (borrador para el equipo): sujeto por edad, territorio y uno o dos rasgos del centroide.

    `centroide`: z-score por rasgo. `edad` y `tipo`: porcentaje de la lista nominal por grupo de edad y por U, M, R.
    """
    if sum(edad.get(g, 0.0) for g in EDAD_JOVEN) >= umbral_pct:
        sujeto, plural = "Jóvenes", True
    elif sum(edad.get(g, 0.0) for g in EDAD_MAYOR) >= umbral_pct:
        sujeto, plural = "Mayores", True
    else:
        sujeto, plural = "Adultez", False
    dominante = max(TERRITORIO, key=lambda t: tipo.get(t, 0.0))
    partes = [sujeto]
    if tipo.get(dominante, 0.0) >= umbral_pct:
        partes.append(TERRITORIO[dominante][0 if plural else 1])
    rasgos = sorted((r for r in dict.fromkeys(r for r, _ in FRASE_RASGO) if r in centroide), key=lambda r: -abs(centroide[r]))
    elegidos = rasgos[:1] + [r for r in rasgos[1:2] if abs(centroide[r]) >= umbral_z]
    elegidos.sort(key=lambda r: r != "nivel")   # «de baja participación y en retirada» se lee mejor con el nivel primero
    frases = [FRASE_RASGO[(r, 1 if centroide[r] > 0 else -1)] for r in elegidos]
    return " ".join(partes) + " " + " y ".join(frases)



# Polos de los arquetipos (spec 004): frases sobre el voto, no sobre personas. Rasgo y signo que identifican a cada uno.
FIRMA_POLOS = {"Voto presidencial": ("brecha", 1), "Voto parejo que baja": ("tendencia", -1),
               "Voto que crece": ("tendencia", 1), "Voto firme": ("volatilidad", -1)}


def nombrar_polos(z: dict[int, dict]) -> dict[int, str]:
    """Nombre de cada arquetipo por su firma (el extremo de un rasgo) y no por su número, para no depender del orden."""
    if len(z) != len(FIRMA_POLOS):
        raise ValueError(f"se esperaban {len(FIRMA_POLOS)} arquetipos, llegaron {len(z)}")
    nombres = {}
    for nombre, (rasgo, signo) in FIRMA_POLOS.items():
        j = max(z, key=lambda i: signo * z[i][rasgo])
        if j in nombres:
            raise ValueError(f"«{nombre}» y «{nombres[j]}» caen en el mismo arquetipo ({j}): revisar las firmas")
        nombres[j] = nombre
    return nombres
