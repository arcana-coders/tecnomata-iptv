# Diagnóstico de reproducción

Pertenece a [arquitectura](architecture.md) y [estado de sesión](SESSION.md).

## Primer incidente del proveedor

La cuenta conecta y las listas cargan, pero no aparece video. El título sí cambia.
Bug confirmado: `MpvEvent.as_dict()["reason"]` devuelve `b"error"`; una comparación
con str impide informar al usuario. Se normaliza con `text_value`.
No confundir corregir el error oculto con conocer la causa original del stream.

## Revisar sin filtrar secretos

`runtime/playback-status.json` permite ver state, failure, http_status, estado del
motor/render y frames. No contiene URL, host, usuario, contraseña o título.
No imprimir HTTP requests ni propiedades MPV `path`/`stream-open-filename`:
contienen credenciales Xtream. No capturar la pantalla con el formulario lleno.

- HTTP 401/403: acceso al stream rechazado; revisar datos/ruta/cliente/límite
  de conexiones del proveedor. Cargar el catálogo no garantiza acceso al video.
- HTTP 404: comprobar ruta de reproducción, identificador, formato/extensión.
- TLS: revisar el endpoint y su certificado; mantener verificación TLS.
- Red/DNS: comprobar resolución/conectividad al servidor que entrega el video.
- Codec: aislar decoder y formato con video ficticio equivalente.
- Sin error y estado playing pero pantalla negra: comprobar framebuffer y OpenGL.

## Pruebas locales

```bash
.venv/bin/pytest -q
LD_LIBRARY_PATH="$PWD/runtime/libmpv/usr/lib64" .venv/bin/python scripts/smoke_gui.py
ffmpeg -hide_banner -loglevel error -f lavfi -i color=c=teal:s=640x360:r=25 -f lavfi -i sine=frequency=440:sample_rate=48000 -t 10 -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac -f mpegts -y runtime/network.ts
LD_LIBRARY_PATH="$PWD/runtime/libmpv/usr/lib64" .venv/bin/python scripts/smoke_network.py
```

El servidor del smoke es localhost, sus datos son ficticios y sus logs de acceso
están desactivados. Testea redirect, rechazo 403 e imagen/audio H264/AAC.
El motivo de fallo bytes se verifica con 403 real.

## Compatibilidad de cliente

User-Agent explícito de reproductor; ytdl desactivado porque Xtream entrega rutas
directas y no necesitamos extracción de páginas. Evita requests extra con firma
de navegador tras un fallo. Software decode aísla hardware/OpenGL inicialmente.
La firma de cliente puede afectar a algunos proveedores; es una hipótesis para
este servicio hasta confirmar su resultado real, no una causa demostrada.

Referencia primaria sobre portales Xtream y User-Agent:
[IPTVnator #1170](https://github.com/4gray/iptvnator/pull/1170).
