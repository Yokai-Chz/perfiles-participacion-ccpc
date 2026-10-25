# Plan · 001 Perfiles ciudadanos de participación

**Estado:** borrador (bloqueado: la spec sigue en `borrador` y tiene decisiones abiertas)
**Spec:** `specs/001-perfiles-ciudadanos/spec.md`
**Fecha:** 2026-10-20

> **Cumplimiento de las guías SDD.** La guía de plan exige spec aprobada sin dudas abiertas, y `AGENTS.md` y `MEMORY.md`. Hoy no existe ninguno de esos tres archivos (solo `docs/constitution.md`). Por indicación de la persona responsable, este borrador se redacta antes de resolver las dudas. **Nada de este plan se implementa** hasta que la spec se apruebe. El plan asume las *recomendaciones* de la sección 8 de la spec; si alguna decisión cambia, se revisan las secciones marcadas con «depende de Dn».

## 1. Estado del código y de las pruebas

- No existe código, repositorio git ni pruebas. La carpeta contiene `Convocatoria_Hackaton-1.pdf`, `docs/constitution.md`, `.mcp.json` y `.claude/`.
- El único antecedente técnico es el notebook de prueba en Colab (2 celdas: descarga de Colima 2021 y lectura de 1,000 filas). **No se modifica**; se aprovecha solo como referencia del patrón de descarga con `gdown`.
- Entorno de ejecución: Colab, conectado mediante `colab-mcp`. Cada ejecución de celda se aborta si pasan 30 s sin salida; las celdas largas deben emitir progreso o dividirse (ver riesgo R3).
- Nota de la constitución: los artículos están numerados 1, 2 y 6; faltan el 3, 4 y 5. Se confirma con la persona responsable si son omisiones.

## 2. Resumen del enfoque (depende de D2, D1, D4)

Se segmentan **celdas demográficas** (grupo de edad × sexo × tipo de sección × entidad) según su **trayectoria de participación** a lo largo de las 5 elecciones, medida frente al promedio nacional de cada elección. Se agrupan con k-means ponderado por lista nominal, con k entre 4 y 6. Después se caracteriza cada perfil, se le pone nombre y estrategia, y se ubica en el territorio por sección para los mapas y las fichas.

**Salvedad metodológica que debe aparecer en el documento.** Una celda «20 a 24 años» en 2009 y en 2021 contiene personas distintas (los de 2009 tienen 32 a 36 años en 2021). La trayectoria describe cómo se comporta una *franja de edad* en cada elección, no el recorrido de las mismas personas. Esto se declara; seguir cohortes reales corresponde a la opción D2(c).

## 3. Archivos y responsabilidades (propuestos)

| Archivo | Responsabilidad |
|---|---|
| `src/ingesta.py` | Listar la carpeta compartida (recursivo, por la carpeta anidada de 2021), descargar con reintentos y escribir un único Parquet con elección y entidad por fila. |
| `src/calidad.py` | Validaciones de RF-02 y tabla de calidad de RF-15. |
| `src/indicadores.py` | Limpieza de edad (RF-04), grupos de edad, tasa de participación (RF-05), diferencia frente al promedio nacional por elección (RF-06). |
| `src/segmentacion.py` | Matriz de rasgos por celda (RF-07), k-means ponderado, selección de k y estabilidad (RF-08, RF-09). |
| `src/perfiles.py` | Caracterización de cada perfil (RF-10) y asignación de perfil a cada sección para los mapas. |
| `src/figuras.py` | Gráficas y tablas listas para las fichas, el documento y las diapositivas (RF-11, RNF-06). |
| `notebooks/01_pipeline.ipynb` | Ejecución en Colab de principio a fin (RF-14). Contiene solo llamadas a `src/`. |
| `tests/test_indicadores.py`, `tests/test_calidad.py`, `tests/test_segmentacion.py` | Pruebas automatizadas de funciones puras con tablas sintéticas pequeñas (**nuevas; requieren D12**). |
| `README.md` | Cómo reproducir el análisis y qué datos se necesitan. |
| `entrega/` | Documento técnico, fichas, presentación, cartas y `.zip` final (artefactos, no código). |

La estructura es simple a propósito (constitución, art. 1). Los módulos exponen funciones sobre `polars.LazyFrame` o `DataFrame` y no guardan estado.

