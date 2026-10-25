import pytest

import verificacion as v

pytestmark = pytest.mark.skipif(not (v.ENTREGA / "documento_tecnico.pdf").exists(),
                                reason="primero genera los entregables (documento.py, presentacion.py, figuras.py)")


def test_el_documento_tiene_entre_8_y_12_paginas_en_liberation_sans():
    r = v.resumen()
    assert 8 <= r["paginas"] <= 12
    assert r["fuentes"] <= {"LiberationSans", "LiberationSans-Bold", "LiberationSans-Italic"}


def test_la_presentacion_tiene_como_maximo_10_diapositivas():
    assert v.resumen()["diapositivas"] <= 10


def test_las_fichas_son_de_alta_resolucion():
    r = v.resumen()
    assert r["fichas"] == 5 and min(r["dpi_fichas"]) >= 300


def test_el_texto_no_usa_rayas_largas():
    assert v.resumen()["rayas_largas"] == 0


def test_los_marcadores_pendientes_siguen_visibles():
    assert "[NOMBRE DEL EQUIPO]" in v.texto_pdf(v.ENTREGA / "documento_tecnico.pdf")
    assert "Borrador para revisión" in v.texto_pptx(v.ENTREGA / "presentacion_ejecutiva.pptx")
