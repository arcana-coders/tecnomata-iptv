# Progreso de películas y episodios

Cada película y cada episodio conserva posición, pista de audio, pista de
subtítulos (incluido Desactivados) y tamaño de subtítulos. Se retoma automáticamente
al abrir desde catálogo, favoritos o recientes. No hay un único punto global.
La TV en vivo no guarda posición: usa Ir al directo.

`LibraryStore` añade la tabla `progress` a la biblioteca SQLite existente sin
recrear ni borrar favoritos/recientes. Clave: cuenta (hash servidor+usuario),
tipo vod/episode, ID del contenido y serie padre. Dos episodios con el mismo ID
de diferentes series quedan separados. Cambiar contraseña mantiene biblioteca;
cambiar/olvidar cuenta aísla/oculta sus datos. El progreso no se elimina con el
límite de los últimos 100 del historial.

Se guarda cada cinco segundos y al pausar, detener, cambiar contenido, cambiar
pistas/tamaño o cerrar. Un cierre abrupto puede perder aproximadamente los últimos
cinco segundos desde el último guardado. No se escribe antes de file-loaded ni
sin duración/posición válidas. El EOF normal marca terminado con posición cero,
conservando preferencias; volver a abrir empieza desde el inicio. No se usa un
porcentaje para declarar terminada una película que el usuario dejó a medias.

La restauración espera duración y metadatos. Aplica pistas por ID y descriptores
idioma/códec/título; si los IDs cambian, acepta una coincidencia descriptiva única.
Si la pista desaparece o queda ambigua, mantiene la selección del motor.
Aplica tamaño y seek exacto, y espera confirmar posición antes de sobrescribir
el punto guardado. Un fallo de carga/seek, o contenido sin seek, conserva el punto
y muestra aviso; Desde inicio permite abandonar ese punto y empezar de nuevo.
El botón está en la barra externa que se muestra al pulsar el video VOD/episodio.

Archivo: `$XDG_DATA_HOME/tecnomata-iptv/library.sqlite3` (por defecto
`~/.local/share/tecnomata-iptv/library.sqlite3`), permisos 600. Sólo IDs, posición,
duración, preferencias, estado y fecha; nunca URL del stream, usuario ni contraseña.
`progress.py` resuelve pistas; `app.py` coordina checkpoints/restauración en GUI.

Validación: 62 pruebas automatizadas, incluyendo migración aditiva, cuentas,
dos películas/dos episodios, historial podado, fallo de carga/seek y EOF.
`scripts/smoke_progress.py` prueba libmpv nativo con dos audios/dos subtítulos locales:
dos películas y dos episodios retoman posiciones y preferencias distintas después
de cerrar/reabrir ventana y SQLite. No se valida con el proveedor en esta entrega.

La versión ya abierta anteriormente no puede guardar retroactivamente su posición.
La función se activa al cerrar/reabrir la app actualizada; no reiniciar por sorpresa
la película que Arturo está viendo.

Padres: [README](../README.md), [arquitectura](architecture.md),
[sesión](SESSION.md) y [contrato](plan.md).
