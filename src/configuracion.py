"""Constantes y rutas del análisis (specs 001 y 002)."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "datasets"   # CSV originales, solo lectura (RNF-03)
ECEG = BRUTOS / "eceg_2020"   # ECEG 2020 de INEGI e INE por sección, una tabla por entidad (spec 003)
PROCESADOS = RAIZ / "datos_procesados"
TABLAS = RAIZ / "entrega" / "tablas"                      # toda cifra publicada sale de aquí (RNF-06)

ELECCIONES = [2009, 2012, 2015, 2018, 2021, 2024]
PRESIDENCIALES = [2012, 2018, 2024]
INTERMEDIAS = [2009, 2015, 2021]
SEMILLA = 2026

UMBRAL_LN = 100          # D7: lista nominal mínima por celda y elección
RANGO_K = (4, 6)         # RF-08


UMBRAL_NS = 0.25         # spec 002, D1: sección marcada si NS / LN supera este valor en una elección

REFERENCIA_PRINCIPAL = "entidad"   # D16b: cada celda se mide contra su propia entidad

ESTADISTICAS = TABLAS.parent / "estadisticas"   # figuras de apoyo (spec 002, RF-16)

# Circunscripciones plurinominales del acuerdo INE/CG130/2023, usadas como región en todos los años (spec 002, D3).
CIRCUNSCRIPCION = {
    2: 1, 3: 1, 8: 1, 10: 1, 14: 1, 18: 1, 25: 1, 26: 1,
    1: 2, 5: 2, 11: 2, 19: 2, 24: 2, 28: 2, 32: 2,
    4: 3, 7: 3, 20: 3, 23: 3, 27: 3, 30: 3, 31: 3,
    9: 4, 12: 4, 13: 4, 17: 4, 21: 4, 29: 4,
    6: 5, 15: 5, 16: 5, 22: 5,
}
SEDE_CIRCUNSCRIPCION = {1: "Guadalajara", 2: "Monterrey", 3: "Xalapa", 4: "Ciudad de México", 5: "Toluca"}

# Carpeta y sufijo de cada corrida. La principal escribe en las carpetas base.
_CARPETAS = {"entidad": ("", ""), "nacional": ("sensibilidad_nacional", "_nacional"), "ns": ("sensibilidad_ns", "_ns"),
             "volatilidad": ("sensibilidad_volatilidad", "_volatilidad"), "region": ("sensibilidad_region", "_region"),
             "escolaridad": ("sensibilidad_escolaridad", "_escolaridad")}


def rutas(corrida: str = REFERENCIA_PRINCIPAL) -> dict:
    """Carpetas de salida de una corrida (ver `analisis.CORRIDAS`)."""
    if corrida not in _CARPETAS:
        raise ValueError(f"corrida desconocida: {corrida}")
    carpeta, sufijo = _CARPETAS[corrida]
    tablas = TABLAS / carpeta if carpeta else TABLAS
    tablas.mkdir(parents=True, exist_ok=True)
    PROCESADOS.mkdir(exist_ok=True)
    return {"procesados": PROCESADOS, "tablas": tablas, "sufijo": sufijo}


NOMBRE_EQUIPO = "[NOMBRE DEL EQUIPO]"   # reemplazar antes de entregar

# Fuente de los entregables: Liberation Sans, del sistema Fedora, con las mismas medidas que Arial.
FUENTE = "Liberation Sans"
_DIR_FUENTE = Path("/usr/share/fonts/liberation-sans-fonts")
ARCHIVOS_FUENTE = {"normal": _DIR_FUENTE / "LiberationSans-Regular.ttf",
                   "negrita": _DIR_FUENTE / "LiberationSans-Bold.ttf",
                   "cursiva": _DIR_FUENTE / "LiberationSans-Italic.ttf"}