## 4. Flujo (pseudocódigo)

```text
1. ingesta
   archivos = listar_carpeta(recursivo)            # 5 años × 32 entidades
   para cada archivo: leer CSV (utf8, esquema fijo) + columnas anio, entidad
   escribir datos/ccpc.parquet                      # persistido en Drive (D11)

2. calidad
   verificar LN == SV + NV + NS en todas las filas
   verificar unicidad (anio, EDOCVE, SECCION, SEXO, EDAD)
   tabla: filas, LN, SV, NV, NS por anio y entidad; edades > 90

3. indicadores
   EDAD -> top-code "90+" (D6); grupo_edad
   tasa = sum(SV) / sum(SV + NV)                    # D1; nunca promedio de tasas
   excluir unidades con sum(LN) < umbral (D7)
   rel_nacional[anio] = tasa_celda - tasa_nacional[anio]   # D4

4. segmentacion
   celda = (grupo_edad, sexo, TIPOSEC, EDOCVE)
   X = rasgos candidatos que separen nivel de forma (no solo los 5 valores de rel_nacional,
       que separarían principalmente por nivel de participación):
         - participación relativa media
         - brecha presidenciales − intermedias
         - tendencia 2009 → 2021
       [+ los 5 valores por elección, si aportan]
   escalar; para k en 4..6: KMeans(sample_weight = LN, semilla fija)
   elegir k: silhouette + estabilidad (varias semillas, submuestras) + interpretabilidad

5. perfiles
   por perfil: edad, sexo, región, TIPOSEC, trayectoria, peso (LN)
   para cada (EDOCVE, SECCION): proporción de su LN que cae en cada perfil (composición)
   mapa: proporción de un perfil elegido, o perfil más sobrerrepresentado frente a su peso nacional
   (una celda no tiene dimensión de sección: asignar un solo perfil por «celda dominante»
    daría el mismo resultado a todas las secciones de una misma entidad y tipo)
   nombre + narrativa + estrategia (trabajo humano, con apoyo de las tablas)

6. figuras y entrega
   generar tablas/figuras desde código; maquetar documento, fichas y deck
   lista de verificación de cumplimiento; .zip; envío
```

## 5. Interfaz

No hay interfaz de usuario. Las interfaces son las funciones públicas de `src/` (entrada y salida en Polars) y el notebook como punto de entrada. Contratos principales: `cargar(anios, entidades) -> LazyFrame`, `validar(df) -> dict`, `tasa_participacion(df, por) -> DataFrame`, `segmentar(celdas, k, semilla) -> DataFrame`.

## 6. Compatibilidad de datos

- Esquema único de 16 columnas (verificado en Colima; verificar en todas las entidades dentro de la ingesta, con error explícito si algún archivo difiere).
- Clave territorial: (`EDOCVE`, `SECCION`) siempre. `SECCION` sola **no** es única en el país.
- Los `.txt` y los CSV están en UTF-8; se leen como tal (en la exploración se leyeron como latin-1 y se vio texto corrupto).
- Las secciones cambian entre elecciones. El enfoque D2(b) no necesita seguir una sección en el tiempo; solo la asignación de perfil a la sección usa la elección de referencia (por defecto 2021, el marco cartográfico de DEF/DEL).
- Tipos compactos y textos categóricos para caber en memoria (RNF-04).

## 7. Decisiones de diseño y alternativas consideradas

| Decisión | Elegida | Alternativas descartadas |
|---|---|---|
| Unidad | Celdas demográficas (D2b) | Secciones: no produce perfiles de personas. Cohortes: más trabajo y riesgo con 11 días. |
| Método | K-means ponderado | Jerárquico: no escala bien con muchas celdas. GMM: más difícil de explicar a un público no técnico. Se puede usar como validación. |
| Formato intermedio | Parquet | CSV: lento y sin tipos. |
| Ejecución | Colab con módulos en `src/` | Todo en celdas del notebook: difícil de probar y de entregar como código. |
| Participación relativa | Diferencia frente al promedio nacional de cada elección | Valores absolutos: mezclan el efecto presidencial/intermedia con el perfil. |

## 8. Matriz de trazabilidad

La columna «prueba automatizada» solo cita pruebas **nuevas propuestas**; hoy no existe ninguna. «Manual» es una comprobación concreta que hace una persona.

