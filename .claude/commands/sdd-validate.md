# Guía SDD: validación

Entrada: nombre `NNN-nombre`.

Lee `spec.md`, `plan.md`, `tasks.md`, constitución y diff. Recorre cada RF y criterio de finalización. Ejecuta desde `backend/` pruebas afectadas o `python -m pytest tests` para lógica Python; si la caché falla por permisos, usa `-p no:cacheprovider`. Ejecuta `npm run lint` y `npm run build` desde `frontend/` para frontend. No instales dependencias y registra resultados reales o impedimentos.

Separa evidencia automatizada de comprobaciones manuales de interfaz. Chrome DevTools MCP es opcional; úsalo solo si está configurado y accesible, con Google Chrome o Chrome for Testing, incluida una vista móvil. Si no está disponible, indícalo. No atribuyas cobertura automatizada a una revisión visual. Devuelve `VEREDICTO: APROBADO` o `VEREDICTO: CAMBIOS NECESARIOS`, con incumplimientos concretos por archivo, línea y RF. Una prueba fallida o dependencia ausente bloquea la aprobación.
