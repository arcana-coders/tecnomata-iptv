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
`QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q` (35 pruebas actualmente).

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
