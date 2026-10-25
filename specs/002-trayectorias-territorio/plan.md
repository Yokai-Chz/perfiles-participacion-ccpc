# Plan 002 · Trayectorias en el tiempo y análisis por distrito

**Estado:** aprobado (2026-10-25). Spec: `spec.md` de esta carpeta.

## Corridas
`analisis.CORRIDAS` define cada corrida con su referencia de participación relativa, su unidad territorial, su filtro de `NS` y sus rasgos. Cada una escribe en su propia carpeta de `entrega/tablas/`.

| Corrida | Referencia | Territorio | Excluye NS alto | Rasgos | Carpeta |
|---|---|---|---|---|---|
| `entidad` (principal) | entidad | EDOCVE | no | 3 | `tablas/` |
| `nacional` (001, D16) | nacional | EDOCVE | no | 3 | `sensibilidad_nacional/` |
| `ns` (RF-02) | entidad | EDOCVE | sí | 3 | `sensibilidad_ns/` |
| `volatilidad` (D2b) | entidad | EDOCVE | no | 4 | `sensibilidad_volatilidad/` |
| `region` (RF-13) | circunscripción | REGION | no | 3 | `sensibilidad_region/` |

La comparación con la principal se mide con el ARI sobre las celdas de entidad. En la corrida `region`, cada celda de entidad recibe el perfil de la celda de región que la contiene. Todo queda en `sensibilidad_corridas.csv`.

## Módulos
| Requisito | Dónde | Qué |
|---|---|---|
| RF-01 | `calidad.secciones_ns_alto`, `calidad.distribucion_ns` | Secciones marcadas e histograma de `pct_NS` por elección |
| RF-02, RF-13 | `analisis.paso_*` con `corrida`; `indicadores` con `territorio` | Filtro de secciones, celdas por región, referencia por región |
| RF-03 | `segmentacion.volatilidad`, `matriz_rasgos(..., volatilidad=)` | Desviación estándar de `rel` entre elecciones |
| RF-04, RF-05 | `segmentacion.pca`, `segmentacion.comparar_metodos` | PCA, Ward, GMM con BIC y ARI frente a k-means |
| RF-06 a RF-08, RF-15 | `cohortes.py` | Cohortes por año y quinquenio, curva por edad, primer voto, cohortes por perfil |
| RF-09 a RF-12 | `territorio.py` | Equivalencia de sección a distrito, trayectoria, composición y conservación |
| RF-16 | `estadisticas.py` | Figuras en `entrega/estadisticas/`; cada una lee una tabla |
| RNF-02 | `analisis._csv` y los `sort` en `perfiles` | Flotantes redondeados a 10 decimales y orden fijo de filas y columnas |

## Riesgos
- Ward y el método de mezcla no aceptan pesos: se declara en la tabla y en el texto.
- La corrida `region` usa la circunscripción de 2023 para todos los años; no es la que estaba vigente en 2009 a 2021.
- El documento puede pasar de 12 páginas: el detalle va al repositorio (D6).
