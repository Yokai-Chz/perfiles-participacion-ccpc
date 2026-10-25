# Plan 003 · Escolaridad del entorno en la segmentación

**Estado:** aprobado (2026-10-25). Spec: `spec.md` de esta carpeta.

## Datos
- `datasets/eceg_2020/`: 32 tablas por sección de la ECEG 2020, una por entidad, sin modificar (fuera de git, como `datasets/`).
- `escolaridad.leer_eceg` las lee (CSV con Polars o XLSX con `zipfile` de la biblioteca estándar) y deja una tabla con entidad, sección, grado promedio por sexo y conteos de educación posbásica por sexo. El formato se fija al ver los archivos descargados.

## Cálculo (`src/escolaridad.py`)
| Requisito | Función | Qué hace |
|---|---|---|
| RF-02 | `unir_secciones` | Une la ECEG con la lista nominal 2021 por (EDOCVE, SECCION) y reporta lo que no une, de cada lado |
| RF-03 | `por_celda` | Promedio del grado de su sexo, ponderado por la LN 2021 de la celda en cada sección |
| RF-04 | `relativa_a_entidad` | Resta el promedio ponderado de la entidad; la suma ponderada da 0 |
| RF-07 | `por_perfil` | Grado promedio y % posbásica del entorno de cada perfil |

## Segmentación
- `segmentacion.matriz_rasgos` recibe columnas extra de la tabla ancha (`extras=[...]`); la principal no pasa ninguna.
- `analisis.CORRIDAS["escolaridad"]`: referencia por entidad, toma la tabla ancha de la principal y le agrega `esc_rel`. Carpeta `entrega/tablas/sensibilidad_escolaridad/`. Entra a `paso_comparar_corridas` y a la figura de robustez.
- Si faltan los datos, `paso_escolaridad` avisa y el notebook sigue sin esa sección.

## Figuras y textos
- `estadisticas.py`: escolaridad del entorno por perfil y cruce entre la principal y la variante.
- Documento técnico: un párrafo en 3.6 con el ARI de la variante y la escolaridad del entorno de cada perfil (D4).
