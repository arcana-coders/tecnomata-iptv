# Arquitectura

- Python, PySide6/Qt Widgets y python-mpv. Distribución inicial local.
- `XtreamClient`: `player_api.php`, timeouts de 20 s, redirecciones desactivadas,
  validación de respuestas y URLs con componentes escapados. No logs privados.
- Qt ejecuta consultas en QThreadPool, una consulta activa; controles de navegación
  deshabilitados durante la operación. Categorías primero, catálogo después.
- `VideoWidget`: QOpenGLWidget con render API libmpv. Un MPV y render context por
  ventana. `loadfile ... replace` cambia el contenido. Sin subprocess MPV y sin
  embedding por identificador X11, para funcionar con Wayland nativo.
- Callbacks de render notifican a Qt mediante señal encolada; dibujo con contexto
  OpenGL activo. Liberar render context antes de terminar el motor.
- Credenciales y respuestas en RAM. SQLite para favoritos/progreso y keyring para
  recordar credenciales se evalúan en fase 4; no persistir contraseñas en SQLite.

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
