# Guía SDD: cambio de requisitos

Entrada: nombre `NNN-nombre` y cambio solicitado.

Lee la spec y la petición. Modifica primero solo `spec.md`: RF afectados en lenguaje verificable, casos límite y alcance. Muestra el diff y solicita aprobación explícita. Después actualiza `plan.md` y `tasks.md`, inspeccionando código y pruebas pertinentes y reconstruyendo la trazabilidad RF → implementación → validación. Solicita aprobación del plan y tareas antes de cambiar código. Pide autorización antes de crear archivos o cambiar el formato de datos guardados.
