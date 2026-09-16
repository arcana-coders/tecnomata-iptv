# Arquitectura

- Python, PySide6/Qt Widgets y python-mpv. Distribución inicial local.
- `XtreamClient`: `player_api.php`, timeouts de 20 s, redirecciones desactivadas,
  validación de respuestas y URLs con componentes escapados. No logs privados.
- Qt ejecuta consultas en QThreadPool, una consulta activa. Operaciones de auth,
  almacén seguro y episodios no cacheados bloquean controles de navegación;
  la precarga de secciones mantiene navegación/reproducción habilitadas.
- `CatalogCache` conserva categorías/listas de live/vod/series en RAM por cuenta.
  Precarga una sección a la vez, prioriza la sección seleccionada para la próxima
  tarea y no sobrescribe una sección/episodios visible con otra respuesta.
  Filtro de categorías local; episodios cacheados por serie. Actualizar listas,
  cambiar u olvidar cuenta sustituyen el caché completo. Fallos se reintentan sólo
  con Actualizar listas; una sección fallida no impide precargar las demás.
- `VideoWidget`: QOpenGLWidget con render API libmpv. Un MPV y render context por
  ventana. `loadfile ... replace` cambia el contenido. Sin subprocess MPV y sin
  embedding por identificador X11, para funcionar con Wayland nativo.
- Callbacks de render notifican a Qt mediante señal encolada; dibujo con contexto
  OpenGL activo. Liberar render context antes de terminar el motor.
- Playback usa User-Agent de reproductor VLC, timeout de 20 s y ytdl desactivado
  para URLs IPTV directas. Decodificación por software durante validación inicial.
- Eventos python-mpv pueden contener bytes; normalizarlos antes de comparar.
  Logs del motor sólo se convierten a códigos HTTP/TLS/red/codec permitidos;
  no se guardan los mensajes originales ni URLs. Estado saneado en runtime.
