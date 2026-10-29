# Constitución del proyecto

1. **Stack simple.** Usamos Python con Polars. Enmienda 2026-10-24 (D3, D12): se permiten además scikit-learn (segmentación) y pytest (pruebas); cualquier otra dependencia requiere decisión explícita. Enmienda 2026-10-28 (spec 004): se permiten seaborn (gráficas), kmodes (K-Prototypes) y el uso directo de SciPy, que ya llegaba con scikit-learn.
2. **La spec manda.** Ningún cambio de código se implementa sin una spec activa en `specs/NNN-*/` que lo cubra; si falta una decisión, se detiene el trabajo y se pregunta.
6. **Idioma consistente.** Textos visibles, comentarios y documentación van en español; los identificadores siguen la convención del módulo.