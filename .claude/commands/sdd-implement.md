# Guía SDD: implementación

Entrada: nombre `NNN-nombre` y tarea `Tn`.

Lee la spec, el plan y las tareas aprobadas, más `AGENTS.md`, `MEMORY.md` y `docs/constitution.md`. Implementa solo la tarea indicada. Para lógica Python, agrega o ajusta pruebas de comportamiento y comprueba el fallo antes del cambio cuando sea práctico. Ejecuta desde `backend/` pruebas afectadas o `python -m pytest tests`; si la caché está bloqueada, usa `python -m pytest tests -p no:cacheprovider`. Para frontend, ejecuta desde `frontend/` `npm run lint` y `npm run build`. No instales dependencias de prueba. Si falla una prueba o falta una dependencia, detente y no marques la tarea.

Registra comandos y resultados reales, archivos modificados, RF cubiertos y comprobaciones manuales. Marca `Tn` solo tras validar. Solicita autorización antes de crear archivos o cambiar el formato de datos guardados.
