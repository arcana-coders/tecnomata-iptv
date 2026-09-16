# Tecnomata IPTV

App personal de escritorio para Arturo en Linux. Interfaz inspirada en los flujos
de IPTV Smarters Pro, con TV en vivo, películas y series del proveedor Xtream.
Nombre, código y recursos propios; no utiliza recursos de Smarters.

## Pertenece a

- [Índice de memoria](../asistente/projects/tecnomata-iptv/index.md)
- [Documento temático](../asistente/projects/tecnomata-iptv/desarrollo.md)
- [Alcance y fases](docs/plan.md)
- [Estado y cómo retomar](docs/SESSION.md)

## Ejecutar

```bash
cd /home/tecnomata/tecnomata/tecnomata-iptv
./scripts/run.sh
# Demostración con catálogo ficticio:
./scripts/run.sh --demo
# Dos videos locales para comprobar cambio dentro del mismo reproductor:
./scripts/run.sh --demo-file runtime/demo-a.mp4 --demo-file runtime/demo-b.mp4
```

Conectar mi servicio abre el formulario de servidor, usuario y contraseña.
Doble clic o Enter abre el contenido. F alterna pantalla completa; Escape sale.
Las series primero abren su lista de episodios, identificados por temporada.

## Preparar otro entorno

Python >=3.11, libmpv y OpenGL funcional. En Fedora, el paquete del sistema es
`mpv-libs`; instalarlo requiere privilegios del usuario. En este equipo se utiliza
una copia local extraída del RPM oficial de Fedora, ignorada por Git, sin sudo.
Su procedencia y reproducción están en [arquitectura](docs/architecture.md).

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q
```

`requirements.lock` fija las versiones usadas en este equipo. Instalar con
`.venv/bin/pip install -r requirements.lock` y después `pip install -e .` desde
el mismo entorno. `./scripts/install-desktop.sh` instala el lanzador de usuario.

## Archivos importantes

| Ruta | Papel |
|---|---|
| `src/tecnomata_iptv/app.py` | Interfaz Qt y consultas en segundo plano |
| `src/tecnomata_iptv/xtream.py` | Acceso, catálogos, episodios y URLs |
| `src/tecnomata_iptv/player.py` | Video integrado por OpenGL/libmpv |
| `src/tecnomata_iptv/diagnostics.py` | Errores saneados del motor, sin logs privados |
| `tests/` | Pruebas de contrato con proveedor simulado |
| `scripts/` | Arranque y verificación gráfica |
| `docs/` | Contrato, fases, decisiones y punto de reanudación |
| `runtime/` | Dependencias locales y videos de prueba; fuera de Git |

[Diagnóstico de reproducción](docs/playback-troubleshooting.md) explica las
pruebas de red y el estado saneado en `runtime/playback-status.json`.

## Reglas operativas

Credenciales sólo en memoria durante la sesión. No guardar listas reales, URLs de
reproducción, respuestas privadas ni logs HTTP en Git. No leer ni migrar datos de
IPTVnator automáticamente. No alterar Hyprland o MPV como efecto de esta app.
La persistencia de favoritos/progreso y el almacenamiento seguro de cuenta son
fases posteriores. No considerar la conexión real validada por pasar mocks.

Cadena: archivo → repo → documento temático → índice del proyecto → asistente.
