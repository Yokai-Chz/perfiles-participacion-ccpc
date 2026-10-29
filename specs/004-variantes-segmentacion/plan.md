# Plan 004 · Variantes de segmentación candidatas a corrida principal

**Estado:** aprobado (2026-10-28). Spec: `spec.md` de esta carpeta.

## Código
| Requisito | Dónde | Qué hace |
|---|---|---|
| RF-01 | `segmentacion.matriz_rasgos(con_volatilidad=True)` | Los 4 rasgos base; `segmentacion.rel` queda pública |
| RF-02 `pca_r` | `experimentos.rasgos_pca_r` | PCA ponderada de los 6 valores de participación relativa |
| RF-02 `gower` | `experimentos.gower`, `k_medoides` | Distancia de Gower y k-medoides ponderado |
| RF-02 `kproto` | `experimentos.kprototipos` | K-Prototypes de kmodes con `sample_weight` |
| RF-02 `consenso` | `experimentos.consenso` | Co-asociación y enlace promedio |
| RF-02 `gmm`, RF-05 | `experimentos.mezcla`, `probabilidades` | Mezcla ponderada por remuestreo y probabilidades alineadas a sus perfiles |
| RF-03, RF-04 | `experimentos.evaluar_variante`, `metricas` | Selección de k, estabilidad y métricas en el espacio común |
| RF-06 | `experimentos.centroides_z` y funciones de `perfiles.py` | Centroides y composición |
| RF-07 | `figuras.radar_centroides`, `figuras.mapa_centroides` | Gráficas |
| RF-08 | `contenido.sugerir_nombre` | Nombre sugerido |
| RF-10, RF-11 | `experimentos.arquetipos`, `seleccion_arquetipos`, `estabilidad_arquetipos`, `perfiles.mezcla_secciones`, `figuras.mezcla_por_perfil`, `analisis.paso_arquetipos` | Arquetipos ponderados (alternancia de NNLS con suma 1, inicio «furthest sum»), mezcla por celda, perfil y sección |
| Todo | `analisis.paso_experimentos` | Corre las variantes y escribe `entrega/tablas/experimentos/` |

## Notebook
Secciones «11c. Variantes de segmentación (spec 004)» y «11d. Arquetipos (spec 004, RF-10)» antes de la 12.

## Documento
Un párrafo de arquetipos en la sección 3.6, con cifras leídas de `entrega/tablas/experimentos/`.

## Pruebas
`src/tests/test_experimentos.py`.

## Si se cumple D4
Se cambia la corrida principal en `analisis.CORRIDAS`, se reescriben `contenido.NOMBRES` y `ESTRATEGIAS`, y se regeneran las fichas, el PDF y la presentación.