| Req. | Cambio previsto | Prueba automatizada | Comprobación manual |
|---|---|---|---|
| RF-01 | `ingesta.py` | Propuesta: lee 2 CSV sintéticos y verifica columnas anio y entidad. | En Colab, contar archivos leídos: 160 CSV (5 años × 32). Comparar con el listado de Drive. |
| RF-02 | `calidad.validar` | Propuesta: tabla con una fila `LN ≠ SV+NV+NS` debe ser reportada; tabla con duplicado debe fallar. | Revisar la tabla de calidad nacional; el desbalance máximo debe ser 0 o estar explicado. |
| RF-03 | uso de (EDOCVE, SECCION) en todos los `group_by`/`join` | Propuesta: dos entidades con la misma sección no se mezclan al agregar. | Revisar que el número de secciones únicas por año se acerque a lo publicado por el INE (por confirmar contra una fuente). |
| RF-04 | `indicadores.limpiar_edad` | Propuesta: edades 89, 90, 125 → «90+»; conteo reportado. | Revisar cuántas personas se afectan por año. |
| RF-05 | `indicadores.tasa_participacion` | Propuesta: promedio ponderado ≠ promedio simple en un caso construido; `LN=0` no divide. | Comparar la participación nacional por elección contra las cifras de la propia plataforma CCPC (URL de la convocatoria). Una diferencia frente a los cómputos distritales es **esperada** (el CCPC excluye casillas especiales y residentes en el extranjero) y no es un error. |
| RF-06 | `rel_nacional` | Propuesta: la suma ponderada de diferencias por elección es 0, siempre que el promedio nacional se calcule sobre el mismo conjunto ya filtrado por D7. | Revisar que 2012 y 2018 se vean distintas a las intermedias en los datos sin ajustar. |
| RF-07 | `segmentacion.matriz_rasgos` | Propuesta: forma de la matriz y ausencia de nulos. | Revisar la lista de variables contra la convocatoria (edad, sexo, región, historial). |
| RF-08 | `segmentacion.segmentar` | Propuesta: misma semilla ⇒ mismas etiquetas; k fuera de 4-6 falla. | Ejecutar el notebook dos veces y comparar tablas. |
| RF-09 | `segmentacion.estabilidad` | Propuesta: devuelve silhouette y concordancia entre semillas en datos sintéticos separables. | Revisar que el documento justifique k. **Laguna:** no hay criterio automático de «interpretable»; es juicio del equipo. |
| RF-10 | `perfiles.caracterizar` | Propuesta: los pesos de los perfiles suman 100 %; las proporciones por sección suman 100 %. | Revisar cada ficha contra la tabla de origen; comprobar en el mapa que secciones de una misma entidad y tipo no salen idénticas. |
| RF-11 | Texto y figuras | **Sin cobertura automatizada.** | Lectura por una persona ajena al equipo: ¿entiende cada perfil sin explicación? |
| RF-12 | Texto | **Sin cobertura automatizada.** | Revisión de que cada estrategia cite un rasgo del perfil y una acción posible para el INE. |
| RF-13 | Diseño: todo agregado | Propuesta: ninguna columna de salida tiene granularidad individual (el mínimo es celda o sección). | Revisar los archivos de `entrega/`. |
| RF-14 | Notebook + `README.md` | **Sin cobertura automatizada.** | Persona ajena ejecuta el notebook desde cero y compara 3 cifras clave. |
| RF-15 | `calidad.tabla` | Propuesta: columnas y totales de una tabla de ejemplo. | Revisar la tabla de calidad en el repositorio y el `.zip` (si va en el PDF, cuenta dentro del límite de cuartillas; ver D15). |
| RE-01 a RE-08 | Documentos de `entrega/` | **Sin cobertura automatizada** (excepto el conteo de diapositivas, si se decide). | Lista de verificación: páginas (8-12), fuente (Arial/Calibri 11), interlineado 1.5, 4-6 perfiles, ≤10 diapositivas, firmas, nombre del `.zip`, destinatarios, tamaño. |

**Lagunas de cobertura (declaradas):**
1. No existe ninguna prueba hoy; todas las anteriores son nuevas y dependen de D12. Sin D12, la verificación es solo manual.
2. La calidad de los perfiles (interpretabilidad, utilidad institucional) no es automatizable.
3. Los entregables documentales se verifican manualmente.
4. La validación contra la plataforma CCPC es manual: hay que localizar sus cifras nacionales por elección.

