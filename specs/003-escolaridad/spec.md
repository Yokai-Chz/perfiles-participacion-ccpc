# 003 · Escolaridad del entorno en la segmentación

**Estado:** implementada (2026-10-25)

> Aprobada el 2026-10-25: la persona responsable aceptó D1 a D5 con su recomendación y descargará las 32 tablas a `datasets/eceg_2020/`.
**Fecha:** 2026-10-25
**Fecha límite de entrega:** 2026-10-31, 18:00 (envío). Documentos cerrados el 2026-10-29.
**Extiende:** specs 001 y 002. Cambia D5 de la 001 (escolaridad omitida) y la decisión del 2026-10-25 en la 002 (Censo como línea futura).

## 1. Contexto y objetivo

La convocatoria sugiere usar escolaridad «cuando esté disponible» y los CCPC no la traen. El equipo quiere ver cómo cambian los perfiles si la escolaridad entra al vector de rasgos (hoy: nivel, brecha y tendencia de cada celda entidad × tipo de sección × sexo × grupo de edad).

## 2. Fuente y hechos verificados (2026-10-25)

**Estadísticas Censales a Escalas Geoelectorales 2020 (ECEG 2020), INEGI e INE.**

| Hecho | Fuente |
|---|---|
| Indicadores del cuestionario básico del Censo de Población y Vivienda 2020 (marzo de 2020), 220 en total, por sección electoral y por distrito federal. | Boletín INEGI 455/21 |
| Las secciones usan el Marco Seccional Electoral del INE con corte de enero de 2021: el mismo marco de las secciones de los CCPC de 2021. | Metodología INEGI de la ECEG 2020 |
| Cada manzana, caserío disperso o localidad rural del Censo se asigna a una sección por la ubicación de su centroide; los casos fuera de límite van a la sección más cercana. | Metodología INEGI de la ECEG 2020 |
| Variables de escolaridad por sección, todas por sexo: grado promedio escolar; población de 15 años o más sin escolaridad, con primaria o secundaria (completa o incompleta) y analfabeta; población de 18 años o más con educación posbásica. | Archivo por sección de Jalisco con la estructura del INEGI (IIEG Jalisco), 225 columnas |
| **No hay desglose por edad.** | Mismo archivo |
| Hay una descarga nacional (datos abiertos del INEGI) con `conjunto_de_datos/INE_SECCION_2020.csv` y su diccionario; es la que se usa. | Boletín INEGI 455/21 y búsqueda |
| Grado promedio de escolaridad nacional publicado: 9.7 años. | Presentación INEGI de la ECEG 2020 |

## 3. Alcance

**Incluye:** obtener la ECEG 2020 de las 32 entidades; llevar la escolaridad de la sección a la celda; una corrida variante con escolaridad como cuarto rasgo; comparación con la corrida principal; escolaridad del entorno de cada perfil; figuras y tablas de apoyo.

**No incluye:** cambiar la corrida principal; escolaridad por edad (la fuente no la tiene); otros indicadores del Censo; datos individuales.

## 4. Requisitos funcionales

- **RF-01 Obtención.** Se usan las tablas por sección de la ECEG 2020 de las 32 entidades, sin modificarlas, guardadas fuera del repositorio.
- **RF-02 Unión.** Las secciones de la ECEG se unen con las de los CCPC de 2021 por (entidad, sección). Se reportan las secciones sin correspondencia de cada lado y su lista nominal; no se imputan.
- **RF-03 Escolaridad de la celda.** Cada celda recibe el promedio del grado escolar de su mismo sexo en las secciones donde vive, ponderado por la lista nominal de 2021 de esa celda en cada sección.
- **RF-04 Referencia.** La escolaridad de la celda se expresa según D1. Si es relativa, la diferencia ponderada suma cero en cada entidad.
- **RF-05 Corrida variante.** Se segmenta con nivel, brecha, tendencia y escolaridad, con el mismo método, semilla y criterio de selección de k que la principal.
- **RF-06 Comparación.** Se reportan el k elegido, el ARI frente a la principal, el peso de cada perfil y la tabla de cruce entre ambas asignaciones.
- **RF-07 Descripción.** Para cada perfil de la corrida principal se reportan el grado promedio del entorno y el porcentaje con educación posbásica, ponderados por lista nominal.
- **RF-08 Límites declarados.** Se declara que es un dato del entorno y no de las personas, que es de 2020 y se aplica a 2009-2024, que el Censo cuenta residentes y no lista nominal, y que no hay dato para la categoría no binaria.

## 5. Requisitos no funcionales

- **RNF-01** Sin dependencias nuevas: si la fuente viene en XLSX, se lee con la biblioteca estándar.
- **RNF-02** La corrida principal no cambia: tablas iguales a las del commit `3733f18`.
- **RNF-03** Reproducibilidad: dos corridas seguidas dan tablas idénticas byte a byte.
- **RNF-04** Toda cifra publicada sale de una tabla en `entrega/tablas/`.

## 6. Criterios de finalización

- Más de 95 % de la lista nominal de 2021 tiene escolaridad. Si no se alcanza, se detiene y se reporta.
- El grado promedio nacional ponderado queda cerca de los 9.7 años publicados. La diferencia esperada se explica: lista nominal de 18 años o más frente a población de 15 años o más.
- Pruebas nuevas para la ponderación, la referencia y las secciones sin correspondencia; todas las pruebas pasan.
- RNF-02 y RNF-03 comprobados; `verificacion.resumen()` sin fallas.

## 7. Decisiones (resueltas el 2026-10-25 con su recomendación)

**D1. Referencia de la escolaridad.** (a) Relativa a la entidad. (b) Absoluta.
*Recomendación:* (a). Es la misma regla que la participación (D16b de la 001); con (b), las diferencias entre estados volverían a dominar los perfiles.

**D2. Variable.** (a) Grado promedio escolar. (b) Porcentaje de 18 años o más con educación posbásica. (c) Ambas.
*Recomendación:* (a) en el vector y (b) solo para describir. Dos variables de escolaridad le darían el doble de peso frente a cada rasgo de participación.

**D3. Papel en el análisis.** (a) Solo corrida variante. (b) Reemplazar la corrida principal.
*Recomendación:* (a). (b) cambiaría perfiles, nombres, textos y entregables a 6 días del envío.

**D4. Entregables.** (a) Un párrafo y una cifra por perfil en el PDF, con el detalle en el repositorio. (b) También en las fichas. (c) Solo en el repositorio.
*Recomendación:* (a). Las fichas ya están completas.

**D5. Obtención de los datos.** Las tablas se descargan por entidad desde la página del Censo 2020 (pestaña de herramientas) o desde el Mapa Digital de México, y se guardan en `datasets/eceg_2020/`.
*Recomendación:* la persona responsable las descarga, porque no hay una descarga directa que el código pueda automatizar con certeza.
