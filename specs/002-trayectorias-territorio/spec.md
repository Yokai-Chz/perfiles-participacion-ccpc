# 002 · Trayectorias en el tiempo y análisis por distrito

**Estado:** aprobada (2026-10-25)

> Aprobada el 2026-10-25: la persona responsable aceptó las recomendaciones D1 a D7 y pidió agregar RF-16 (figuras de estadísticas y de los algoritmos en `entrega/estadisticas/`).
**Fecha:** 2026-10-25
**Fecha límite de entrega:** 2026-10-31, 18:00 (envío). Documentos cerrados el 2026-10-29.
**Extiende:** `specs/001-perfiles-ciudadanos/`. Todo lo que esta spec no cambia sigue rigiéndose por la 001.

## 1. Contexto y objetivo

La spec 001 produjo 5 perfiles a partir de celdas demográficas (entidad × tipo de sección × sexo × grupo de edad), descritas por su nivel, brecha y tendencia de participación relativa a su entidad (D16b). El equipo quiere reforzar la solidez del análisis y agregar una lectura territorial y en el tiempo:

- Tratar `NS` como un problema de calidad y no como abstención.
- Reconocer de forma explícita la falacia ecológica.
- Seguir generaciones (cohortes) como pseudo-panel y medir el efecto del primer voto.
- Medir la volatilidad de la participación.
- Mostrar la estructura de los datos (PCA) y validar los perfiles con otros métodos.
- Analizar zonas a lo largo del tiempo con una unidad territorial del INE.

Decisiones ya tomadas por la persona responsable (2026-10-25):
- La corrida principal de la 001 **no se reemplaza**. La unidad de los perfiles sigue siendo el estado.
- La **región** se usa solo como corrida de apoyo.
- La zona para el análisis en el tiempo es el **distrito electoral federal**.
- El Censo 2020 (INEGI-INE) no se incorpora y queda como línea futura (se mantiene D5a de la 001).

## 2. Hechos verificados sobre los datos

Verificados el 2026-10-25 en los `.txt` de descripción y en los Parquet de las 6 elecciones:

| Hecho | Estado |
|---|---|
| En 2009, 2012, 2015, 2018 y 2021, `DEF` y `DEL` están en el **marco cartográfico DERFE 2021**. En 2024 están en el **marco DERFE 2023**. | Según los `.txt` de cada año. |
| Ninguna sección cambia de distrito federal entre 2009 y 2021 (0 de 63,859 secciones presentes en ambos años). | Verificado. |
| Entre 2021 y 2024 cambiaron de distrito federal 13,183 de 67,976 secciones presentes en ambos años. | Verificado. |
| Hay 300 distritos federales en 2015 a 2024. En 2009 y 2012 hay secciones sin `DEF` (1,522,844 y 909,923 personas en lista nominal), que no existen en el marco 2021. | Verificado. |
| 62,048 secciones aparecen en las 6 elecciones, de 72,681 distintas. 2,775 secciones de 2024 no existen en 2021. | Verificado (clave entidad + sección). |
| Secciones con `NS` mayor a 25 % de su lista: 2,444 (2009), 251 (2012), 6,313 (2015), 7,415 (2018), 5,078 (2021), 7,193 (2024). | Verificado. |
| `NS` agrupa cuadernillos sin marcas, no disponibles, solicitados por autoridad jurisdiccional o páginas faltantes. No es abstención. | Según los `.txt`. |
| `SEXO = 2` (no binario) solo existe en 2024. | Según el `.txt` de 2024. |
| La edad es exacta en años cumplidos al día de la elección; la mínima es 18. | Verificado. |
| Sección × sexo × 5 grupos de edad da 707,525 unidades en 2024, con mediana de 105 personas y 137,060 con menos de 50. | Verificado: por eso la sección no se usa como unidad de perfiles. |

## 3. Alcance

**Incluye:** calidad por sección según `NS`; rasgo de volatilidad; estructura de los datos y validación con métodos alternativos; análisis de cohortes y efecto del primer voto; trayectoria de participación por distrito federal y composición de perfiles por distrito; corrida de apoyo por región; ajustes de reproducibilidad; incorporación de estos resultados a los entregables sin pasar sus límites.

**No incluye:** cambiar la unidad o el número de perfiles de la corrida principal; datos del Censo o de otras fuentes externas; mapas con geometría (no hay cartografía en los datos ni se agregan dependencias); distritos locales; datos individuales.

