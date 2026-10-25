# Guía SDD: plan

Entrada: nombre `NNN-nombre`.

Lee `AGENTS.md`, `MEMORY.md`, `docs/constitution.md` y la spec. Exige `Estado: aprobada` y ninguna duda abierta. Inspecciona código y pruebas existentes antes de redactar el plan. Solicita autorización antes de crear `plan.md`.

Incluye archivos y responsabilidades, flujo o pseudocódigo, interfaz cuando aplique, compatibilidad de datos y decisiones con alternativas consideradas. Agrega una matriz de trazabilidad: cada RF → cambio previsto → prueba automatizada existente o nueva → comprobación manual concreta si aplica. Señala explícitamente toda laguna de cobertura. Para Python, prevé pruebas afectadas o `python -m pytest tests`; para frontend, `npm run lint` y `npm run build`. No inventes pruebas ni conviertas inspección visual en cobertura automatizada. Presenta el plan para aprobación junto con las tareas.
