"""Constantes y rutas del análisis (spec 001)."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "drive-download-20261025T011328Z-1-001"   # CSV originales, solo lectura (RNF-03)
PROCESADOS = RAIZ / "datos_procesados"
TABLAS = RAIZ / "entrega" / "tablas"                      # toda cifra publicada sale de aquí (RNF-06)

ELECCIONES = [2009, 2012, 2015, 2018, 2021, 2024]
PRESIDENCIALES = [2012, 2018, 2024]
INTERMEDIAS = [2009, 2015, 2021]
SEMILLA = 2026

UMBRAL_LN = 100          # D7: lista nominal mínima por celda y elección
RANGO_K = (4, 6)         # RF-08


REFERENCIA_PRINCIPAL = "entidad"   # D16b: cada celda se mide contra su propia entidad


def rutas(referencia: str = REFERENCIA_PRINCIPAL) -> dict:
    """Carpetas de salida según la referencia de participación relativa.

    La corrida principal (D16b, referencia por entidad) escribe en las carpetas base;
    la referencia nacional (D4a original) escribe aparte como análisis de apoyo.
    """
    if referencia == "entidad":
        procesados, tablas, sufijo = PROCESADOS, TABLAS, ""
    elif referencia == "nacional":
        procesados, tablas, sufijo = PROCESADOS, TABLAS / "sensibilidad_nacional", "_nacional"
    else:
        raise ValueError(f"referencia desconocida: {referencia}")
    tablas.mkdir(parents=True, exist_ok=True)
    procesados.mkdir(exist_ok=True)
    return {"procesados": procesados, "tablas": tablas, "sufijo": sufijo}

NOMBRE_EQUIPO = "[NOMBRE DEL EQUIPO]"   # reemplazar antes de entregar
