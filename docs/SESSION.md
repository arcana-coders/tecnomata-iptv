# Punto de reanudación — 2026-09-16

## Estado

Fases 0 y 1 completas; fase 2 validada con videos locales en Wayland.
Fase 3 pendiente de conectar el proveedor de Arturo desde la app.
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

1. Validar cuenta real y categorías de las tres secciones.
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
