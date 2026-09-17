# Fondos por tema — versión 2

Doce imágenes raster locales, distintas para TV, cine y series en cada tema.
Son ejemplos decorativos; no representan el catálogo ni identifican el contenido
que reproduce el usuario. Un cuadro real de reproducción tiene prioridad.

| Tema | TV | Cine | Series |
|---|---|---|---|
| Springfield | Set deportivo cartoon | Proyector, palomitas y dona | Dragón y trono cartoon |
| Mcfly | Set deportivo con acero/circuitos | Controles del DeLorean | Dragón/trono con electricidad/circuitos |
| Retro | Set deportivo neón | Videoclub VHS/casetes | Diner de drama criminal noventero |
| Dog Eyes | Set deportivo B/N | Proyector noir | Diner criminal B/N |

Archivos vigentes: `<tema>-tv-v2.png`, `<tema>-movies-v2.png` y
`<tema>-series-v2.png`. Generador: image_gen nativo de Codex; fallback elegido
tras el resultado agy genérico rechazado en el trabajo visual previo.
[Prompts finales exactos](theme-prompts-v2.json). Enfoque vertical con sujeto
centrado y parte inferior disponible para etiquetas Qt. Sin logos ni actores.
Los PNG previos Springfield quedan como histórico; no se cargan en el tema actual.

Doce PNG de 1024 × 1536 verificados, escenas y recorte revisados con datos ficticios; el wheel incluye
recursos como package-data. Preview sólo en RAM; Dog Eyes desatura miniaturas,
sin modificar video. Dona y botones son Qt nativos.

Padres: [diseño](../../../../docs/design.md) y [README](../../../../README.md).
