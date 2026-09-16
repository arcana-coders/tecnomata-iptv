# Contexto operativo — Tecnomata IPTV

Leer `README.md`, `docs/SESSION.md` y `docs/plan.md` antes de trabajar.
Este repo contiene una app personal Linux autorizada por Arturo; avanzar por fases
con evidencia y dejar punto de reanudación. Qt/PySide6 + python-mpv + libmpv,
con API Xtream para TV, películas y series. No se busca equivalencia completa ni
copiar recursos de Smarters.

Comandos: `./scripts/run.sh`, `.venv/bin/pytest -q` y prueba gráfica documentada en
`docs/SESSION.md`. Entorno real de arranque: Fedora 44 / Hyprland / Wayland.

Nunca imprimir secretos, URLs autenticadas ni excepciones HTTP crudas. Usuario y
contraseña se capturan en el formulario y sólo viven en memoria. Pruebas con
`example.invalid`, MockTransport y videos locales; no tocar credenciales de
IPTVnator. Catálogos grandes: no consultar todo al entrar ni bloquear hilo gráfico.

Cerrar trabajo actualizando `docs/SESSION.md`, el índice y desarrollo en
`../asistente/projects/tecnomata-iptv/`, más `../asistente/journal.md`.
No marcar una fase como validada con el proveedor si únicamente hay pruebas
simuladas. El repo Git es local hasta configurar remoto; no inventar un push.
