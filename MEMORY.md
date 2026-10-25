# MEMORY.md 

## Estado y decisiones duraderas
- 2026-10-24: spec 001 aprobada con todas las recomendaciones D1–D15. Constitución art. 1 enmendado: Python + Polars + scikit-learn + pytest.
- Equipo registrado y paritario; carta de cesión anexada (D9). Falta recoger firmas de las dos cartas (límite interno 10-28).
- D8 resuelta: el Drive ya trae 2024 (192 CSV = 6 elecciones × 32 entidades). Usar 6 elecciones; 2024 es presidencial. Ya no hace falta escribir al INE por 2024.
- Prueba 10-24 (ags, cdmx, col × 6 años): esquema idéntico de 16 columnas y LN=SV+NV+NS sin fallas. NS varía mucho (Ags 2009 ≈10 % de LN, Ags 2012 ≈0). CDMX ≈800 mil filas por elección. Falta verificar las otras 29 entidades.
- Texto de la convocatoria en `convocatoria.md` (el PDF no se puede leer sin librerías).
- Calendario: ingesta+calidad 10-25 · segmentación 10-26/27 · perfiles 10-28 · documentos 10-29 · revisión y .zip 10-30 · envío antes de 10-31 18:00.

- 10-25: spec 002 aprobada (D1 a D7 con su recomendación + RF-16). Corridas en `analisis.CORRIDAS`: principal intacta (k=5, mismas tablas que d48acaf más columna `volatilidad`); apoyo: nacional (k=4), sin NS > 25 % (k=5, ARI 0.93), con volatilidad (k=4, ARI 0.44), por circunscripción INE/CG130/2023 (k=5, ARI 0.32). Ward y mezcla gaussiana: ARI 0.37 y 0.26; silhouette 0.24: perfiles = partición de un continuo, declararlo.
- 10-25: distritos federales 2009-2021 vienen en marco 2021 (secciones no cambian de DEF); 2024 en marco 2023. Trayectoria con marco 2021 por equivalencia de sección; 2,775 secciones nuevas de 2024 (5.3 % de LN) sin distrito. Primer voto: +3.4 pp a los 18, -9.6 pp tres años después.
- 10-25: las tablas se escriben con 12 cifras significativas y orden fijo; dos corridas dan CSV idénticos byte a byte. Figuras de apoyo en `entrega/estadisticas/` (19). Entrega pesa 11 MB.
- 10-25: se trabaja en Fedora. Los 192 CSV están en `datasets/` (ignorada por git). Entorno `src/.venv` con Python 3.12.5 de pyenv; numpy 2.2.6 no tiene versión para 3.14. Notebook completo en unos 45 s.
- 10-25 (D17): los entregables usan Liberation Sans (sistema, medidas de Arial); ruta en `configuracion.ARCHIVOS_FUENTE`. RE-01 pide Arial o Calibri: riesgo declarado.
- 10-24: Colab falló por cuota de gdown. Autorizado por el usuario el 10-24 usar matplotlib, reportlab, python-pptx, pypdf y nbconvert además del art. 1.
- 10-24: la lógica está en módulos `src/*.py`; un solo notebook `src/reto1_perfiles_participacion.ipynb` los llama y lo explica. 48 pruebas en `src/tests/` pasan. Antislop y antislop-code activos (sin rayas largas, sin cifras sin tabla, sin scripts generadores en el repo).
- D16 resuelta (b) el 10-24 y registrada en la spec: participación relativa contra la propia entidad. Corrida principal k=5; la referencia nacional (k=4, 10 entidades dominadas por un perfil) queda en `entrega/tablas/sensibilidad_nacional/`.
- Entregables generados el 10-24 como borrador: `entrega/documento_tecnico.pdf` (10 págs.), `entrega/fichas/` (5 PNG 300 ppp), `entrega/presentacion_ejecutiva.pptx` (10 diap.). Nombres y estrategias en `src/contenido.py`, pendientes de validar por el equipo. Estado por requisito en `entrega/lista_verificacion.md`.
- Faltan: nombre del equipo (marcador `[NOMBRE DEL EQUIPO]`), cartas firmadas, `.zip`, contraste con plataforma CCPC. D10 resuelta el 10-24: repo git local (rama main) y remoto privado https://github.com/Yokai-Chz/perfiles-participacion-ccpc. `.gitignore` excluye CSV, Parquet, .venv, markitdown y *.zip.

## Validación y errores a evitar
- El pivote de Polars no fija el orden de filas ni columnas y `fill_null(0.0)` sobre todo el pivote vuelve decimal la clave: ordenar y rellenar solo las columnas de valores.
- Reportlab declara Helvetica aunque no la use: verificar la fuente con los spans de texto (pymupdf), no con los recursos del PDF.
- Desempatar siempre los órdenes (p. ej. entidades con el mismo índice) para que las tablas no cambien entre corridas.
- La edad modal se calcula por grupo completo (mediana), no por la celda más grande.
- La herramienta colab-mcp corta celdas a los 30 s sin salida (`.mcp.json` timeout 30000); dividir celdas o emitir progreso.
- Verificar en la ingesta: esquema en 32 entidades, LN=SV+NV+NS nacional, filas por elección.
