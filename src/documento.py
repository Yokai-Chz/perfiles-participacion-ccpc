"""Documento técnico en PDF (RE-01): Liberation Sans 11 (medidas de Arial), interlineado 1.5, entre 8 y 12 páginas.

El texto es una propuesta de redacción; todas las cifras se leen de las tablas de `entrega/tablas/`.
"""
import polars as pl
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import contenido
from configuracion import ARCHIVOS_FUENTE, ELECCIONES, ESTADISTICAS, NOMBRE_EQUIPO, TABLAS, UMBRAL_NS
from figuras import FIGURAS

pdfmetrics.registerFont(TTFont("Sans", ARCHIVOS_FUENTE["normal"]))
pdfmetrics.registerFont(TTFont("Sans-Bold", ARCHIVOS_FUENTE["negrita"]))
pdfmetrics.registerFont(TTFont("Sans-Italic", ARCHIVOS_FUENTE["cursiva"]))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans-Italic", boldItalic="Sans-Bold")

CUERPO = ParagraphStyle("cuerpo", fontName="Sans", fontSize=11, leading=16.5, alignment=TA_JUSTIFY, spaceAfter=6)
H1 = ParagraphStyle("h1", parent=CUERPO, fontName="Sans-Bold", fontSize=14, leading=21, spaceBefore=10, spaceAfter=4, alignment=0)
H2 = ParagraphStyle("h2", parent=CUERPO, fontName="Sans-Bold", fontSize=11, leading=16.5, spaceBefore=6, spaceAfter=2, alignment=0)
TITULO = ParagraphStyle("titulo", parent=CUERPO, fontName="Sans-Bold", fontSize=20, leading=28, alignment=0, spaceAfter=2)
SUBTITULO = ParagraphStyle("subtitulo", parent=CUERPO, textColor=colors.HexColor("#52514e"), alignment=0, spaceAfter=2)
CELDA = ParagraphStyle("celda", parent=CUERPO, fontSize=10, leading=13, alignment=0, spaceAfter=0)
CELDA_B = ParagraphStyle("celdab", parent=CELDA, fontName="Sans-Bold")
PIE = ParagraphStyle("pie", parent=CUERPO, fontSize=10, leading=15, textColor=colors.HexColor("#52514e"), alignment=0)


def _t(nombre):
    return pl.read_csv(TABLAS / nombre)


def p(texto, estilo=CUERPO):
    return Paragraph(texto, estilo)


def viñetas(items):
    return [Paragraph(f"• {i}", ParagraphStyle("v", parent=CUERPO, leftIndent=14, firstLineIndent=-10, spaceAfter=3)) for i in items]


def tabla(filas, anchos, encabezado=True):
    datos = [[Paragraph(str(c), CELDA_B if (encabezado and i == 0) else CELDA) for c in fila] for i, fila in enumerate(filas)]
    t = Table(datos, colWidths=anchos, repeatRows=1 if encabezado else 0)
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#0b0b0b")),
                           ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#c9c8c2")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def figura(nombre, ancho_cm, pie_texto, carpeta=FIGURAS):
    ruta = carpeta / nombre
    from PIL import Image as PILImage
    w, h = PILImage.open(ruta).size
    return KeepTogether([Image(str(ruta), width=ancho_cm * cm, height=ancho_cm * cm * h / w), p(pie_texto, PIE)])


def n(x):
    return f"{x:,.0f}"


