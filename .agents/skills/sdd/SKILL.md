---
name: sdd
description: Úsala para redactar, revisar, planificar, implementar o validar specs de QA Callcenter bajo docs/constitution.md y specs/.
---

# Desarrollo dirigido por especificaciones

## Flujo

Constitución → spec → clarificación → plan → tareas → implementación → validación → cambio.

- La spec y el plan con tareas requieren aprobación explícita del usuario antes de avanzar. Las instrucciones explícitas del usuario prevalecen sobre esta guía.
- La spec manda: si algo no está en la spec, no se implementa. Si falta una decisión, para y pregunta.
- Un cambio de requisitos se hace primero en la spec, luego en el plan y las tareas, por último en el código.
- Cada spec vive en su carpeta: `specs/NNN-nombre/` con `spec.md`, `plan.md` y `tasks.md`.
- Al terminar cada fase, actualiza `MEMORY.md`

Lee `AGENTS.md`, `MEMORY.md` y `docs/constitution.md` al iniciar. Antes de tocar código, identifica y lee la spec activa. Pide autorización antes de crear archivos nuevos o cambiar el formato de los datos guardados. Para una fase concreta, consulta la guía correspondiente en `.codex/commands/`: `sdd-constitution`, `sdd-spec`, `sdd-clarify`, `sdd-plan`, `sdd-tasks`, `sdd-implement`, `sdd-validate`, `sdd-change` o `sdd-status` (archivos `.md`). Son guías de la skill, no comandos de barra registrados por Codex.

```
# Spec NNN — <Nombre>
Estado: borrador | aprobada | implementada
## Contexto y objetivo
## Usuarios
## Historias de usuario - HU-1. Como <rol>, quiero <acción> para <beneficio>.
## Definiciones (solo si hay términos que puedan interpretarse de varias formas)
## Requisitos funcionales
## Requisitos no funcionales
## Casos límite
## Fuera de alcance
## Criterios de finalización
## Dudas abiertas
- [NECESITA ACLARACIÓN] <duda>
```
La spec describe el QUÉ y el POR QUÉ. Nada de stack, arquitectura ni nombres de archivos.

## Requisitos en EARS (en español)
- RF-x: CUANDO <evento>, EL SISTEMA <respuesta>.
- RF-x: SI <condición no deseada>, ENTONCES EL SISTEMA <respuesta>.
- RF-x: MIENTRAS <estado>, EL SISTEMA <respuesta>.
- RF-x: EL SISTEMA <comportamiento permanente>.

Cada RF debe ser verificable: nada de "rápido", "intenso" o "bonito" sin un criterio
medible.

## Plan (plan.md)
Antes de redactarlo, inspecciona el código y las pruebas existentes relacionados con cada requisito. Describe archivos y responsabilidades, flujo o pseudocódigo cuando ayude, interfaz si corresponde y decisiones justificadas con alternativas consideradas. Vincula cada RF a la implementación y a una validación concreta: prueba automatizada, comprobación manual de interfaz o ambas. Señala los RF sin cobertura; una inspección visual no cuenta como prueba automatizada. Si la spec tiene dudas abiertas o no está aprobada, detente.

## Tareas (tasks.md)
```
- [ ] **Tn. <Descripción>.** RF-x, RF-y
 - Hecho cuando: <comprobación verificable>.
```
Máximo 20-30 min por tarea, en orden de dependencia. Si salen más de 10, propón dividir
la spec.

## Implementación y validación
Una tarea aprobada a la vez. Para lógica Python, agrega o ajusta pruebas de comportamiento y comprueba el fallo antes del cambio cuando sea práctico. Después ejecuta desde `backend/` las pruebas afectadas o `python -m pytest tests`; si la caché está bloqueada, usa `python -m pytest tests -p no:cacheprovider`. Para frontend, ejecuta desde `frontend/` `npm run lint` y `npm run build`. No agregues pruebas que solo reproduzcan la implementación o para cambios de documentación. Si falla una prueba o falta una dependencia de pruebas, detente, informa el impedimento y no instales paquetes.

Registra los comandos y resultados reales. Separa evidencia automatizada de comprobaciones manuales de interfaz. Chrome DevTools MCP es opcional: úsalo solo si está configurado y accesible, preferentemente con Google Chrome o Chrome for Testing, incluida una vista móvil; si no está disponible, registra la limitación. El revisor evalúa cada RF y criterio de finalización, y no aprueba los que carecen de evidencia suficiente.
