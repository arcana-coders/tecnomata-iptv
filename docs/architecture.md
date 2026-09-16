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
