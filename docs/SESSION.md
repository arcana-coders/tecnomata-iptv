# Punto de reanudación — 2026-09-16

## Estado

Fases 0–3 completas: Arturo confirma canales, cambios entre canales, película
y serie reproducidos correctamente con su proveedor en la versión corregida.
Fase 4 iniciada con precarga/caché de tres secciones y cuenta recordada en Linux.
Prototipo funcional, todavía sin fichas, portadas, EPG ni progreso; favoritos y recientes ya implementados.

## Último cambio: Springfield, ejemplos y pestaña de lista oculta

Arturo quiere ejemplos de fondo al arrancar, tarjetas colecciones sólo con datos,
flecha para lista escondida y navegación más bonita, con referencias a Los Simpson.
TV/cine/series: fondos ilustrados locales, preview real en RAM tiene prioridad;
favoritos/último se ocultan vacíos y sólo muestran preview si título corresponde.
Única tarjeta de colección llena fila. Inicio/Ver control segmentado amarillo,
dona nativa Qt, base noche y esquinas suaves. Icono lista sólo en reproductor;
rail › Lista aparece al esconder columna; clic/F4/Ctrl+K restaura mismos tamaños,
selección y motor. Ver design.md y assets/backgrounds/README.md para provenance.

48 pruebas cubren colecciones condicionales y recuperación de lista/navegación;
smoke_library real comprueba fondos cargados y rail visible/restauración sin
cambiar motor. Assets generados con image_gen tras rechazar intento genérico de
Antigravity. Falta validación visual de Arturo con su proveedor.

## Histórico: favoritos, recientes y diseño del ZIP

Arturo pide favoritos/último reproducido y adaptar al ZIP en la raíz. Ver design.md:
Inicio con mosaicos/datos reales y reproductor Metro oscuro plano azul/cian con
una lista izquierda. Inter Variable oficial incluida, sólo Qt, con licencia OFL.
Info/controles siguen fuera del video. F4 lista, Ctrl+K búsqueda. Preview del último
cuadro en RAM sólo; no capturas reales en archivos ni paneles ficticios de DVR/red.

LibraryStore SQLite local por cuenta (scope SHA256 sin secretos), modo600,
favoritos TV/VOD/series/episodios y recientes de últimos100 exitosos/deduplicados.
Añadir/quitar desde fila; colecciones comparten lista y permanecen al reproducir
TV/VOD/episodio; serie abre episodios. Historial al comenzar, no al intentar abrir.
Cambio/olvido aíslan/ocultan, no borran DB; reapertura conserva todo. Aún no minuto VOD.

45 pruebas pasan; smoke_library real reproduce y registra, favorites siguen
visibles y ambas colecciones sobreviven cierre/reopen. Capturas ficticias home/
player inspeccionadas. Smoke_gui 8 cambios/131frames/mismo motor/widget/ventana;
tracks y live PASS después de rediseño. Wheel contiene Inter y OFL. ZIP original
versionado sin modificar para recuperar referencia. Arturo valida nuevo UX real.

## Histórico: detener real e Ir al directo

Arturo reporta Detener aparentemente pausa y pide ponerse al corriente del live.
Stop ya mandaba el comando de cierre, pero el framebuffer podía conservar el
último cuadro; ahora paintGL limpia negro sin pending_url y stop pide redibujado.
Stop limpia fuente/metadata/título/tipo; Pausa no actúa detenido. Ir al directo
junto a info sólo cuando fuente activa live: stop + loadfile replace de esa URL,
sin pausa, mismo motor/widget. Navegar otra pestaña no altera fuente activa.
No se promete sincronía absoluta ni quitar el retraso del proveedor.

39 pruebas pasan. scripts/smoke_live.py PASS en Wayland con stream HTTP sintético:
pausa, reconexión genera nueva request y cierre anterior, mismo motor, un item;
stop estando pausado cierra conexión, idle_active, playlist vacía y framebuffer
negro en tres puntos. No hay URLs/logs reales en salida. Valida Arturo proveedor.

## Histórico: información, pistas y tipografía

Panel bajo video: resolución recibida, fps declarados y códec; audio y subtítulos
seleccionables por ID (subtítulos también Desactivados). Ausencias explícitas.
37 pruebas pasan; smoke_tracks.py real Wayland: 640×360/25fps, audios Español y
English, subtítulo activo/desactivado y limpieza al detener. Captura inspeccionada.
Lista compactada 14→8 px de padding vertical; toda la app con Adwaita Sans en
este equipo, fallback SF Pro/Inter si instalados. Neutros y jerarquía Apple.
No instalar SF Pro ni activar transparencia. User validation del servicio pendiente.
Cómo generar fixture y repetir: architecture.md, sección Información externa.

## Histórico: categorías y marca de contenido