## 4. Requisitos funcionales

- **RF-01 Calidad por sección.** Se identifican las combinaciones (elección, entidad, sección) cuyo `NS` supera el umbral de D1, y se reportan su número y su lista nominal por elección y entidad.
- **RF-02 Sensibilidad a NS.** Se repite la segmentación sin las secciones marcadas en RF-01 y se compara con la corrida principal (k elegido, ARI de la asignación de las celdas comunes y peso de cada perfil). La corrida principal no cambia por este requisito.
- **RF-03 Volatilidad.** Cada celda tiene una medida de volatilidad: la variación de su participación relativa entre elecciones. Cada perfil reporta su volatilidad ponderada por lista nominal. Su uso en la segmentación se rige por D2.
- **RF-04 Estructura de los datos.** Se reporta la proporción de varianza que explica cada componente principal de los rasgos estandarizados, y una vista de los dos primeros componentes con la asignación de perfiles.
- **RF-05 Validación con otros métodos.** Para el k elegido, se compara la asignación de k-means con al menos un método jerárquico y un modelo de mezcla gaussiana, mediante ARI. Se reporta el BIC del modelo de mezcla para k de 4 a 6. Se declara qué métodos no admiten pesos.
- **RF-06 Cohortes.** Se agrega la participación por cohorte de nacimiento (D5) × sexo × tipo de sección × elección, como cociente de sumas y como participación relativa a la entidad (misma referencia que la 001).
- **RF-07 Efecto primer voto.** Para cada cohorte que tiene entre 18 y 20 años en alguna elección, se compara su participación relativa en esa primera elección con la de la siguiente y la de seis años después. La comparación usa participación relativa para no confundirla con el tipo de elección.
- **RF-08 Cohortes y perfiles.** Se describe qué cohortes componen cada perfil, ponderando por la lista nominal de 2024.
- **RF-09 Equivalencia sección a distrito.** Cada (entidad, sección) se asocia a su distrito federal en el marco 2021 y en el marco 2023. Las secciones sin equivalencia se reportan con su lista nominal y no se imputan (D4).
- **RF-10 Trayectoria por distrito.** Para cada distrito federal en el marco 2021 y cada elección de 2009 a 2024 se reportan la tasa, la participación relativa a la entidad, el porcentaje de `NS` y el porcentaje de lista urbana, junto con su nivel, brecha, tendencia y volatilidad.
- **RF-11 Perfiles por distrito.** Se reporta la composición por perfil de la lista nominal 2024 de cada distrito federal, en el marco 2023 (uso operativo actual) y en el marco 2021 (comparación en el tiempo).
- **RF-12 Conservación.** En cada elección, la lista nominal sumada de todos los distritos más la «sin distrito» es igual al total nacional.
- **RF-13 Corrida de apoyo por región.** Se repite la segmentación con la región (D3) como unidad territorial de las celdas y como referencia de la participación relativa. Se compara con la corrida principal como se hizo con la referencia nacional en la 001 (D16).
- **RF-14 Falacia ecológica.** Los entregables dicen de forma explícita que los perfiles describen grupos y territorios y no personas, y que una cohorte no sigue a las mismas personas.
- **RF-15 Límites de interpretación de cohortes.** Se declara que edad, periodo y cohorte no se separan por completo, y que el año de nacimiento es aproximado (±1 año).
- **RF-16 Figuras de estadísticas.** En `entrega/estadisticas/` se generan figuras PNG con: (a) estadísticas y distribuciones de los datos (lista nominal por edad y sexo, participación por elección, tipo de sección y entidad, distribución de `NS` por sección, distribución de los rasgos de las celdas); (b) visualizaciones de los algoritmos (selección de k, PCA, comparación entre métodos, estabilidad, rasgos por perfil); (c) cohortes y distritos. Cada figura sale de una tabla en `entrega/tablas/`. Estas figuras no cuentan para el límite de páginas: son material de apoyo del repositorio y del `.zip`.

## 5. Requisitos de entrega

Los RE-01 a RE-08 de la 001 siguen vigentes. Esta spec agrega:
- **RE-09** El documento técnico incorpora RF-01, RF-07, RF-11 y RF-14 sin pasar de 12 páginas (D6). El resto de los resultados va en las tablas del repositorio.
- **RE-10** La presentación sigue en 10 diapositivas como máximo; un resultado nuevo reemplaza contenido, no lo suma.

