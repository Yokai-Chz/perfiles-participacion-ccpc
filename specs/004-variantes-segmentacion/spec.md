# 004 · Variantes de segmentación candidatas a corrida principal

**Estado:** aprobada (2026-10-28)

> Aprobada el 2026-10-28: la persona responsable pidió que las variantes sean candidatas a reemplazar la principal, autorizó seaborn y kmodes (enmienda del art. 1), un módulo nuevo `src/experimentos.py` y la tasa absoluta solo como descriptor.
**Fecha:** 2026-10-28
**Fecha límite de entrega:** 2026-10-31, 18:00 (envío). Documentos cerrados el 2026-10-29.
**Extiende:** specs 001, 002 y 003. Puede cambiar la corrida principal de la 001 (RF-07, RF-08) si se cumple D4.

## 1. Contexto y objetivo

La corrida principal (k-means ponderado por lista nominal sobre nivel, brecha y tendencia; k = 5) tiene silhouette 0.24 y baja coincidencia con Ward y con la mezcla gaussiana (ARI 0.37 y 0.26). Los perfiles parten un continuo. El equipo quiere probar si rasgos ampliados, una distancia que incluya sexo, edad y tipo de sección, un consenso de métodos o una mezcla gaussiana con probabilidades dan perfiles más robustos y más fáciles de narrar.

## 2. Alcance

**Incluye:** seis variantes (tabla de RF-02); métricas comunes; probabilidades de pertenencia; centroides, composición demográfica y tasa absoluta de cada perfil; radar y mapa de calor de centroides; regla para sugerir nombres; compuerta de decisión (D4).

**No incluye:** cambiar la referencia por entidad (D16b de la 001); datos individuales; nuevas fuentes de datos.

## 3. Requisitos funcionales

- **RF-01 Rasgos base.** Toda variante parte de nivel, brecha, tendencia y volatilidad de cada celda (D1).
- **RF-02 Variantes.**

| Id | Rasgos | Algoritmo | Pesos por lista nominal |
|---|---|---|---|
| `km4` | 4 rasgos base | k-means | sí |
| `pca_r` | componentes principales de los 6 valores de participación relativa (90 % de varianza) y volatilidad | k-means | sí |
| `gower` | 4 rasgos, edad ordinal, sexo y tipo de sección | k-medoides sobre distancia de Gower | sí |
| `kproto` | 4 rasgos y edad estandarizados, sexo y tipo de sección | K-Prototypes | sí |
| `consenso` | 4 rasgos | co-asociación de 100 k-means, 100 Ward y 100 mezclas gaussianas sobre submuestras | por submuestreo proporcional a la lista nominal |
| `gmm` | 4 rasgos | mezcla gaussiana de covarianza completa | por remuestreo proporcional a la lista nominal |

- **RF-03 Selección de k.** Cada variante elige k entre 4 y 6 con el criterio de la 001 (estabilidad y silhouette), salvo el consenso, que usa k = 5.
- **RF-04 Métricas.** Para cada variante: silhouette, Davies-Bouldin y Calinski-Harabasz en el espacio común (D2); ARI medio entre semillas y en submuestras; ARI frente a la principal; porcentaje de lista nominal del perfil más chico.
- **RF-05 Continuo.** Se reporta el PAC del consenso (pares con co-asociación entre 0.1 y 0.9) y el porcentaje de lista nominal con probabilidad máxima menor a 0.6 en la mezcla gaussiana.
- **RF-06 Descripción.** Para cada variante: centroides ponderados en z-score, composición por sexo, tipo de sección y edad, y tasa absoluta de participación por elección (descriptor, D6).
- **RF-07 Gráficas.** Radar de centroides (un panel por perfil, misma escala) y mapa de calor con los valores.
- **RF-08 Nombres.** Regla reproducible que sugiere un nombre por perfil a partir de edad, tipo de sección y centroides (D7). Los nombres finales los valida el equipo.
- **RF-09 Sensibilidad de Gower.** Se reporta el ARI de la variante `gower` con peso del bloque categórico 0.5, 1 y 2 (D5).
- **RF-10 Arquetipos (ampliación del 2026-10-28).** Se ajustan arquetipos ponderados por lista nominal sobre el z-score de los 4 rasgos base. Se reportan sus coordenadas, la mezcla de cada celda, la mezcla media de cada perfil de la corrida principal y la de cada sección de 2024 (D8 a D10).
- **RF-11 Estabilidad de los arquetipos.** Se ajusta sobre 10 submuestras del 80 % y se reporta la distancia media, en z, entre cada arquetipo y su pareja, emparejados con el algoritmo húngaro.

