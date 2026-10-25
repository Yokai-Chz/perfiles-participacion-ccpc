# Lista de verificación de entrega

Estado al 2026-10-24. «Hecho» significa generado y comprobado por código (`python -m pytest src/tests`); «Falta» requiere al equipo.

| Req. | Entregable | Estado | Cómo se comprobó o qué falta |
|---|---|---|---|
| RE-01 | Documento técnico PDF | Hecho (borrador) | `entrega/documento_tecnico.pdf`: 10 páginas, texto en Arial, cuerpo en 11 pt con interlineado de 16.5 pt (1.5). Las tablas van en 10 pt. Falta el nombre del equipo (`[NOMBRE DEL EQUIPO]`) y la revisión del equipo. |
| RE-02 | Fichas de perfil | Hecho (borrador) | `entrega/fichas/ficha_perfil_1.png` a `_5.png`, A4 a 300 ppp. Falta el nombre del equipo. |
| RE-03 | Presentación ejecutiva | Hecho (borrador) | `entrega/presentacion_ejecutiva.pptx`: 10 diapositivas. Falta el nombre del equipo. |
| RE-04 | Código | Hecho | `src/` con 35 pruebas y `README.md`. Repositorio privado en https://github.com/Yokai-Chz/perfiles-participacion-ccpc (D10); si el enlace debe verlo el INE, hay que hacerlo público o dar acceso. El código también va en el `.zip`. |
| RE-05 | Carta de cesión de derechos | Falta | Firmas de todas las personas integrantes (límite interno 10-28). |
| RE-06 | Carta de decir verdad | Falta | Firmas de todas las personas integrantes (límite interno 10-28). |
| RE-07 | Paquete `.zip` | Falta | Nombre del equipo y eje; solo por correo a las dos direcciones de la convocatoria, antes del 10-31 a las 18:00. Tope sugerido: 20 MB (D13). |
| RE-08 | Condiciones del equipo | Por confirmar | Paridad, registro y representante con cuenta bancaria mexicana. |

## Pendientes de contenido
- Revisión de nombres y estrategias por el equipo y las áreas del INE (borrador).
- Contraste de la participación nacional con la plataforma CCPC (RF-15, manual).
- Revisión externa: una persona ajena ejecuta el notebook y lee los perfiles sin explicación.
- Si el PDF pasa de 12 páginas al editar, mover detalle metodológico al repositorio (D15b).

## Antislop: Delivery Gate aplicado a fichas, documento y presentación
- Sin rayas largas en ningún texto: comprobado por prueba automática.
- Sin logotipos, íconos ni personas inventadas; el nombre del equipo es un marcador visible.
- Sin cifras sin respaldo: todas salen de `entrega/tablas/` (`contenido.py` las calcula).
- Sin lenguaje de marketing ni llamadas a la acción genéricas.
- Colores de las gráficas: primeras cinco posiciones de la paleta categórica validada, orden fijo, leyenda siempre presente.
- Nombres y estrategias marcados como «borrador para revisión del equipo».
