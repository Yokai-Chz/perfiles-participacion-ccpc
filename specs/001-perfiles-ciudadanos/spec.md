# 001 · Perfiles ciudadanos de participación (Reto 1)

**Estado:** aprobada (2026-10-24)
**Fecha:** 2026-10-20
**Fecha límite de entrega:** 2026-10-31, 23:59

> Aprobada el 2026-10-24: la persona responsable aceptó en bloque las recomendaciones D1–D15 de la sección 8 y confirmó D9 (equipo registrado, paritario y carta de cesión anexada). D3 y D12 se resolvieron enmendando el art. 1 de la constitución (scikit-learn y pytest). D8 sigue pendiente de respuesta del INE: si no hay datos de 2024, se declara como limitación.
>
> Contraste con `convocatoria.md` (2026-10-24): el Eje 1 tiene un solo reto; los entregables RE-01 a RE-08 coinciden con las bases SEXTA y SÉPTIMA. La convocatoria dice «género» pero los datos solo traen `SEXO`; se usa «sexo» y se declara. Criterios de evaluación: apego, solidez, originalidad, viabilidad y potencial institucional.

## 1. Contexto y objetivo

La convocatoria «Hackea la participación: Datos que construyen democracia» (INE-DECEyEC) pide a cada equipo elegir **un solo eje**. Este proyecto elige el **eje 1, Reto 1: Perfiles ciudadanos de participación**.

Pregunta guía del reto: *¿qué tipos de ciudadanía existen según su comportamiento de participación?*

Objetivo: identificar **4 a 6 perfiles ciudadanos claramente diferenciados** a partir de los Conteos Censales de Participación Ciudadana (CCPC), caracterizarlos, nombrarlos y proponer una estrategia de fomento a la participación distinta para cada uno, de forma que el INE pueda usarlos en campañas focalizadas y mensajes diferenciados.

## 2. Hechos verificados sobre los datos

Verificados el 2026-10-20 en la carpeta compartida de Drive y en el CSV de **Colima** de cada año:

| Hecho | Estado |
|---|---|
| La carpeta contiene 5 elecciones: 2009, 2012, 2015, 2018 y 2021, con un CSV por entidad (32) y un `.txt` de descripción por año. | Verificado (165 archivos). |
| **Actualización 2026-10-24: la carpeta ya incluye 2024.** Ahora hay 198 archivos (192 CSV = 6 elecciones × 32 entidades, más 6 `.txt`). La verificación del 10-20 (sin 2024, 165 archivos) quedó superada; D8 se resuelve con (a). El análisis usa 6 elecciones (2024 es presidencial). | Verificado el 10-24 por listado de la carpeta. |
| Esquema y `LN = SV + NV + NS` en Aguascalientes, Colima y CDMX × 6 años (18 archivos). | Verificado el 10-24: un solo esquema de 16 columnas y 0 filas con desbalance. Faltan las otras 29 entidades. |
| El esquema es idéntico en los 5 años: `AELEC, FELECCION, EDOCVE, EDONOM, MPIOCVE, MPIONOM, SECCION, TIPOSEC, DEF, DEL, SEXO, EDAD, LN, SV, NV, NS`. | Verificado en Colima; los `.txt` son iguales entre años. Falta verificar en las 32 entidades. |
| Cada fila es una combinación de sección × sexo × edad. | Verificado. |
| `LN = SV + NV + NS` en todas las filas. | Verificado solo en Colima. |
| `SEXO`: 0 = hombres, 1 = mujeres. `TIPOSEC`: U, M, R. | Verificado. |
| **No existe escolaridad** en esta fuente. | Verificado. |
| La edad llega a 112-132 años en Colima; la edad mínima es 18. | Verificado solo en Colima. |
| `NS` pesa muy distinto por elección (en Colima 2015 fue cerca del 8 % de `LN`; en 2012 fue cercano a 0). | Verificado en Colima. |
| La referencia territorial es la sección de la credencial. Los datos excluyen casillas especiales y residentes en el extranjero. | Según la descripción oficial. |
| Los archivos de 2021 están en una carpeta anidada un nivel más. | Verificado. |

Suposiciones **no verificadas**: el país completo tiene del orden de 8 millones de filas por elección y unos 40 millones en total (estimación proporcional a Colima); las secciones cambian de límites entre años; `SECCION` solo es única dentro de una entidad.

## 3. Alcance

