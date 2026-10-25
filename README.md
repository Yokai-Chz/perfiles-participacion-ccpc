# Perfiles ciudadanos de participación (Reto 1, eje 1)

Análisis de los Conteos Censales de Participación Ciudadana (CCPC, 2009 a 2024) para la convocatoria «Hackea la participación». Las specs están en `specs/001-perfiles-ciudadanos/` (perfiles) y `specs/002-trayectorias-territorio/` (NS, cohortes, robustez y distritos).

## Qué datos se necesitan
Los 192 CSV originales (6 elecciones × 32 entidades) en `datasets/`, una subcarpeta por elección (`DatosAbiertos_DECEyEC_ConteosCensales2009/` a `...2024/`). Nunca se modifican. No se incluyen en el repositorio por su tamaño (unos 3.5 GB).

Para la escolaridad (spec 003): la descarga nacional de las Estadísticas Censales a Escalas Geoelectorales 2020 del INEGI, descomprimida en `datasets/eceg_2020/` (se usa `conjunto_de_datos/INE_SECCION_2020.csv`). Sin ella, el análisis corre igual y omite la escolaridad.

## Cómo reproducir
Desde la raíz del proyecto, con Python 3.10 a 3.13 (numpy 2.2 no tiene versión para 3.14). Probado con Python 3.12 en Linux:

```bash
python3.12 -m venv src/.venv
src/.venv/bin/python -m pip install -r src/requirements.txt
cd src
.venv/bin/python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 reto1_perfiles_participacion.ipynb
```

Pruebas: `src/.venv/bin/python -m pytest src/tests` desde la raíz.

En Windows, el intérprete del entorno es `src\.venv\Scripts\python.exe` en lugar de `src/.venv/bin/python`.

## Qué hace cada pieza
| Módulo | Responsabilidad |
|---|---|
| `src/ingesta.py` | Lee los CSV, valida el esquema y escribe un Parquet por elección. |
| `src/calidad.py` | Integridad (`LN = SV + NV + NS`, duplicados), tabla de calidad y secciones con NS alto. |
| `src/indicadores.py` | Grupos de edad, tasa de participación, participación relativa, celdas. |
| `src/segmentacion.py` | Rasgos (con volatilidad opcional), k-means ponderado, selección de k, estabilidad, PCA y comparación con Ward y mezcla gaussiana. |
| `src/cohortes.py` | Cohortes de nacimiento como pseudo-panel, curva por edad y efecto del primer voto. |
| `src/escolaridad.py` | Escolaridad del entorno por celda a partir de la ECEG 2020 (Censo por sección y sexo). |
| `src/territorio.py` | Equivalencia de secciones entre marcos 2021 y 2023, trayectoria y composición por distrito federal. |
| `src/perfiles.py` | Caracterización de perfiles y composición de cada sección. |
| `src/contenido.py` | Nombres, narrativa y estrategias de los perfiles (borrador); las cifras se leen de las tablas. |
| `src/figuras.py`, `src/documento.py`, `src/presentacion.py` | Gráficas y fichas PNG, documento PDF y presentación PPTX. |
| `src/estadisticas.py` | Figuras de apoyo en `entrega/estadisticas/`: datos, algoritmos, cohortes y distritos. |
| `src/verificacion.py` | Comprueba páginas, fuente, diapositivas, resolución de fichas y rayas largas. |
| `src/analisis.py` | Encadena los pasos. `CORRIDAS` define la principal y las de apoyo (referencia nacional, sin NS alto, con volatilidad, por circunscripción). |

El notebook único `src/reto1_perfiles_participacion.ipynb` explica cada sección y solo llama a estos módulos. Las tablas que respaldan cada cifra publicada quedan en `entrega/tablas/`.

## Limitaciones declaradas
Sin escolaridad en la fuente; los datos usan `SEXO`, no género; las secciones cambian de límites entre elecciones; el CCPC excluye casillas especiales y residentes en el extranjero. La participación nacional aún no se contrasta con la plataforma CCPC (RF-15). Las cohortes no siguen a las mismas personas y los perfiles describen grupos, no individuos (falacia ecológica). Las secciones nuevas de 2024 no tienen distrito en el marco 2021.
