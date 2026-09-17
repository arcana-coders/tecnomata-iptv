# Contexto operativo — Tecnomata IPTV

Leer `README.md`, `docs/SESSION.md` y `docs/plan.md` antes de trabajar.
Repo privado Gitea arturo/tecnomata-iptv; remoto gitea, rama main. Push explícito
autorizado por Arturo para respaldar el avance mientras prueba la app.
Instalación desde clone limpio en docs/install-fedora.md.
Este repo contiene una app personal Linux autorizada por Arturo; avanzar por fases
con evidencia y dejar punto de reanudación. Qt/PySide6 + python-mpv + libmpv,
con API Xtream para TV, películas y series. No se busca equivalencia completa ni
copiar recursos de Smarters.

Comandos: `./scripts/run.sh`, `.venv/bin/pytest -q` y prueba gráfica documentada en
`docs/SESSION.md`. Entorno real de arranque: Fedora 44 / Hyprland / Wayland.

Nunca imprimir secretos, URLs autenticadas ni excepciones HTTP crudas. La cuenta
se captura en el formulario y puede guardarse en Secret Service de Linux mediante
`AccountStore` (servicio tecnomata-iptv / identidad default-account). No usar
fallbacks de archivo. Restauración/auth automáticas y Olvidar cuenta implementados.
Pruebas con
`example.invalid`, MockTransport y videos locales; no tocar credenciales de
IPTVnator. `CatalogCache` es por cuenta y sesión: precargar categorías/listas de
live/vod/series en segundo plano, reutilizar al entrar/cambiar categoría y cachear
episodios. Actualizar listas/cambiar/olvidar cuenta invalidan el caché.
No bloquear navegación/reproducción por la precarga. Pruebas GUI de caché/cuenta:
`QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q` (51 pruebas actualmente).

Cerrar trabajo actualizando `docs/SESSION.md`, el índice y desarrollo en
`../asistente/projects/tecnomata-iptv/`, más `../asistente/journal.md`.
No marcar una fase como validada con el proveedor si únicamente hay pruebas
simuladas. Arturo confirma playback real de TV/cambios, película y serie.
Precarga/cuenta recordada tienen 33 pruebas y prueba de keyring real; validación
del último UX por Arturo en curso. No reiniciar la app durante sus pruebas por
una tarea de documentación/push. Comprobar HEAD local contra gitea/main al cerrar.

UX autorizado: una sola lista y reproductor al lado, apto para media pantalla
ultrawide. No agregar columna persistente de categorías. widgets.py contiene
overlay acotado con scroll/Cerrar/Escape/clic fuera y delegate de contenido
elegido persistente por ID y contexto (episodios por serie), sólo en la sesión.

Panel externo bajo video: media.py formatea datos, player.py lee video_params/
container_fps/video_codec/track_list/aid/sid y emite media_changed al cambiar.
Elegir pistas por ID, nunca posición. No inventar idiomas/resolución desde nombres.
Reset al abrir/detener; controles deshabilitados si no hay pistas. OSD/OSC apagados
(sí se renderizan subtítulos). Tipografía Qt: configure_appearance en app.py.
Validación real ficticia: scripts/smoke_tracks.py y runtime/tracks-demo.mkv.

Detener: command stop, pending_url=None, metadata vacía y update; paintGL limpia
GL_COLOR_BUFFER_BIT a negro sin fuente. Pausa no actúa estando detenido.
Ir al directo sólo para playing_kind live; reconnect_current hace stop+loadfile
replace de fuente activa en RAM y despausa, mismo motor. No usar pestaña ni fila
seleccionada para decidir qué canal reconectar. Sin prometer retraso cero.
Prueba real: scripts/smoke_live.py, runtime/network.ts ficticio y HTTP local.

Diseño vigente: docs/design.md y ZIP original en raíz, instrucción explícita
prevalece sobre estética Apple anterior (Metro plano/recto/azul/cian). Inicio y
reproductor Qt, una sola lista; nunca poner telemetry/control fuera de alcance
como decoración funcional. Inter 4.1 incluida en assets/fonts con licencia OFL;
QFontDatabase la carga privadamente, pyproject incluye package-data.
LibraryStore SQLite local XDG_DATA_HOME/tecnomata-iptv/library.sqlite3, modo600.
Scope SHA256 servidor+usuario, excluye password; IDs/nombres/kind/parent/ext, sin
URLs/secretos. Toggle favoritos; últimos100 exitosos sin duplicados. Registrar
tras file-loaded + time_pos, no al intentar abrir; polling no declara playing
antes de media_ready. Cambiar cuenta aísla; Olvidar oculta, no borra biblioteca.
Colecciones siguen visibles al abrir TV/VOD/episodio; serie abre episodios.
Pruebas aisladas con SQLite temporal/memory, nunca historial real. Smoke nuevo
scripts/smoke_library.py; capturas únicamente ficticias. Progreso VOD pendiente.

Diseño más reciente Springfield en docs/design.md: acentos amarillos/rosa dona,
base azul noche, navegación Inicio/Ver segmentada. Base estructural ZIP permanece.
Fondos siempre locales en assets/backgrounds para TV/cine/series; ejemplo separado
del preview en RAM, éste tiene prioridad. Favoritos/Último tarjetas ocultas si
vacíos, ocupan fila completa si sólo una. No asignar preview de otro título.
Lista oculta deja hidden_list_rail / › Lista fuera del video. set_list_visible
coordina header/icono/rail/tamaños; usarlo desde F4/icono/Ctrl+K, sin cambiar motor.

Temas actuales: themes.py + selector en Inicio, QSettings Tecnomata/IPTV sólo key.
Demo no persiste. FavoriteList intercepta clics en estrella (38px), delegate usa
FAVORITE_ROLE; sin botón inferior. Pruebas test_themes_controls con settings
temporal y videos ficticios; no leer preferencias/biblioteca del usuario.
