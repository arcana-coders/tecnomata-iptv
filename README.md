# Tecnomata IPTV

App personal de escritorio para Arturo en Linux. Interfaz inspirada en los flujos
de IPTV Smarters Pro, con TV en vivo, películas y series del proveedor Xtream.
Nombre, código y recursos propios; no utiliza recursos de Smarters.

## Pertenece a

- [Índice de memoria](../asistente/projects/tecnomata-iptv/index.md)
- [Documento temático](../asistente/projects/tecnomata-iptv/desarrollo.md)
- [Alcance y fases](docs/plan.md)
- [Estado y cómo retomar](docs/SESSION.md)
- [Diseño Metro del ZIP y adaptación](docs/design.md)
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

Inicio muestra mosaicos de TV, películas, series, favoritos y lo último reproducido,
según el ZIP de diseño de Arturo. Elige un mosaico o Reproductor para ver la lista
y video; Inicio vuelve al tablero. F4 alterna la lista; Ctrl+K enfoca la búsqueda.

Conectar mi servicio abre el formulario de servidor, usuario y contraseña.
«Recordar mi cuenta» está activado por defecto: guarda la cuenta en GNOME Keyring
y conecta automáticamente al abrir la app. «Olvidar cuenta» la elimina.
Después de conectar, los tres catálogos se precargan en segundo plano y se conservan
en RAM durante la sesión. Secciones/categorías no vuelven a consultar el proveedor.
«Actualizar listas» renueva los tres catálogos y los episodios guardados en RAM.
«Detener» cierra el stream y deja el video negro; no es pausa. «Pausa / seguir»
conserva el punto de reproducción. En TV aparece «Ir al directo» junto a la info:
cierra y reabre el canal activo para descartar el búfer acumulado. Puede tardar
en conectar; no elimina el retraso que introduce el proveedor. Funciona sobre
el canal que se reproduce aunque estés navegando otra sección.
Doble clic o Enter abre el contenido. F alterna pantalla completa; Escape sale.
Las series primero abren su lista de episodios, identificados por temporada.
Se conserva una sola lista a la izquierda. Categorías abre un menú acotado al
ancho del selector y al interior de la ventana, con scroll y Cerrar; Escape o
clic fuera también lo cierran. El contenido abierto queda azul con ●, incluso
al buscar o volver a una sección. La marca indica elección, no playback exitoso.

La información aparece debajo del video: resolución recibida, clasificación
SD/HD/Full HD/UHD por altura, fps indicados por el stream y códec. Audio permite
elegir entre pistas disponibles; Subtítulos permite elegir pista o Desactivados.
Si no hay pistas, el selector queda deshabilitado; idioma sin etiqueta es explícito.
Las filas son más compactas y la app incluye Inter Variable, cargada sólo dentro
de Qt, con alternativas del sistema si falla. Diseño plano oscuro con azul/cian.

## Favoritos y recientes

Selecciona una fila y pulsa ☆ Añadir a favoritos; ★ Quitar permite eliminarla.
Canales, películas, series y episodios son guardables. ★ Favoritos muestra la
colección en la misma lista. ↺ Recientes muestra las últimas 100 reproducciones,
más nuevas primero, sin duplicar contenido al repetir. Doble clic o Enter abre.
Se registra al comenzar playback, no sólo al intentar abrir. Series abren episodios;
recientes de episodios conservan serie/formato. Aún no se restaura el minuto VOD.

Ambas colecciones persisten entre sesiones, separadas por cuenta, en
`$XDG_DATA_HOME/tecnomata-iptv/library.sqlite3` (por defecto
`~/.local/share/tecnomata-iptv/library.sqlite3`), modo 600. Sin contraseña, usuario,
servidor ni URL de reproducción almacenados: scope opaco, IDs y nombres mínimos.
Olvidar cuenta elimina credenciales y oculta colecciones; reconectar esa cuenta
recupera favoritos/historial local. La biblioteca no se sube a Git/Gitea.

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
| `src/tecnomata_iptv/media.py` | Formato de resolución e idiomas para el panel externo |
| `src/tecnomata_iptv/widgets.py` | Menú acotado y marca persistente de contenido |
| `src/tecnomata_iptv/player.py` | Video integrado por OpenGL/libmpv |
| `src/tecnomata_iptv/diagnostics.py` | Errores saneados del motor, sin logs privados |
| `src/tecnomata_iptv/catalog.py` | Caché de secciones, filtro local y episodios |
| `src/tecnomata_iptv/library.py` | SQLite local por cuenta para favoritos y recientes |
| `src/tecnomata_iptv/assets/fonts/` | Inter incluida y licencia/procedencia |
| `docs/design.md` | Fuente ZIP, adaptación y límites del diseño |
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
Favoritos y recientes implementados; progreso sigue pendiente. El proveedor real está validado por
Arturo para canales y cambios, películas y series. Los cambios de caché/cuenta
tienen pruebas propias y se validan en la versión nueva desde el formulario.

Cadena: archivo → repo → documento temático → índice del proyecto → asistente.