**Incluye:** análisis con datos agregados (sin datos personales) de las elecciones disponibles; segmentación; caracterización; narrativa y estrategias por perfil; todos los entregables obligatorios del Reto 1.

**No incluye:** los ejes 2 y 3; datos personales o desagregación individual; fuentes externas, salvo que se decida lo contrario en D5.

## 4. Requisitos funcionales (análisis)

- **RF-01 Ingesta completa.** El análisis incorpora todos los archivos de entidad de todas las elecciones disponibles en un solo conjunto, identificando de forma inequívoca elección y entidad de cada fila.
- **RF-02 Integridad.** Se verifica en todo el conjunto que `LN = SV + NV + NS` y que no hay filas duplicadas por (elección, entidad, sección, sexo, edad). Las filas que incumplan se reportan; no se descartan en silencio.
- **RF-03 Identificador territorial.** Toda unión o agregación por sección usa la pareja (entidad, sección), nunca la sección sola.
- **RF-04 Limpieza de edad.** Las edades atípicas se tratan con una regla única y documentada (D6). El conteo de personas afectadas se reporta.
- **RF-05 Indicador de participación.** Existe una única definición de tasa de participación (D1), calculada siempre como cociente de **sumas** y nunca como promedio de porcentajes. Se documentan las reglas para denominadores nulos o muy pequeños (D7).
- **RF-06 Diferencia entre tipos de elección.** El análisis distingue las elecciones presidenciales (2012, 2018) de las intermedias (2009, 2015, 2021) para que esa diferencia no se confunda con tendencia (D4).
- **RF-07 Variables de segmentación.** Se construye, para cada unidad de análisis (D2), un conjunto de variables que cubra edad, sexo, región o entidad, tipo de sección e historial de participación por elección. Las variables de historial deben separar el **nivel** de participación de su **forma** en el tiempo (por ejemplo: nivel medio, brecha entre elecciones presidenciales e intermedias y tendencia), para que los perfiles no se distingan solo por «más o menos participación». La escolaridad solo se incluye si se decide en D5.
- **RF-08 Segmentación.** Se aplica un método de segmentación que produce entre 4 y 6 perfiles. La corrida es reproducible: mismos datos y misma semilla dan los mismos perfiles.
- **RF-09 Validación.** Se documenta la elección del número de perfiles con al menos una medida cuantitativa y un criterio de interpretabilidad, y se mide la estabilidad de los perfiles ante cambios de semilla y submuestras.
- **RF-10 Caracterización.** Cada perfil se describe con edad, sexo, región, tipo de sección e historial de participación, con cifras agregadas y su peso (cuántas personas o unidades representa). Su presencia en el territorio se expresa como la **composición de cada sección** (qué proporción de su lista nominal pertenece a cada perfil), no como una etiqueta única por sección.
- **RF-11 Perfiles con nombre y narrativa.** Cada perfil recibe un nombre y una descripción narrativa y visual comprensibles para personal del INE sin formación técnica.
- **RF-12 Estrategias.** Cada perfil tiene una estrategia diferenciada de fomento a la participación, ligada explícitamente a sus rasgos y a un uso institucional concreto.
- **RF-13 Sin datos personales.** Ningún producto del análisis contiene datos individuales; todo está agregado.
- **RF-14 Reproducibilidad.** Una persona del equipo puede repetir el análisis completo de principio a fin con el código entregado y obtener las mismas tablas y figuras.
- **RF-15 Calidad de datos documentada.** Se entrega una tabla de calidad (filas, totales y `NS` por elección y entidad, edades atípicas) que respalda el documento técnico. La participación nacional obtenida se contrasta con las cifras de la propia plataforma CCPC; una diferencia frente a los cómputos distritales es esperada, porque el CCPC excluye casillas especiales y residentes en el extranjero.

## 5. Requisitos de entrega (cumplimiento de la convocatoria)

Falta cualquiera de los obligatorios ⇒ **descalificación**. Cada uno debe tener responsable y fecha (ver plan).

