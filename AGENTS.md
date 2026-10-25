# Guía para agentes

## Propósito del proyecto



## Estructura


## Constitución y especificación activa

- Lee `docs/constitution.md` y la spec activa (`specs/NNN-*/`) antes de tocar código.
- La spec activa manda: no implementes cambios de código si no existe o si no cubre el cambio solicitado. Si falta una decisión, detente y pregunta antes de implementar.
- Para localizar los documentos desde la raíz del proyecto:

```powershell
Get-Content docs/constitution.md
Get-ChildItem specs -Directory -Filter '???-*'
```

Identifica la spec activa y lee sus archivos antes de modificar código.

## Desarrollo y validación



## Memoria de trabajo

- Al iniciar una tarea, lee `MEMORY.md` para conocer el estado, decisiones y riesgos vigentes.
- Al terminar un cambio que aporte contexto duradero, actualiza `MEMORY.md` con el estado actual, decisiones relevantes y errores a evitar.
- Mantenlo por debajo de ~50 líneas: resume o elimina información obsoleta.
- No incluyas claves, tokens, credenciales, datos personales ni transcripciones en la memoria.
- Si una indicación se vuelve permanente, propón moverla a este archivo en lugar de mantenerla solo en `MEMORY.md`.
- Conserva el contenido ajeno a la tarea; no reemplaces decisiones existentes sin verificar que ya no aplican.

## Ejecución local


## Reglas importantes

- No incluyas archivos `.env`, claves de IA, contraseñas, URLs con credenciales ni transcripciones reales en el repositorio, logs o respuestas.
- Evita cambios de esquema incompatibles

## Límites
- Siempre: respetar las reglas, y mantener los textos en español 
- Pregunta antes: crear archivos nuevos, cambiar el formado de los datos guardados 
- Nunca: añadir dependencias, frameworks o un paso de build

<!-- antislop:start -->
## antislop
For code comments work, read the core `.agents/skills/antislop/SKILL.md` and then the skill for the task:
- Code comments: `.agents/skills/antislop-code/SKILL.md`
Before starting, follow the core's "Two Usage Modes" section in strict order: explicit session instruction first, then global preference, then ask. A session instruction always wins. For a resolved mode, say `antislop active: <mode> (session override).` or `antislop active: <mode> (global preference).` once before presenting findings or making edits, using the actual mode and source.
<!-- antislop:end -->