- `AccountStore` usa explícitamente `keyring.backends.SecretService.Keyring`.
  Toda la cuenta se guarda como un secret, servicio tecnomata-iptv, identidad
  default-account. No JSON con credenciales en disco ni backends plaintext.
  Después de autenticar: guardar/borrar según Recordar mi cuenta. Al arrancar:
  leer el secret en worker, autenticar y precargar. Olvidar elimina el secret y
  cierra la cuenta/caché. Error de almacén se informa y permite uso sólo en sesión.
  GNOME Keyring real probado con entrada ficticia aislada y eliminada al terminar.
  [Documentación primaria de keyring](https://github.com/jaraco/keyring).
- SQLite para favoritos/progreso sigue pendiente; nunca contraseñas en SQLite.

## Dependencia local de este equipo

Fedora tiene MPV 0.41 pero no mpv-libs. Se descargó el paquete
`mpv-libs-0.41.0-5.fc44.x86_64.rpm` de:

https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/os/Packages/m/mpv-libs-0.41.0-5.fc44.x86_64.rpm

Verificado con `rpm -K` (digests signatures OK). Extraído mediante rpm2cpio/cpio
a `runtime/libmpv/`. Añadido enlace `libmpv.so -> libmpv.so.2` para que
`ctypes.util.find_library` lo detecte con LD_LIBRARY_PATH. `scripts/run.sh` aplica
esa ruta sólo a la app. No se instaló RPM en el sistema; no requiere sudo.
En otro equipo, preferir el paquete nativo de la distribución. Esta copia local
necesita las dependencias Fedora instaladas y no es un bundle portable universal.

## Referencias primarias

- [Qt QOpenGLWidget](https://doc.qt.io/qt-6/qopenglwidget.html)
- [python-mpv](https://github.com/jaseg/python-mpv)
- [MPV: manual, comandos y embedding](https://mpv.io/manual/stable/)
- [Ejemplos oficiales libmpv](https://github.com/mpv-player/mpv-examples)

Xtream no tiene un contrato público universal único: los mocks verifican el
formato esperado, y la fase 3 confirma las particularidades del proveedor real.

## UX de categorías y contenido elegido — 2026-09-16

Una sola lista a la izquierda y video ocupando el resto, por uso de Arturo en
media pantalla ultrawide. `widgets.py` abre categorías como overlay hijo de
la ventana: ancho del selector, altura máxima 340 px y límites del host. Nombres
largos se abrevian; scroll vertical, Cerrar, Escape y clic fuera. Se cierra al
redimensionar/desactivar la ventana. No depende de posicionar ventanas Wayland.

El delegate dibuja verde, borde y ● para contenido abierto. Identidad stream_id
o series_id por sección, episodios por serie; conserva marca al filtrar/volver,
y se limpia al cambiar/olvidar cuenta. La selección de teclado tiene otro color.
La marca no afirma reproducción exitosa ni se guarda entre ejecuciones.

35 pruebas pasan, incluyendo 200 categorías largas, scroll y cierres, y marca
tras búsqueda/secciones/episodios. Smoke Wayland: overlay acotado e inspección
de captura ficticia; video: 8 cambios, 127 frames, un motor/widget/ventana.

## Información externa, pistas y tipografía — 2026-09-16

Panel debajo del video, sin OSD informativo: resolución de video_params, nivel
por altura, códec y container_fps. Los fps son declarados, pueden no ser fiables;
resolución no garantiza calidad/bitrate. No usa HD/UHD del nombre del canal.
Audio/Subtítulos muestran track_list, lang/title/codec e ID; seleccionan aid/sid
por ID y subtítulos permiten no. Idioma ausente y pistas ausentes explícitos.
Sólo propiedades permitidas en RAM; no amplía diagnósticos guardados ni registra
metadata, URLs o respuestas reales. Inicio/cambio/stop limpia el panel. Actualiza
por polling Qt y comparación, después de file-loaded, incluidos cambios de pistas.

Interfaz usa una sola lista, padding vertical 8 px (antes 14), controles más
compactos, colores neutros y jerarquía tipográfica inspirada en Apple. Se aplicó
skill apple-design con criterio de escritorio/puntero, sin transparencia de ventana.
configure_appearance elige SF Pro si existe, Inter, Adwaita Sans o fallback;
en este Linux usa Adwaita Sans ya instalada. No incluye ni instala SF Pro.

37 pruebas pasan. Smoke Wayland con MKV sintético: 640×360, 25 fps, dos audios
spa/eng, subtítulo spa; cambios reales aid/sid, desactivar subtítulos y stop.
Captura ficticia inspeccionada: panel fuera del video y subtítulos renderizados.
Generar fixture (fuera de Git):

```bash
python -c 'from pathlib import Path; Path("runtime/demo-sub.srt").write_text("1\n00:00:00,000 --> 00:00:10,000\nSubtítulo de prueba\n")'
ffmpeg -hide_banner -loglevel error -y -i runtime/demo-a.mp4 -f lavfi -i sine=frequency=440:duration=12 -f lavfi -i sine=frequency=880:duration=12 -i runtime/demo-sub.srt -map 0:v -map 1:a -map 2:a -map 3:s -c:v copy -c:a aac -c:s srt -metadata:s:a:0 language=spa -metadata:s:a:1 language=eng -metadata:s:s:0 language=spa -t 12 runtime/tracks-demo.mkv
LD_LIBRARY_PATH="$PWD/runtime/libmpv/usr/lib64" .venv/bin/python scripts/smoke_tracks.py
```

Referencias: [MPV propiedades](https://mpv.io/manual/stable/#property-list),
[Apple tipografía](https://developer.apple.com/design/human-interface-guidelines/typography).

## Stop y vuelta al directo — 2026-09-16

La percepción de pausa con Stop provenía de conservar el framebuffer del último
cuadro. Stop manda el comando MPV (cierra archivo/stream y limpia playlist), borra
pending_url/metadata y pide update. paintGL sin fuente limpia negro vía funciones
OpenGL del contexto, en vez de dejar imagen antigua. Pausa no actúa sin fuente.
Window limpia título y playing_kind en stop/cambio/olvido. Motor sigue disponible.

Ir al directo junto a resolución sólo si playing_kind=live. Reconecta la fuente
activa con stop+loadfile replace y pause=False. Descarta demux/cache del archivo
anterior; evita buscar al final en TS no seekable. No usa fila ni pestaña actuales
para decidir fuente. No cambia globalmente límites de caché ni ofrece retraso
cero: la cadena del proveedor puede llevar retraso. Pistas vuelven a detección
normal al reconectar; preferencias de idioma persistentes aún pendientes.

39 pruebas y scripts/smoke_live.py PASS: HTTP local con runtime/network.ts sintético,
servidor continuo/paced; nueva request/cierre previo, despausa, mismo motor,
playlist de un item; stop pausado cierra request, idle, playlist vacía y negro
medido en framebuffer. Fixture no privado, ignorado. Generarlo si falta:

```bash
ffmpeg -hide_banner -loglevel error -y -f lavfi -i color=c=teal:s=640x360:r=25 -f lavfi -i sine=frequency=440:duration=12 -t 12 -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac -f mpegts runtime/network.ts
LD_LIBRARY_PATH="$PWD/runtime/libmpv/usr/lib64" .venv/bin/python scripts/smoke_live.py
```

[MPV stop](https://mpv.io/manual/stable/#command-interface) confirma cierre y
limpieza de playlist con motor disponible para cliente API.

## Biblioteca y rediseño Metro — 2026-09-16

Diseño/pantallas/fuente ZIP en [design.md](design.md). Inicio y reproductor alternan
widgets Qt en la misma ventana/motor; búsqueda/filtros/tablas se mueven a la única
columna izquierda. Colecciones reutilizan QListWidget; row_source/metadata mínima
permiten abrir mezcla de TV/VOD/series/episodios sin confundir IDs o rutas. Serie
favorita abre episodios; episodio favorito/reciente conserva parent y extension.
No se restauran posiciones todavía. Favorito se añade desde la fila seleccionada.

library.py: SQLite fuera del repo, permissions600/dir700 al crear; tabla entries
con PK(scope,kind,id,parent), nombre/category/ext/series_name/favorite/played.
Scope SHA256 servidor normalizado + NUL + usuario, no incluye contraseña; cambiar
password conserva biblioteca. Nunca guarda cuenta/server/URL/rawresponse/logo.
UPsert sólo campos permitidos y parámetros SQL; favorite toggle y played se
confirman en transacción. Historial ordenado por played, límite100/deduplicado,
pruna anteriores no favoritos y preserva favoritos antiguos. SQLite errores
visibles/sanitizados; si falla apertura, video sigue y biblioteca se deshabilita.
Olvidar/cambiar sólo ocultan/aislan colecciones, no eliminan DB. No lectura de
historial real en pruebas: dependency injection Memory/temporal. Backup por usuario
fuera de Git; cuenta sigue Secret Service, no hay plaintext fallback.

pending_history pertenece a la fuente activada, no pestaña navegada, y se registra
una vez al estado playing. Polling espera media_ready tras file-loaded, evitando
marcar nueva fuente con time_pos del archivo anterior. Stop/cambio de cuenta
limpia pendiente. Reconnect live no crea duplicados. Foreground workers bloquean
acciones de biblioteca/Inicio hasta terminar; prefetch no reemplaza una colección.
Filtro resuelve favoritos en una consulta por vista, sin N queries para canales.

45 pruebas y smoke_library real con fixture: persistencia/reopen, namespace,
aislamiento por cuenta y cambio/olvido, orden/dedup/límite, series/episodios,
secrets no guardados y modo600. Smokes tracks/live siguen PASS; smoke_gui ocho
cambios, 131 frames, mismo motor/widget/ventana. Capturas ficticias inspeccionadas.
Inter oficial incluida en wheel con OFL; pip wheel usa build isolation (venv no
incluye setuptools, no usar --no-build-isolation en este entorno).
