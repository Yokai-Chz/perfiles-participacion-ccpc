# Perfiles ciudadanos de participación (Reto 1, eje 1)

Análisis de los Conteos Censales de Participación Ciudadana (CCPC, 2009 a 2024) para la convocatoria «Hackea la participación». La spec está en `specs/001-perfiles-ciudadanos/`.

## Qué datos se necesitan
Los 192 CSV originales (6 elecciones × 32 entidades) en `drive-download-20261025T011328Z-1-001/`. Nunca se modifican. No se incluyen en el repositorio por su tamaño (unos 3.5 GB).

## Cómo reproducir
Desde la raíz del proyecto, con Python 3.10 o superior:

```powershell
python -m venv src/.venv
src/.venv/Scripts/python.exe -m pip install -r src/requirements.txt
cd src
../src/.venv/Scripts/python.exe -m nbconvert --to notebook --execute --inplace reto1_perfiles_participacion.ipynb
```

Pruebas: `src/.venv/Scripts/python.exe -m pytest src/tests` desde la raíz.

## Qué hace cada pieza
| Módulo | Responsabilidad |
|---|---|
| `src/ingesta.py` | Lee los CSV, valida el esquema y escribe un Parquet por elección. |
| `src/calidad.py` | Integridad (`LN = SV + NV + NS`, duplicados) y tabla de calidad. |
| `src/indicadores.py` | Grupos de edad, tasa de participación, participación relativa, celdas. |
| `src/segmentacion.py` | Rasgos, k-means ponderado, selección de k y estabilidad. |
| `src/perfiles.py` | Caracterización de perfiles y composición de cada sección. |
| `src/contenido.py` | Nombres, narrativa y estrategias de los perfiles (borrador); las cifras se leen de las tablas. |
| `src/figuras.py`, `src/documento.py`, `src/presentacion.py` | Gráficas y fichas PNG, documento PDF y presentación PPTX. |
| `src/verificacion.py` | Comprueba páginas, fuente, diapositivas, resolución de fichas y rayas largas. |
| `src/analisis.py` | Encadena indicadores, segmentación y perfiles; se repite con la referencia por entidad (sensibilidad D16). |

El notebook único `src/reto1_perfiles_participacion.ipynb` explica cada sección y solo llama a estos módulos. Las tablas que respaldan cada cifra publicada quedan en `entrega/tablas/`.

## Limitaciones declaradas
Sin escolaridad en la fuente; los datos usan `SEXO`, no género; las secciones cambian de límites entre elecciones; el CCPC excluye casillas especiales y residentes en el extranjero. La participación nacional aún no se contrasta con la plataforma CCPC (RF-15).