def construir(ruta):
    m = contenido.metricas()
    cal = _t("calidad_nacional.csv")
    tc = pl.read_csv(TABLAS / "tabla_calidad.csv")
    res = _t("resumen_indicadores.csv").row(0, named=True)
    comp = _t("sensibilidad_comparacion.csv")
    sel = _t("seleccion_k.csv")
    principal, apoyo = comp.row(0, named=True), comp.row(1, named=True)
    sm = _t("perfiles_secciones_mayoritarias.csv")
    k5 = sel.filter(pl.col("k") == 5).row(0, named=True)
    filas_total = tc["filas"].sum()
    ln24 = cal.filter(pl.col("AELEC") == 2024)["LN"][0]
    ns_min, ns_max = cal["pct_NS"].min(), cal["pct_NS"].max()
    p90 = 100 * tc["LN_90_o_mas"].sum() / tc["LN"].sum()
    pct = lambda i: m[i]["pct_lista"]
    # Spec 002: NS, robustez, primer voto y distritos.
    rns = _t("resumen_ns_alto.csv")
    corr = {r["corrida"]: r for r in _t("sensibilidad_corridas.csv").iter_rows(named=True)}
    met = {r["metodo"]: r["ARI_vs_kmeans"] for r in _t("robustez_metodos.csv").iter_rows(named=True)}
    pv = _t("efecto_primer_voto.csv").filter(pl.col("edad_primera") == 18).drop_nulls("rel_siguiente")
    d23 = _t("distritos_composicion_2023.csv")
    pcts23 = [c for c in d23.columns if c.startswith("pct_perfil_")]
    mezcla = d23.filter(pl.max_horizontal(pcts23) < 50).height
    dom = {i: d23.filter(pl.col("perfil_dominante") == i).height for i in m}
    cons = _t("distritos_conservacion.csv").filter(pl.col("AELEC") == 2024).row(0, named=True)

    h = []
    h += [p("Perfiles ciudadanos de participación", TITULO),
          p("Cinco maneras de participar en las elecciones federales, 2009 a 2024", SUBTITULO),
          p(f"Eje 1, Reto 1 · {NOMBRE_EQUIPO} · Borrador para revisión del equipo", SUBTITULO), Spacer(1, 6)]

    h += [p("1. Resumen ejecutivo", H1),
          p(f"La pregunta del reto es qué tipos de ciudadanía existen según su comportamiento de participación. Con los Conteos Censales de Participación "
            f"Ciudadana (CCPC) de seis elecciones federales (2009 a 2024) encontramos <b>cinco perfiles</b> claramente diferenciados. No se definen por el "
            f"estado donde viven sino por la forma en que cada grupo de edad, sexo y tipo de sección participa respecto a su propia entidad, y se "
            f"distinguen por dos rasgos: <i>cuánto</i> participan y <i>cómo cambia</i> su participación entre elecciones presidenciales e intermedias."),
          p(f"Los dos perfiles de mayor prioridad para el INE son los más jóvenes. El perfil 1, <b>{m[1]['nombre']}</b>, reúne {pct(1):.0f} % de la lista nominal "
            f"de 2024 y participa {m[1]['brecha_pp']:.0f} puntos más en las presidenciales que en las intermedias. El perfil 2, <b>{m[2]['nombre']}</b>, pesa "
            f"{pct(2):.0f} % y es el que más cayó en las elecciones presidenciales: de {100 * m[2]['part'][2012]:.0f} % en 2012 a "
            f"{100 * m[2]['part'][2024]:.0f} % en 2024. En el otro extremo, los <b>{m[4]['nombre'].lower()}</b> (perfil 4) son el grupo con mayor aumento: "
            f"su participación en intermedias pasó de {100 * m[4]['part'][2009]:.0f} % a {100 * m[4]['part'][2021]:.0f} % entre 2009 y 2021."),
          p("Para cada perfil proponemos una estrategia distinta de fomento a la participación, con objetivo, acciones e indicador de seguimiento (sección 5). "
            "Los nombres y las estrategias son propuestas para revisión del equipo y de las áreas del INE que las aplicarían."),
          figura("pesos.png", 13.5, "Figura 1. Peso de cada perfil en la lista nominal de 2024. Fuente: CCPC, cálculos propios.")]

    h += [p("2. Datos y calidad", H1),
          p(f"Se usaron los CCPC publicados para las elecciones federales de 2009, 2012, 2015, 2018, 2021 y 2024: 192 archivos (6 elecciones por 32 entidades) con "
            f"{n(filas_total)} filas. Cada fila es una combinación de sección electoral, sexo y edad, con la lista nominal (LN), los votantes (SV), los no votantes "
            f"(NV) y las personas sin dato de voto (NS). Los datos están agregados y no contienen información personal. La lista nominal de 2024 suma {n(ln24)} personas."),
          p("Antes de analizar se verificó que en todas las filas se cumple LN = SV + NV + NS y que no hay claves repetidas por elección, entidad, sección, sexo y edad. "
            "Las filas que no cumplieran se habrían reportado y no descartado. El porcentaje de NS varía mucho entre elecciones "
            f"(de {ns_min:.1f} % a {ns_max:.1f} % de la lista nominal), por lo que la participación se define sin NS: SV / (SV + NV). "
            f"Las edades de 90 años o más representan {p90:.1f} % de la lista y se agrupan en un solo tramo («90+»)."),
          p(f"NS no es abstención: son registros de cuadernillos sin marcas, no disponibles o con páginas faltantes. Por sección, NS se concentra: según la elección, "
            f"entre {rns['secciones_marcadas'].min():,} y {rns['secciones_marcadas'].max():,} secciones tienen más de {100 * UMBRAL_NS:.0f} % de su lista en NS "
            f"(de {rns['pct_LN'].min():.1f} % a {rns['pct_LN'].max():.1f} % de la lista nominal). Se marcan y se repite el análisis sin ellas (sección 3.6)."),
          tabla([["Elección", "Tipo", "Lista nominal", "Participación SV/(SV+NV)", "NS (% de la LN)"]] +
                [[r["AELEC"], "Presidencial" if r["AELEC"] in (2012, 2018, 2024) else "Intermedia", n(r["LN"]),
                  f"{r['part_SV_sobre_SV_NV']:.1f} %", f"{r['pct_NS']:.1f} %"] for r in cal.iter_rows(named=True)],
                [2.2 * cm, 3 * cm, 3.4 * cm, 4.6 * cm, 3.2 * cm]),
          p("Tabla 1. Participación nacional por elección. Fuente: CCPC, cálculos propios.", PIE),
          figura("participacion_nacional.png", 12.5, "Figura 2. La participación es mayor en las elecciones presidenciales. Esa diferencia no debe confundirse con una tendencia, por eso el análisis mide la participación respecto a un grupo de referencia."),
          p("<b>Qué no dicen los datos.</b> La fuente no trae escolaridad. Trae el campo SEXO (hombres y mujeres) y no género, por eso usamos «sexo». La unidad territorial es la "
            "sección de la credencial y las secciones cambian de límites entre elecciones. El CCPC excluye casillas especiales y residentes en el extranjero, "
            "así que sus cifras no coinciden con los cómputos distritales. El contraste de la participación nacional con las cifras de la plataforma CCPC queda pendiente.")]

    h += [p("3. Metodología", H1),
          p("3.1 Unidad de análisis: la celda demográfica", H2),
          p(f"Un perfil ciudadano debe describir personas, no territorios. Por eso la unidad es la <b>celda demográfica</b>: grupo de edad (15 tramos, de 18-19 a 90+) por sexo por "
            f"tipo de sección (urbana, mixta o rural) por entidad. Cada celda tiene su participación en las seis elecciones. Se conservaron {n(res['celdas_conservadas'])} "
            f"celdas. Se excluyeron {n(res['celdas_excluidas'])} por tener menos de 100 personas en alguna elección o no existir en las seis; representan "
            f"{res['pct_ln_excluida']:.3f} % de la lista nominal y se reportan en una tabla aparte."),
          p("3.2 Participación relativa a la propia entidad", H2),
          p("La participación se calcula siempre como cociente de sumas, nunca como promedio de porcentajes. Para que un perfil no se distinga solo por «participar más o menos» "
            "se mide la <b>participación relativa</b>: la tasa de la celda menos la tasa de su entidad en esa elección. Así se descuenta el efecto de las elecciones presidenciales "
            "y también el de cada estado. La suma ponderada de estas diferencias es cero en cada entidad y elección, y el código lo comprueba."),
          p(f"Esta decisión se tomó después de una prueba de sensibilidad. Con la referencia nacional, la entidad explicaba {100 * apoyo['eta2_brecha']:.0f} % de la variación de la brecha "
            f"entre presidenciales e intermedias y {100 * apoyo['eta2_tendencia']:.0f} % de la tendencia, y {apoyo['entidades_con_80pct_en_un_perfil']} de 32 entidades "
            f"quedaban con más de 80 % de su lista en un solo perfil: los perfiles se parecían a etiquetas de estado. Con la referencia por entidad esas cifras bajan a "
            f"{100 * principal['eta2_brecha']:.1f} % y {100 * principal['eta2_tendencia']:.1f} %, y ninguna entidad queda dominada por un perfil. "
            "Una posible explicación es que las elecciones locales concurrentes elevan la participación en unas entidades y no en otras, pero no pudimos verificarlo "
            "porque el calendario local no está en los datos."),
          p("3.3 Rasgos y método de segmentación", H2),
          p("Cada celda se resume con tres rasgos que separan el nivel de la forma en el tiempo: el <b>nivel</b> (participación relativa media en las seis elecciones), la "
            "<b>brecha</b> (media en presidenciales menos media en intermedias) y la <b>tendencia</b> (pendiente de la participación relativa). Las celdas se agrupan con "
            "k-means ponderado por lista nominal y semilla fija, de modo que los mismos datos dan los mismos perfiles. La demografía no entra en el agrupamiento: se usa "
            "después para describir cada perfil."),
          p("3.4 Elección del número de perfiles", H2),
          p(f"Se probaron 4, 5 y 6 perfiles con dos medidas cuantitativas: el <i>silhouette</i> (qué tan separados quedan los grupos; se calcula sin pesos porque la librería no los admite) y la "
            f"estabilidad, medida con el índice de Rand ajustado (ARI) entre corridas con otras semillas y con submuestras de 80 % de las celdas. Se eligió k = 5: tiene el mayor silhouette "
            f"({k5['silhouette_sin_pesos']:.2f}) y es estable (ARI medio de {k5['ARI_semillas_media']:.2f} entre semillas y {k5['ARI_submuestras_media']:.2f} entre submuestras). "
            f"Con 6 perfiles la estabilidad mínima por submuestra baja a {sel.filter(pl.col('k') == 6)['ARI_submuestras_min'][0]:.2f}. El criterio de interpretabilidad queda a "
            "confirmación del equipo: en este borrador los cinco perfiles se describen con claridad y piden acciones distintas."),
          figura("seleccion_k.png", 13, "Figura 3. Selección del número de perfiles. La línea punteada marca el umbral de estabilidad de 0.80."),
          p("3.5 Presencia en el territorio", H2),
          p("Una celda no tiene dimensión de sección, por lo que no se asigna un solo perfil a cada sección. En su lugar se calcula la <b>composición de cada sección</b>: qué proporción de su "
            "lista nominal de 2024 pertenece a cada perfil. La clave territorial es siempre la pareja (entidad, sección), porque el número de sección solo es único dentro de una entidad. "
            "La tabla de composición está en el repositorio y sirve para focalizar acciones por sección."),
          p("3.6 Robustez", H2),
          p(f"Sin las secciones con NS alto, k-means vuelve a elegir {corr['ns']['k']} perfiles y la asignación casi no cambia (ARI de {corr['ns']['ARI_vs_principal']:.2f}). "
            f"Otros algoritmos sobre los mismos rasgos coinciden solo en parte: ARI de {met['Ward (jerárquico)']:.2f} con Ward y de {met['Mezcla gaussiana']:.2f} con una mezcla "
            f"gaussiana, ambos sin pesos. Las celdas no forman grupos muy separados (silhouette de {k5['silhouette_sin_pesos']:.2f}): los perfiles son una partición útil de un continuo "
            "y no tipos naturales. Las figuras de PCA, la comparación entre métodos y las corridas por circunscripción y con volatilidad están en la carpeta <i>entrega/estadisticas</i>.")]

    h += [p("4. Los cinco perfiles", H1),
          p("Los perfiles se describen con cifras agregadas de la lista nominal de 2024. Conviene leerlos con tres precauciones. Primero, describen <i>grupos de edad y sexo en cada elección</i>, no "
            "a personas: atribuir el rasgo de un grupo a cada integrante sería una falacia ecológica, y una franja de edad no sigue a las mismas personas a lo largo del tiempo: quien tenía 20 a 24 años en 2009 tiene 32 a 36 en 2021. Segundo, se definen por su comportamiento y no por el territorio, así que un perfil "
            "mayoritariamente rural puede tener presencia urbana. Tercero, las explicaciones de por qué ocurre cada comportamiento son hipótesis para trabajo de campo, no resultados de este análisis."),
          figura("trayectorias.png", 14.5, "Figura 4. Participación de cada perfil por elección. Fuente: CCPC, cálculos propios."),
          tabla([["Perfil", "% de la lista 2024", "Edad mediana", "Mujeres", "Urbana", "Participación 2024"]] +
                [[f"{i}. {x['nombre']}", f"{x['pct_lista']:.1f}", x["mediana_edad"], f"{x['pct_mujeres']:.0f} %", f"{x['pct_urbana']:.0f} %",
                  f"{100 * x['part'][2024]:.0f} %"] for i, x in m.items()],
                [5.6 * cm, 2.4 * cm, 2.4 * cm, 1.9 * cm, 1.9 * cm, 2.6 * cm]),
          p("Tabla 2. Resumen de los perfiles. Fuente: CCPC, cálculos propios.", PIE),
          figura("edades.png", 13.5, "Figura 5. Distribución por grupo de edad dentro de cada perfil. Los perfiles 1 y 2 concentran a las personas de 18 a 34 años; los perfiles 3, 4 y 5 se reparten entre adultez y vejez."),
          p("<b>Dónde pesa cada perfil.</b> Los perfiles están presentes en todo el país; ninguna entidad queda dominada por uno solo. La tabla 3 muestra las tres entidades donde cada perfil pesa más "
            "frente a su peso nacional y el número de secciones electorales donde reúne la mitad o más de la lista nominal."),
          tabla([["Perfil", "Entidades donde pesa más", "Secciones donde es mayoría"]] +
                [[f"{i}. {x['nombre']}", ", ".join(x["top_entidades"]),
                  f"{n(sm.filter(pl.col('perfil') == i)['secciones_mayoritarias'][0])} de {n(sm['secciones_total'][0])}"] for i, x in m.items()],
                [5.6 * cm, 6.4 * cm, 4.8 * cm]),
          p("Tabla 3. Presencia territorial. Fuente: CCPC, cálculos propios (composición de cada sección con la lista nominal de 2024).", PIE)]
    lecturas = {
        1: "Es el perfil más numeroso y el más sensible al tipo de elección: su participación se desploma cuando no hay elección presidencial. Una hipótesis es que el interés se concentra en la contienda nacional.",
        2: "Es el único perfil con una caída sostenida en las presidenciales. Casi todo su peso está en secciones rurales o mixtas y tres de cada cuatro personas son hombres. Una hipótesis sin verificar es la movilidad laboral, que haría difícil estar en la sección el día de la jornada.",
        3: "Es el núcleo estable de la ciudadanía urbana. No destaca por ningún extremo y por eso mismo es un recurso: participa de forma consistente en todo tipo de elección.",
        4: "Es el grupo que más ha crecido. Sus integrantes son mayoritariamente mujeres de 60 años o más, y su participación en 2024 es de las más altas del conjunto.",
        5: "Es el perfil de participación más alta y constante. Combina edad adulta madura con una fuerte presencia rural; funciona como referencia de lo que se puede lograr en comunidad.",
    }
    for i, x in m.items():
        h += [p(f"Perfil {i}: {x['nombre']}", H2), p(contenido.narrativa(i, m) + " " + lecturas[i])]

    h += [p("Primer voto y cohortes", H2),
          p(f"Con la edad exacta se puede seguir a cada generación entre elecciones como un pseudo-panel (no son las mismas personas). Quienes votan por primera vez a los 18 años "
            f"participan en promedio {100 * pv['rel_primera'].mean():.1f} puntos por encima de su entidad; tres años después, la misma cohorte queda "
            f"{abs(100 * pv['rel_siguiente'].mean()):.1f} puntos por debajo. El entusiasmo del primer voto existe y se pierde pronto, lo que refuerza las estrategias de los perfiles 1 y 2."),
          figura("14_efecto_primer_voto.png", 13, "Figura 6. Participación relativa de cada cohorte en su primera elección y tres años después. Fuente: CCPC, cálculos propios.", ESTADISTICAS),
          p("Perfiles por distrito federal", H2),
          p(f"Para usar los perfiles en campo, la composición de cada sección se suma por distrito federal. En el marco vigente (2023), el perfil 1 es el de mayor peso en {dom[1]} de 300 "
            f"distritos y el 3 en {dom[3]}, pero en {mezcla} distritos ningún perfil llega a la mitad de la lista: casi todo el territorio combina perfiles. Para comparar en el tiempo se usa "
            f"el marco 2021, en el que vienen los datos de 2009 a 2021; las secciones nuevas de 2024 ({cons['pct_sin_distrito']:.1f} % de su lista) no tienen equivalencia y se reportan aparte. "
            "Las tablas por distrito y por circunscripción están en el repositorio.")]

    h += [p("5. Estrategias diferenciadas", H1),
          p("Cada estrategia responde a un rasgo del perfil y propone acciones que el INE y sus Juntas Locales pueden aplicar. La prioridad combina el peso del perfil con la distancia entre su "
            "participación y la del resto. Todas las estrategias incluyen un indicador que se puede medir con los CCPC de la siguiente elección, lo que permite evaluar si funcionaron.")]
    for i in m:
        e = contenido.ESTRATEGIAS[i]
        h.append(KeepTogether([p(f"Perfil {i}: {m[i]['nombre']} (prioridad {e['prioridad'].lower()})", H2),
                               p(f"<b>Objetivo.</b> {e['objetivo']}")] + viñetas(e["acciones"]) + [p(f"<b>Indicador.</b> {e['indicador']}")]))
    h += [p("Para validar el enfoque antes de escalarlo, proponemos una prueba piloto en dos o tres entidades con estrategias de los perfiles 1 y 2, comparada con entidades similares sin la acción. "
            "La composición por sección permite elegir dónde aplicarla y medir el resultado.")]

    h += [p("6. Limitaciones", H1)] + viñetas([
        "No hay escolaridad en la fuente; incorporarla con el Censo de INEGI es una línea futura.",
        "Se usa sexo y no género, porque es lo que registra la fuente.",
        "Los perfiles y las cohortes describen grupos, no personas. En las cohortes el año de nacimiento es aproximado (±1 año) y los efectos de edad, periodo y cohorte no se separan por completo.",
        "Otros algoritmos dan agrupaciones parecidas solo en parte; los perfiles son una partición útil, no tipos naturales.",
        "Las secciones cambian de límites entre elecciones; el análisis no necesita seguir una sección en el tiempo, pero la composición territorial usa los límites de 2024.",
        "El CCPC excluye casillas especiales y residentes en el extranjero. La participación nacional aún no se contrasta con la plataforma CCPC.",
        "Las hipótesis sobre causas (elecciones locales concurrentes, movilidad laboral) no se verificaron con los datos disponibles.",
        "Los nombres y estrategias son una propuesta y requieren validación institucional."])

    h += [p("7. Reproducibilidad", H1),
          p("El análisis completo se repite con el código entregado: el notebook <i>reto1_perfiles_participacion.ipynb</i> explica cada sección y llama a módulos con pruebas automáticas. "
            "Las instrucciones están en el archivo README. Cada cifra de este documento se calcula desde una tabla generada por el código (carpeta <i>entrega/tablas</i>). "
            "Los archivos originales no se modifican y el resultado es el mismo con la misma semilla.")]

    doc = SimpleDocTemplate(str(ruta), pagesize=letter, leftMargin=2.5 * cm, rightMargin=2.5 * cm, topMargin=2.5 * cm, bottomMargin=2.5 * cm,
                            title="Perfiles ciudadanos de participación", author=NOMBRE_EQUIPO)
    doc.build(h, onFirstPage=_pie, onLaterPages=_pie)


def _pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Sans", 9)
    canvas.setFillColor(colors.HexColor("#52514e"))
    canvas.drawRightString(letter[0] - 2.5 * cm, 1.4 * cm, f"{doc.page}")
    canvas.restoreState()


if __name__ == "__main__":
    from configuracion import TABLAS as T
    destino = T.parent / "documento_tecnico.pdf"
    construir(destino)
    from pypdf import PdfReader
    print("páginas:", len(PdfReader(destino).pages))