- **RE-01 Documento técnico**: PDF de 8 a 12 cuartillas, Arial o Calibri 11, interlineado 1.5; incluye 4 a 6 perfiles diferenciados, metodología de segmentación y estrategias diferenciadas.
- **RE-02 Fichas de perfil**: archivo(s) PDF o PNG de alta resolución con resumen narrativo e iconográfico de cada perfil.
- **RE-03 Presentación ejecutiva**: máximo 10 diapositivas.
- **RE-04 Código o enlace a repositorio.**
- **RE-05 Carta de cesión de derechos** firmada por **todas** las personas integrantes (formato en la página de la convocatoria).
- **RE-06 Carta declaratoria de decir verdad** firmada por todas las personas integrantes.
- **RE-07 Paquete**: carpeta `.zip` identificada con **nombre del equipo y eje temático**, enviada **solo por correo** a `grecia.castro@ine.mx` y `cirse.rodriguez@ine.mx` antes del 2026-10-31 23:59.
- **RE-08 Condiciones previas del equipo**: equipo paritario de 2 a 4 personas, registrado dentro del periodo (cerró el 2026-10-15), con representante con cuenta bancaria mexicana. **No se ha verificado** que el equipo esté registrado (D9).

## 6. Requisitos no funcionales

- **RNF-01 Stack:** Python con Polars (constitución, art. 1). Cualquier dependencia adicional requiere decisión explícita (D3).
- **RNF-02 Idioma:** textos visibles, comentarios y documentación en español (constitución, art. 6).
- **RNF-03 Datos originales:** los archivos de origen nunca se modifican.
- **RNF-04 Recursos:** el procesamiento completo debe caber en un entorno gratuito de Colab (memoria limitada), por lo que se prefieren lecturas diferidas y tipos compactos.
- **RNF-05 Persistencia:** los resultados intermedios sobreviven al reinicio del entorno de ejecución.
- **RNF-06 Precisión:** toda cifra publicada en el documento, fichas o diapositivas se puede rastrear hasta una tabla producida por el código.
- **RNF-07 Valor institucional:** las propuestas son aplicables a acciones reales del INE (criterios de evaluación de viabilidad y potencial de aplicación).
- **RNF-08 Honestidad metodológica:** las limitaciones (falta de 2024, falta de escolaridad, cambios de sección, exclusión de casillas especiales) se declaran de forma visible.

## 7. Criterios de finalización

1. RF-01 a RF-15 cumplidos y verificados según la matriz del plan.
2. Los 8 requisitos de entrega (RE-01 a RE-08) comprobados con una lista de verificación firmada por el equipo.
3. Todas las decisiones de la sección 8 resueltas y registradas.
4. Un revisor ajeno al análisis puede reproducir las tablas clave desde el código.
5. Paquete enviado y confirmada la recepción, **antes del 2026-10-31 18:00** (margen interno de 6 horas sobre el límite).

## 8. Decisiones abiertas

Cada una tiene opciones y una recomendación. Ninguna está resuelta.

**D1. Definición de participación.**
(a) `SV / LN`. (b) `SV / (SV + NV)`, excluyendo `NS`. (c) ambas, con una como principal.
*Recomendación:* (b) como principal, marcando las unidades donde `NS` supere un umbral. `NS` varía mucho entre elecciones (8 % en Colima 2015) y distorsionaría las comparaciones.

**D2. Unidad de segmentación** (decisión central: define qué es un «perfil ciudadano»).
(a) **Secciones electorales**, agrupadas por participación y composición. Resultan perfiles territoriales. Es lo más simple, pero se aleja de «jóvenes con alta participación» que usa la convocatoria como ejemplo.
(b) **Celdas demográficas** (sexo × grupo de edad × tipo de sección × región o entidad), agrupadas por su trayectoria de participación en las elecciones. Resultan perfiles de personas, como pide la convocatoria. Hay unas 1,500 celdas, manejables.
(c) **Cohortes de nacimiento** (seguir un grupo de edad hacia adelante a lo largo de las elecciones). Es lo más original y más trabajo, y exige validar el avance de 3 años por elección.
*Recomendación:* (b), con las secciones de (a) usadas solo para ubicar y mapear cada perfil en el territorio.

**D3. Dependencias.** La constitución dice «solo Python con Polars», pero k-means normalmente se hace con scikit-learn.
(a) Permitir scikit-learn y enmendar el art. 1. (b) Programar k-means con Polars y NumPy. (c) Permitir solo las librerías de gráficos y modelado que se declaren aquí.
*Recomendación:* (a), enmendando la constitución por escrito, pues reimplementar k-means añade riesgo sin valor.

**D4. Tipo de elección.**
(a) Expresar la participación de cada unidad como diferencia contra el promedio nacional de esa elección. (b) Separar presidenciales e intermedias en dos variables. (c) Usar valores absolutos y dejar que el método lo absorba.
*Recomendación:* (a) y reportar además (b) como análisis de apoyo.

