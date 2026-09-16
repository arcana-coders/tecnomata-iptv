# Fondos Springfield

Fondos ilustrativos originales locales con referencias visuales al gusto de
Arturo por Los Simpson: sofá cálido, dona rosa, cielo azul, paleta amarilla y
contornos de cartoon. No son portadas reales del catálogo.

- springfield-tv: sofá, dona y televisor de deportes.
- springfield-movies: autocine al atardecer y dona/popcorn.
- springfield-series: casa y jardín con dona decorativa.

Generación: image_gen nativa de Codex, [prompts finales exactos](prompts.json).
Antigravity produjo personajes genéricos (rechazado por calidad). Image_gen
rechazó solicitud de personajes (moderation_blocked, categoría other; no informó
más detalle). Se usó alternativa original de ambientes/objetos sin personajes.
Tres PNG de 1536 × 1024; composición revisada en las tarjetas reales con datos ficticios.
Los assets se empaquetan como package-data y cargan con QPixmap al arrancar;
preview del video tiene prioridad y sólo vive en RAM. DonutBadge es Qt nativo.

Padres: [diseño](../../../../docs/design.md) y [README](../../../../README.md).