## 4. Requisitos no funcionales

- **RNF-01** Dependencias nuevas solo las de la enmienda del art. 1 del 2026-10-28.
- **RNF-02** Mientras no se cumpla D4, la corrida principal no cambia: tablas iguales a las del commit `295b573`.
- **RNF-03** Reproducibilidad: dos corridas seguidas dan tablas idénticas byte a byte.
- **RNF-04** Toda cifra publicada sale de una tabla en `entrega/tablas/`.

## 5. Criterios de finalización

- Tablas de RF-04 a RF-09 en `entrega/tablas/experimentos/`.
- Pruebas nuevas para Gower, k-medoides, consenso, mezcla gaussiana, métricas y nombres; todas las pruebas pasan.
- Resultado de la compuerta D4 registrado en `MEMORY.md`.

## 6. Decisiones (resueltas el 2026-10-28)

**D1. Volatilidad.** Rasgo fijo en todas las variantes. Por eso el espacio de evaluación tiene 4 dimensiones.

**D2. Espacio común.** Las métricas se calculan siempre sobre el z-score de los 4 rasgos base, aunque la variante agrupe en otro espacio. Comparar silhouette entre espacios distintos no es válido.

**D3. Variables demográficas.** Edad como ordinal (grupo 0 a 14), sexo y tipo de sección como categóricas.

**D4. Compuerta para reemplazar la principal.** Una variante reemplaza a la principal solo si cumple todo lo siguiente: (1) ARI medio ≥ 0.80 entre semillas y en submuestras; (2) en el espacio común, silhouette mayor o igual y Davies-Bouldin menor o igual que la principal actual medida en ese mismo espacio; (3) el perfil más chico tiene al menos 5 % de la lista nominal; (4) el equipo valida que los nombres se pueden explicar. Si varias cumplen, gana la de mayor silhouette. Si ninguna, las variantes quedan como apoyo.

**D5. Circularidad.** Si sexo, edad o tipo de sección entran en la distancia, la composición demográfica de los perfiles es en parte resultado del diseño. Se declara en el documento y se mide la sensibilidad al peso del bloque categórico.

**D6. Tasa absoluta.** Solo describe a los perfiles; no entra en ninguna distancia, para respetar D16b de la 001.

**D7. Nombres.** Edad + tipo de sección + comportamiento. Edad: «Jóvenes» si al menos 60 % de la lista del perfil tiene menos de 35 años, «Mayores» si al menos 60 % tiene 60 o más, «Adultez» en otro caso. Tipo de sección solo si uno reúne al menos 60 %. Comportamiento: el rasgo con mayor |z| y el segundo si |z| ≥ 0.5. Sin términos estigmatizantes.

**D8. Número de arquetipos.** Se prueban de 3 a 6 y se elige el codo: el k donde más cae la mejora marginal de la varianza explicada. *Cambio declarado (2026-10-28, después de ver los datos):* la regla original («el menor k que mejora menos de 3 puntos frente a k + 1») no se cumplía en ningún k del rango (la mejora pasa de 17 puntos a unos 5 entre 3 y 4 arquetipos y luego baja poco a poco). La persona responsable eligió el codo, que da k = 4.

**D11. Celdas ancla.** Solo las celdas con lista nominal media de 5,000 o más (por encima del cuartil inferior) pueden formar un arquetipo; todas las celdas reciben su mezcla. Sin esta restricción, dos de los seis arquetipos quedaban anclados al 100 % en una sola celda chica de personas de 80 años o más. Decidido el 2026-10-28, después de ver los datos.

**D9. Papel de los arquetipos.** Lectura complementaria: no pasa por la compuerta D4 ni cambia la corrida principal. Va un párrafo en la sección 3.6 del documento.

**D10. Límites declarados.** Los arquetipos son polos y no grupos de personas: casi ninguna celda es 100 % de uno. Son sensibles a celdas atípicas, por eso se reportan las celdas que más pesan en cada arquetipo.