## 9. Comando de pruebas

Si se aprueba D12: `python -m pytest tests`. No hay frontend, así que no aplican `npm run lint` ni `npm run build`.

## 10. Riesgos y mitigaciones

| Id | Riesgo | Mitigación |
|---|---|---|
| R1 | Límites de descarga de Drive al bajar ~160 archivos con `gdown`. | Reintentos por año, descarga por lotes, avance guardado; alternativa de montar Drive (requiere autorizar en el navegador). |
| R2 | `/content` en Colab es efímero. | Escribir el Parquet y los intermedios en Drive (D11). |
| R3 | Una celda sin salida durante 30 s se aborta en la herramienta. | Dividir en celdas cortas o emitir progreso; si hace falta, elevar el valor `"timeout": 30000` del servidor `colab-mcp` en `.mcp.json` (cambio de configuración que requiere su aprobación). |
| R4 | Memoria con ~40 millones de filas. | Lectura diferida, tipos compactos, agregar antes de materializar. |
| R5 | Cambios de sección entre años. | D2(b) no depende de seguir la misma sección; límites declarados. |
| R6 | Falta 2024 y escolaridad. | Declarar como limitación; D8 y D5. |
| R7 | Tiempo: quedan 11 días. | Calendario con holgura; probar primero con 2 o 3 entidades. |
| R8 | Correo con adjuntos pesados. | D13: tope de tamaño y consulta a las personas contacto. |
| R9 | Descalificación por entregable faltante o firma faltante. | Lista de verificación con responsable y fecha; firmas pedidas desde la primera semana. |

## 11. Calendario propuesto (hoy: 2026-10-20)

| Fechas | Hito |
|---|---|
| 10-20 a 10-21 | Resolver decisiones D1-D15; aprobar spec; confirmar registro y que la carta de cesión se anexó (D9); **repartir los formatos de las dos cartas y pedir las firmas**. |
| 10-21 a 10-22 | Ingesta nacional a Parquet; tabla de calidad. |
| 10-23 a 10-24 | Indicadores y matriz de celdas. |
| 10-24 a 10-26 | Segmentación, selección de k y estabilidad. |
| 10-26 a 10-27 | Caracterización, nombres, estrategias; figuras. |
| 10-27 a 10-29 | Documento técnico, fichas, presentación. Las cartas ya deben estar firmadas (se piden el 10-21; fecha límite interna 10-28). |
| 10-30 | Revisión externa, lista de verificación, `.zip`. |
| 10-31 antes de las 18:00 | Envío y confirmación de recepción (el límite oficial es 23:59). |

## 12. Tareas propuestas (se formalizarán con `sdd-tasks` tras aprobar)

1. Resolver decisiones abiertas y aprobar la spec. *(personas responsables)*
2. Confirmar registro del equipo, paridad, representante y firmantes (D9).
3. Crear repositorio y estructura de carpetas (D10).
4. Implementar `ingesta.py` y generar el Parquet nacional.
2b. Repartir los formatos de las cartas de cesión y de decir verdad y recoger las firmas de todas las personas integrantes (límite interno 10-28).
5. Implementar `calidad.py` y publicar la tabla de calidad.
6. Implementar `indicadores.py` (con sus pruebas, si D12).
7. Construir la matriz de celdas y la validación de unidades pequeñas.
8. Implementar `segmentacion.py`: k-means ponderado, selección de k, estabilidad.
9. Caracterizar perfiles, nombrarlos y redactar estrategias.
10. Generar figuras y tablas.
11. Redactar el documento técnico (8-12 cuartillas).
12. Diseñar las fichas de perfil.
13. Preparar la presentación (≤10 diapositivas).
14. Recopilar las cartas firmadas.
15. Revisión externa de reproducibilidad y de comprensión.
16. Armar el `.zip`, verificar la lista de cumplimiento y enviar.

## 13. Aprobación

Este plan **no está aprobado**. Para avanzar: (1) resolver y registrar D1-D15 en la spec, (2) cambiar el estado de la spec a `aprobada`, (3) revisar y aprobar este plan y las tareas.