**D5. Escolaridad** (la convocatoria la sugiere «cuando esté disponible»).
(a) Omitirla y declararlo como limitación. (b) Cruzar con el Censo de INEGI, lo que exige una tabla de equivalencias entre claves municipales de INE e INEGI y más días de trabajo.
*Recomendación:* (a), y mencionarlo como línea futura.

**D6. Edades atípicas.** Top-codificar a partir de cierta edad (por ejemplo 90 o más) o descartar por encima de un tope.
*Recomendación:* agrupar en «90+» y reportar cuántas personas se afectan.

**D7. Unidades pequeñas.** Umbral mínimo de lista nominal para incluir una unidad (por ejemplo 100 personas) y tratamiento de las que no lo cumplan.
*Recomendación:* excluir bajo el umbral y reportarlas aparte.

**D8. Año 2024.** (a) Buscar los datos en la plataforma del INE o pedirlos a las personas contacto. (b) Trabajar solo con 2009-2021 y declararlo.
*Recomendación:* (a) con tope de un día; si no aparece, (b).

**D9. Condiciones del equipo (urgente).** Confirmar que el equipo está registrado, que es paritario, y quién es la persona representante. La base DÉCIMO PRIMERA indica que la carta de cesión debía **anexarse al formato de registro** (que cerró el 15 de octubre): confirmar que se anexó. Además la carta sigue siendo requisito del envío final (RE-05). Confirmar quién coordina las firmas de las dos cartas y recogerlas desde ya.

**D10. Repositorio.** La carpeta de trabajo no es un repositorio git. Opciones: (a) crear uno local y subirlo a un repositorio privado o público, (b) entregar el código dentro del `.zip`.
*Recomendación:* (a) y además incluir el código en el `.zip`, para que la entrega no dependa de un enlace.

**D11. Persistencia y datos de trabajo.** Dónde viven los datos intermedios (Drive del equipo o carpeta local) y si se monta Drive en Colab, lo que requiere autorización interactiva de la persona usuaria.
*Recomendación:* guardar en Parquet en una carpeta de Drive del equipo.

**D12. Pruebas automatizadas.** No existen pruebas ni `pytest` en el proyecto. Opciones: (a) añadir pruebas con `pytest` para las funciones puras (indicadores, limpieza, validaciones); (b) usar solo verificaciones dentro del propio flujo.
*Recomendación:* (a), lo que también obliga a ampliar la constitución (D3).

**D13. Tamaño del envío.** Se envía por correo, y los límites de adjuntos pueden ser pequeños. Definir un tope del `.zip` y qué hacer si se supera. No se ha confirmado ningún límite.
*Recomendación:* mantener el paquete por debajo de unos 20 MB y consultar a las personas contacto del INE si se necesita más.

**D14. Regionalización.** Usar la entidad (32) como «región» o agrupar las entidades en un número menor de regiones (por ejemplo, 5 o 6). Con 32 entidades hay cerca de 1,900 celdas; con regiones, menos y más estables.
*Recomendación:* empezar con entidad y agrupar solo si los perfiles salen inestables.

**D15. Apéndices y límite de cuartillas.** La convocatoria pide 8 a 12 cuartillas y no dice si los anexos cuentan. (a) El apéndice cuenta dentro de las 12. (b) La tabla de calidad y el detalle metodológico van en el repositorio y el `.zip`, fuera del PDF.
*Recomendación:* (b), para no arriesgar la descalificación por exceso de extensión.

**D16. Referencia de la participación relativa** (surgió el 2026-10-24 al ejecutar la segmentación; enmienda D4).
Con la referencia nacional (D4a), la entidad explica 74 % de la varianza de `brecha` y 76 % de la de `tendencia`, y 10 de 32 entidades tienen más de 80 % de su lista en un solo perfil: los perfiles se parecen a etiquetas de estado. (a) Mantener D4a como principal y reportar la variante como apoyo. (b) Medir cada celda contra la tasa de su propia entidad en cada elección. (c) Presentar ambas.
**Resuelta el 2026-10-24: (b).** La referencia nacional se conserva como análisis de apoyo (`entrega/tablas/sensibilidad_nacional/`). Con (b), k = 5 y ninguna entidad supera 80 % en un perfil. Hipótesis sin verificar: la brecha refleja elecciones locales concurrentes.
