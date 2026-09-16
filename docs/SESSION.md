# Punto de reanudación — 2026-09-16

## Estado

Fases 0 y 1 completas; fase 2 validada con videos locales en Wayland.
Fase 3 en validación: Arturo confirma acceso y listas reales de canales/películas,
pero reporta pantalla sin reproducción. La versión corregida está abierta para
repetir el intento; reproducción del proveedor todavía sin confirmar.
Prototipo funcional, todavía sin fichas, portadas, EPG, favoritos ni progreso.

## Evidencia

- Fedora 44, Python 3.14.6, PySide6 6.11.2, python-mpv 1.0.8, libmpv 0.41.
- `.venv/bin/pytest -q`: 14 passed.
- Integración gráfica con API simulada y respuestas demoradas: TV, películas,
  series y episodios cargan a través de los workers Qt; 77 ticks de un timer de
  interfaz durante las consultas confirman que el hilo gráfico sigue respondiendo.
- Prueba gráfica real `scripts/smoke_gui.py`: PASS; 8 cambios de contenido,
  130 frames dibujados, mismo motor, mismo widget, una ventana visible y una
  entrada en la playlist. Color central [127, 0, 127], correspondiente al segundo
  clip, comprobado por framebuffer real, no sólo por contador de callbacks.
- Navegación demo de series/episodio/volver, búsqueda y fullscreen/salida probadas.
- Hyprland confirma la ventana real con clase `tecnomata-iptv`,
  `floating: false` y `xwayland: false`.
- Captura local inspeccionada en `runtime/prototype.png` (fuera de Git).
- RPM libmpv oficial: `rpm -K` indica digests signatures OK. Copia local, sin sudo.

## Corrección tras primera prueba real

Arturo reporta que conecta y carga catálogos, pero doble clic sólo cambia el título.
Se confirma un bug de diagnóstico: python-mpv entrega `reason` como bytes y el
prototipo comparaba con `"error"` str; se ocultaban fallos de reproducción.
Esto explica el silencio del error, no prueba la causa del fallo del proveedor.

Cambios: normalizar bytes; estados conectando/reproduciendo/pausa/final;
clasificar errores HTTP/TLS/red/codec sin guardar texto privado; User-Agent de
reproductor VLC; extracción ytdl deshabilitada para URLs directas. Hardware decode
desactivado temporalmente para validar el pipeline OpenGL por software.

Evidencia nueva:
- 21 pruebas unitarias pasan, incluyendo reason bytes y saneamiento de errores.
- `scripts/smoke_network.py` PASS: MPEG-TS H264/AAC por HTTP local, redirección 302,
  imagen teal real y HTTP 403 visible. Sin requests del extractor web.
- `scripts/smoke_gui.py` PASS después del cambio: 8 cambios, mismo motor/widget,
  114 frames, una ventana y playlist de una entrada.
- Estado permitido en `runtime/playback-status.json` (modo 600): sólo state,
  failure/http_status, motor/render inicializados, closed y contador de frames.
  Nunca cuenta, servidor, URL, nombre del contenido ni texto crudo de logs.

No se accedió a datos privados de IPTVnator. Al reiniciar la app se pierde la cuenta
porque no hay persistencia; Arturo debe introducirla en el formulario otra vez.

## Ejecutar ahora

```bash
cd /home/tecnomata/tecnomata/tecnomata-iptv
./scripts/run.sh
```

Botón «Conectar mi servicio». Introducir URL del servidor, usuario y contraseña
sin pegarlos en chat. TV/películas se reproducen con doble clic; series abren
episodios primero. No se guardan credenciales al cerrar.
Lanzador local instalado por `scripts/install-desktop.sh`.

## Seguir, en orden

1. Repetir playback del proveedor en versión corregida y revisar estado saneado.
2. Probar canal, película y episodio; registrar sólo resultados saneados.
3. Cambiar de canal repetidamente; comprobar imagen/audio y ninguna ventana MPV.
4. Verificar formatos/extensiones y EPG del proveedor; corregir incompatibilidades.
5. Completar fase 4: portadas/fichas, selector de temporadas, favoritos, EPG,
   progreso y controles de seek/audio/subtítulos.
6. Fase 5: reconexión/cierre/catálogos grandes, empaquetado y remoto de respaldo.

## Repetir prueba gráfica

Videos `runtime/demo-a.mp4` y `demo-b.mp4` generados con ffmpeg (color teal y purple,
640×360, 25 fps, 12 s, MPEG4). Son ficticios y no vienen del proveedor.

```bash
LD_LIBRARY_PATH="$PWD/runtime/libmpv/usr/lib64" .venv/bin/python scripts/smoke_gui.py
```

Si libmpv está instalada en el sistema, la variable no hace falta.
Para entorno reproducible: `.venv/bin/pip install -r requirements.lock`, después
`.venv/bin/pip install -e .`. Para entorno nuevo seguir README/arquitectura.

## Límites actuales

- Sin prueba real de credenciales/contenido/EPG; contratos Xtream probados con mocks.
- Diseño inicial de listas; no experiencia final de Smarters.
- Live usa `.ts`, VOD/series respetan `container_extension` si el API lo entrega.
- No caché/paginación de grandes catálogos, descarga de imágenes ni keyring todavía.
- Cierre durante consulta pide esperar a que termine para evitar destruir el worker.
- Credenciales en memoria y en requests/URLs requeridas por Xtream. HTTP sin TLS
  depende de la URL del proveedor; no inventar HTTPS ni desactivar validación TLS.
- Repo con Git y commit local; remoto todavía no configurado. La memoria tenía
  cambios anteriores de otras tareas y no se mezclaron en este commit.

## Documentación padre

[Índice](../../asistente/projects/tecnomata-iptv/index.md) →
[desarrollo](../../asistente/projects/tecnomata-iptv/desarrollo.md) →
[README](../README.md) → este estado y código.