Arturo pide conservar una sola lista por su uso en media pantalla ultrawide.
Categorías usa overlay interno acotado con scroll, Cerrar, Escape y clic fuera;
no agrega sidebar. Contenido abierto marcado verde con ●, persistente por ID
al buscar y volver. Episodios tienen contexto por serie; limpiar al cambiar cuenta.
Código: widgets.py y app.py. Prueba nueva: tests/test_selection_gui.py.

Evidencia: 35 pruebas pasan; overlay real Wayland con 200 nombres largos dentro
de ventana y captura ficticia inspeccionada. Smoke video: 8 cambios, 127 frames,
mismo motor/widget, una ventana. Falta confirmación de Arturo del nuevo UX real.

## Histórico: precarga y cuenta recordada

Al autenticar, CatalogCache precarga categorías/listas de live/vod/series en
segundo plano. Al entrar a otra sección o filtrar categoría, reutiliza RAM:
cero requests nuevos. Categoría elegida conservada al volver. Episodios cacheados
por serie. Actualizar listas invalida todo y repite la precarga; cambiar/olvidar
cuenta sustituyen el caché completo. Fallar una sección no impide cargar las demás.
Precarga no bloquea navegación ni reproducción de catálogos ya disponibles.

Recordar mi cuenta activado por defecto. AccountStore guarda servidor/usuario/
contraseña como un solo secret de GNOME Keyring, servicio tecnomata-iptv, identidad
default-account. No archivos de credenciales ni backend plaintext. Sólo guardar
después de auth exitosa. Arranque lee el almacén, autentica y precarga solo.
Olvidar cuenta elimina el secret y cierra sesión. Desmarcar Recordar elimina
lo guardado y permite usar sólo esta sesión. Fallos de almacén son visibles.

Evidencia actual:
- `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q`: 33 passed.
- Pruebas GUI: precarga de todas las secciones, navegación habilitada durante
  precarga, regreso sin requests, filtros locales, episodios cacheados, refresh,
  cuenta restaurada automáticamente y Olvidar/sólo sesión.
- Almacén seguro real: guardar/recuperar una cuenta ficticia en servicio aislado,
  comparar valores y borrar entrada de prueba: PASS; no se imprimió el secret.
- Smoke de video integrado tras cambios: 8 cambios, 127 frames, motor/widget
  compartidos y una sola ventana: PASS.
- App nueva abierta; introducir cuenta una vez con Recordar activado para guardar
  la cuenta real, que la versión anterior mantenía únicamente en memoria.

## Histórico: evidencia inicial

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

## Histórico: corrección tras primera prueba real

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

No se accedió a datos privados de IPTVnator. En esa versión la cuenta sólo vivía
en memoria; la versión actual incorpora el almacén seguro descrito arriba.

## Ejecutar ahora

```bash
cd /home/tecnomata/tecnomata/tecnomata-iptv
./scripts/run.sh
```

Botón «Conectar mi servicio». Introducir URL del servidor, usuario y contraseña
sin pegarlos en chat. TV/películas se reproducen con doble clic; series abren
episodios primero. Recordar mi cuenta guarda en GNOME Keyring y permite autoentrada.
Lanzador local instalado por `scripts/install-desktop.sh`.

## Seguir, en orden

1. Guardar cuenta real desde el formulario y comprobar reapertura automática.
2. Verificar precarga y cambio de sección sin volver a cargar con el catálogo real.
3. Completar fase 4: portadas/fichas, selector de temporadas, EPG,
   progreso y controles de seek; audio/subtítulos ya implementados, validar proveedor.
4. Fase 5: reconexión/cierre/catálogos grandes y empaquetado. Gitea ya preparado
   para preservar el avance; respaldos externos adicionales por definir.

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

- Playback real de las tres secciones confirmado por Arturo; EPG aún no validado.
- Diseño inicial de listas; no experiencia final de Smarters.
- Live usa `.ts`, VOD/series respetan `container_extension` si el API lo entrega.
- Caché de sesión implementado; no caché de catálogo en disco, paginación ni imágenes todavía.
- Cierre durante consulta pide esperar a que termine para evitar destruir el worker.
- Credenciales en memoria y en requests/URLs requeridas por Xtream. HTTP sin TLS
  depende de la URL del proveedor; no inventar HTTPS ni desactivar validación TLS.
- Repo privado Gitea `arturo/tecnomata-iptv`, remoto `gitea`, rama `main`.
  Memoria padre en `arturo/asistente`, rama `master` (remoto local `origin`).
  Se documenta y sube el avance mientras Arturo prueba precarga/cuenta; no
  reiniciar la app por esta tarea. Cambios previos ajenos quedan fuera del commit.

## Documentación padre

[Índice](../../asistente/projects/tecnomata-iptv/index.md) →
[desarrollo](../../asistente/projects/tecnomata-iptv/desarrollo.md) →
[README](../README.md) → este estado y código.

Instalación/recuperación desde Gitea en [guía Fedora](install-fedora.md).
