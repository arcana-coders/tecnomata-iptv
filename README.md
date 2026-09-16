# Tecnomata IPTV

App personal de escritorio para Arturo en Linux. Interfaz inspirada en los flujos
de IPTV Smarters Pro, con TV en vivo, películas y series del proveedor Xtream.
Nombre, código y recursos propios; no utiliza recursos de Smarters.

## Pertenece a

- [Índice de memoria](../asistente/projects/tecnomata-iptv/index.md)
- [Documento temático](../asistente/projects/tecnomata-iptv/desarrollo.md)
- [Alcance y fases](docs/plan.md)
- [Estado y cómo retomar](docs/SESSION.md)
- [Instalación/recuperación en Fedora](docs/install-fedora.md)
- Gitea privado: [arturo/tecnomata-iptv](http://192.168.1.175:3000/arturo/tecnomata-iptv), rama `main`.
- Memoria en Gitea: [índice del proyecto](http://192.168.1.175:3000/arturo/asistente/src/branch/master/projects/tecnomata-iptv/index.md).

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
«Recordar mi cuenta» está activado por defecto: guarda la cuenta en GNOME Keyring
y conecta automáticamente al abrir la app. «Olvidar cuenta» la elimina.
Después de conectar, los tres catálogos se precargan en segundo plano y se conservan
en RAM durante la sesión. Secciones/categorías no vuelven a consultar el proveedor.
«Actualizar listas» renueva los tres catálogos y los episodios guardados en RAM.
Doble clic o Enter abre el contenido. F alterna pantalla completa; Escape sale.
Las series primero abren su lista de episodios, identificados por temporada.
Se conserva una sola lista a la izquierda. Categorías abre un menú acotado al
ancho del selector y al interior de la ventana, con scroll y Cerrar; Escape o
clic fuera también lo cierran. El contenido abierto queda verde con ●, incluso
al buscar o volver a una sección. La marca indica elección, no playback exitoso.

## Preparar otro entorno

Para clonar, recuperar libmpv local y preparar cuenta/lanzador:
[guía Fedora](docs/install-fedora.md). Git conserva el código; dependencias y
secret de GNOME Keyring se preparan localmente.

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
| `src/tecnomata_iptv/catalog.py` | Caché de secciones, filtro local y episodios |
| `src/tecnomata_iptv/accounts.py` | Cuenta en Secret Service, sin fallback a archivos |
| `tests/` | Pruebas de contrato con proveedor simulado |
| `scripts/` | Arranque y verificación gráfica |
| `docs/` | Contrato, fases, decisiones y punto de reanudación |
| `runtime/` | Dependencias locales y videos de prueba; fuera de Git |

[Diagnóstico de reproducción](docs/playback-troubleshooting.md) explica las
pruebas de red y el estado saneado en `runtime/playback-status.json`.

## Reglas operativas

La cuenta recordada vive en el almacén seguro de Linux (servicio `tecnomata-iptv`,
identidad `default-account`), nunca en archivos del repo. Sin recordar, sólo RAM.
No guardar listas reales, URLs de
reproducción, respuestas privadas ni logs HTTP en Git. No leer ni migrar datos de
IPTVnator automáticamente. No alterar Hyprland o MPV como efecto de esta app.
Favoritos/progreso son fases posteriores. El proveedor real está validado por
Arturo para canales y cambios, películas y series. Los cambios de caché/cuenta
tienen pruebas propias y se validan en la versión nueva desde el formulario.

Cadena: archivo → repo → documento temático → índice del proyecto → asistente.