## 6. Requisitos no funcionales

- **RNF-01** Sin dependencias nuevas: todo se resuelve con Polars y scikit-learn (constitución, art. 1).
- **RNF-02** Reproducibilidad: dos corridas seguidas con los mismos datos producen tablas idénticas byte a byte, incluido el orden de filas y columnas. Hoy varias tablas de la 001 cambian de orden entre corridas; esto se corrige.
- **RNF-03** La corrida principal de la 001 no cambia: perfiles, k y tablas de perfiles iguales a las del commit `d48acaf`, sin importar el orden.
- **RNF-04** Toda cifra publicada sale de una tabla en `entrega/tablas/` (RNF-06 de la 001).
- **RNF-05** El notebook completo corre en esta máquina en menos de 10 minutos.
- **RNF-06** Textos en español, sin rayas largas (reglas antislop vigentes).

## 7. Criterios de finalización

- Todas las pruebas pasan, incluidas las nuevas para cohortes, equivalencia de distritos, marca de `NS` y volatilidad.
- RF-12 se cumple en las 6 elecciones.
- RNF-02 y RNF-03 comprobados.
- `verificacion.resumen()`: de 8 a 12 páginas, 10 diapositivas como máximo, fichas a 300 ppp, 0 rayas largas.
- `MEMORY.md` y `entrega/lista_verificacion.md` actualizados.

## 8. Decisiones abiertas

Resueltas el 2026-10-25: se adopta la recomendación de cada una.

**D1. Umbral de NS por sección.** (a) 10 %. (b) 25 %. (c) Sin umbral fijo: reportar la distribución.
*Recomendación:* (b). Con 25 % se marcan entre 251 y 7,415 secciones por elección; con 10 %, la cifra apenas sube (de 278 a 8,552), así que 25 % aísla los casos graves.

**D2. Volatilidad en la segmentación.** (a) Solo descriptiva. (b) Corrida variante con 4 rasgos, comparada con la principal mediante ARI. (c) Reemplazar el vector principal.
*Recomendación:* (b). (c) cambiaría perfiles, textos y entregables a 6 días del envío.

**D3. Definición de región.** (a) Circunscripciones plurinominales vigentes (marco 2023), fijas para todos los años. (b) 5 o 6 regiones geográficas definidas por el equipo.
*Recomendación:* (a), por ser una regionalización oficial del INE, siempre que la asignación de estados se verifique en el acuerdo del INE antes de usarla. Si no se puede verificar, (b), con la lista de estados escrita en esta spec.
*Verificado el 2026-10-25* en el acuerdo INE/CG130/2023 (punto primero), vigente desde el proceso federal 2023-2024: 1 (Guadalajara): Baja California, Baja California Sur, Chihuahua, Durango, Jalisco, Nayarit, Sinaloa, Sonora. 2 (Monterrey): Aguascalientes, Coahuila, Guanajuato, Nuevo León, San Luis Potosí, Tamaulipas, Zacatecas. 3 (Xalapa): Campeche, Chiapas, Oaxaca, Quintana Roo, Tabasco, Veracruz, Yucatán. 4 (Ciudad de México): Ciudad de México, Guerrero, Hidalgo, Morelos, Puebla, Tlaxcala. 5 (Toluca): Colima, Estado de México, Michoacán, Querétaro.

**D4. Secciones sin equivalente entre marcos.** (a) Reportarlas como «sin distrito» sin imputar. (b) Asignarlas al distrito más frecuente de su municipio.
*Recomendación:* (a). Imputar a partir del municipio mezcla unidades del INE con criterios propios.

**D5. Cohorte.** (a) Año de nacimiento = año de la elección − edad (±1 año por la fecha de la elección). (b) Cohortes quinquenales sobre (a).
*Recomendación:* (b) para tablas y figuras, para tener menos ruido, conservando (a) para el efecto primer voto.

**D6. Páginas del documento técnico.** (a) Integrar solo lo indicado en RE-09 y mover el detalle al repositorio. (b) Reemplazar secciones actuales.
*Recomendación:* (a), con un máximo de 12 páginas.

**D7. Prioridad si falta tiempo.** Orden de recorte, del primero al último: modelo de mezcla y método jerárquico (RF-05), corrida por región (RF-13), variante con volatilidad (D2b). NS, cohortes y distritos no se recortan.
