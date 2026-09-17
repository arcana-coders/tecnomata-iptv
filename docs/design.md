# Diseño autorizado — Springfield / Metro Cinema

Arturo dejó [ZIP original](../stitch_tecnomata_iptv_desktop_player.zip) como fuente
del diseño. Contiene inicio, reproductor (screen.png + code.html) y DESIGN.md.
ZIP versionado sin modificar; extraer bajo runtime/design-reference para revisar,
no ejecutar HTML/JS externo ni convertir el reproductor en un navegador.

## Diseño vigente: Springfield — 2026-09-16

Arturo mantiene la estructura del ZIP y pide un look referido a Los Simpson,
imágenes de ejemplo desde arranque y una pestaña para recuperar lista oculta.
Esta instrucción más reciente cambia los acentos/geometría Metro anteriores:
base azul noche, amarillo Springfield, detalles rosa dona y navegación redondeada.
Header usa dona dibujada en Qt; Inicio/Ver como control segmentado, icono de lista
sólo en reproductor. F4/icono oculta columna y deja pestaña lateral › Lista,
sin cubrir video; clic/F4/Ctrl+K la recupera y conserva fuente/motor/selección.

TV/cine/series incluyen ejemplos ilustrados locales siempre, sin depender del
proveedor, Internet ni playback. Cuadro actual en RAM tiene prioridad al volver
a Inicio. Favoritos/Último se ocultan si vacíos; si sólo existe una tarjeta ocupa
el ancho de la fila. Al existir contenido, usan ejemplo del tipo y cuadro sólo
si corresponde a ese nombre, evitando atribuir imagen de otro canal. Fondos son
decorativos; no afirman emitir Los Simpson ni ser portadas reales del catálogo.

Assets y prompts/procedencia: assets/backgrounds/README.md. Antigravity primer
intento rechazado por personajes genéricos; image_gen rechazó generación de
personajes. Se generaron fondos originales de sofá/dona/autocine/barrio mediante
image_gen, sin personajes, usando la paleta referencial. Revisados/integrados; ZIP
preservados. Capturas de pruebas sólo con videos ficticios. 48 pruebas cubren
condiciones y navegación, más smoke_library real de pestaña/video/biblioteca.

## Histórico: adaptación Qt inicial

- Fondos #080a0f/#11141d, estados azul #0078d7 y acento cian #00e5ff.
- Geometría plana, esquinas rectas, bordes discretos y lista compacta.
- Inicio de mosaicos: TV/cine/series con cantidades del caché real, favoritos y
  último reproducido. Preview opcional del último cuadro decodificado sólo en RAM;
  se borra al cambiar/olvidar cuenta y no se guarda imagen real en archivos.
- Reproductor: una lista izquierda, pestañas/filtros/búsqueda en esa columna;
  video ocupa el resto. Favoritos y Recientes sustituyen el contenido de esa lista.
  Se mantiene lista de colección al reproducir TV/VOD/episodio desde ella.
- Datos, controles y selección de pistas fuera del video por instrucción previa
  de Arturo. Stop negro e Ir al directo preservados. F4 oculta/muestra la lista;
  Ctrl+K abre búsqueda. Inicio y Reproductor alternan conservando motor/fuente.
- Inter Variable 4.1 del release oficial rsms/inter, SIL OFL incluida, cargada sólo
  dentro de Qt. JetBrains Mono para datos si existe en el sistema. No instalar
  SF Pro ni modificar fuentes/transparencia de Linux.

El ZIP prevalece sobre la regla de esquinas redondeadas de apple-design: Arturo
solicita explícitamente Metro. Skill usada como criterio de legibilidad/jerarquía,
no para imponer una estética incompatible. No añadir cifras ficticias de Mbps,
red/latencia/búfer, avatares, EPG, DVR/grabar nube, VAAPI ni controles decorativos.
Portadas/fichas, EPG y progreso continúan pendientes; Recientes permite volver a
abrir el contenido, todavía no restaura el minuto de películas/episodios.

## Archivos y evidencia

app.py coordina vistas; widgets.py contiene HomeTile/delegate/overlay; library.py
persiste favoritos/recientes. Fuente en assets/fonts con README/licencia/procedencia.
45 pruebas pasan, incluida persistencia, aislamiento por cuenta y reapertura de
series/episodios. scripts/smoke_library.py: dos favoritos, playback real registrado,
lista conservada y recuperación SQLite tras cierre. Capturas ficticias inspeccionadas
runtime/metro-home.png y metro-player.png (no versionadas). Smokes de video, audio/
subtítulos y stop/reconexión pasan. Wheel incluye Inter y licencia.

Pertenece al [README](../README.md), [arquitectura](architecture.md) y
[memoria del proyecto](../../asistente/projects/tecnomata-iptv/desarrollo.md).

## Temas y controles por fila — 2026-09-16

Selector Tema en Inicio: Springfield (actual), Mcfly (reloj, acero, fuego y 1985),
Retro 80s / 90s (casete/neón) y Dog Eyes (blanco y negro). QSettings guarda sólo
el identificador, en configuración local Tecnomata/IPTV; demo no persiste.
`themes.py` produce las ilustraciones originales Qt de los tres temas nuevos y
paletas. No necesita red; Springfield conserva sus PNG. Dog Eyes convierte
miniaturas a gris sin modificar reproducción. Cuadro actual tiene prioridad.

Volumen agrupa etiqueta/barra/porcentaje 0–100; audio y subtítulos agrupan etiqueta
y selector. Buscador usa X nativa de QLineEdit. FavoriteList intercepta clic izquierdo
en primeros 38 px y evita dobleclic de estrella: ☆/★ por FAVORITE_ROLE, mantiene
identidad/biblioteca/cuenta; se elimina botón inferior. Nombre conserva activación
normal. ChosenContentDelegate pinta estrella y elección usando paleta del tema.

51 pruebas pasan: temas/fondos distintos, fuente conservada, clic estrella sin
playback, búsqueda, porcentaje y restauración con QSettings temporal. Smoke
Wayland de biblioteca/video cambia cuatro temas con mismo motor/fuente; capturas
sintéticas revisadas. Validación visual del proveedor por Arturo pendiente.

## Botones de biblioteca, desplazamiento VOD y fondos raster — 2026-09-16

Estrella por fila dibujada como botón de 30 × 28 px, borde y estrella vectorial
vacía/llena: no depende de la fuente para distinguir estados. Favorito relleno
y mensaje de añadido/quitado. Clic no reproduce; dobleclic estrella bloqueado.
Encabezado de lista tiene botón ‹ para esconderla; pestaña › Lista restaura.

Clic izquierdo en video de película o episodio alterna una barra debajo de la
imagen con tiempo actual/duración. Slider acepta clic, arrastre y teclado;
comando libmpv seek absolute+exact con objetivo limitado a duración. Sólo habilitado
si fuente activa es vod/series (episodios usan playing_kind series), media lista,
duración positiva y seekable. No usar pestaña navegada para decidir. Stop/cambio
reinician barra; TV mantiene Ir al directo. position_changed a 250 ms no reconstruye
listas de pistas. Sin progreso guardado entre ejecuciones todavía.

Fondos nuevos v2: doce PNG, TV/deportes, cine y series por cada tema.
Springfield cartoon; Mcfly set deportivo tecnológico, cockpit DeLorean y salón
de dragones con circuitos; Retro estudio neón, video club y diner de drama criminal;
Dog Eyes estudio, proyector y diner noir monocromos. Referencias decorativas,
no son portadas o fotogramas del catálogo ni identifican proveedor/contenido real.
Generador nativo image_gen; prompts en assets/backgrounds/theme-prompts-v2.json.

53 pruebas y smoke_seek con video nativo ficticio: película y episodio avanzan
a 12 s y retroceden a 3 s en pausa; Stop limpia barra/fuente. No valida seek
con proveedor. scripts/smoke_library conserva prueba de biblioteca y cuatro temas.

Recursos y prompts finales: [fondos por tema](../src/tecnomata_iptv/assets/backgrounds/README.md).
Doce PNG 1024 × 1536 y su inclusión en wheel verificados; capturas de cuatro temas revisadas.

## Estilo del segundo ZIP y consola inferior — 2026-09-16

Referencia nueva: `stitch_delorean_iptv_player.zip` en raíz, guardado como insumo
original. HTML sólo leído; no se ejecutó ni cargaron sus URLs. Se toman colores,
fuentes y estilo de Temporal Stream Deck para Mcfly y Auteur Cinema Telemetry
para Retro, conservando estructura lista/reproductor/Inicio y fondos v2.
Mcfly: chasis #090b0e/#12151b, cian #00f0ff y ámbar #ffb800, Space Grotesk
en títulos y Space Mono en lectura/controles; esquinas de 4 px. Retro: obsidiana
#0c0a09, espresso #171412, rojo #ef4444 y ámbar #f59e0b, Epilogue en títulos,
Space Grotesk en cuerpo y Space Mono en datos; esquinas de 2 px.
Springfield mantiene paleta, fuentes e imágenes; Dog Eyes conserva blanco/negro.
Fuentes oficiales google/fonts incluidas, SIL OFL 1.1 por familia, carga privada
QFontDatabase; sin instalación global ni red al arrancar.

Controles inferiores en panel común: pausa destacada que pasa a Seguir al pausar,
detener/pantalla completa compactos con tooltip/nombre accesible, volumen
alineado con porcentaje, pistas con títulos encima del selector y resolución
separada. Timeline VOD sigue por clic, info/pistas fuera de video. Ocultar lista
se mueve del encabezado a carril dentro del margen derecho, centrado con dos
stretches; › Lista conserva restauración y tamaños. No crea otra lista.

53 pruebas pasan. Smoke seek película/episodio pasa; smoke_library extendido
comprueba centrado (<2px), mismo motor/fuente y capturas sintéticas de reproductor/
Inicio por tema. Una ejecución gráfica simultánea terminó exit139 sin traceback;
dos ejecuciones aisladas posteriores pasaron. Causa no determinada, no atribuida
al diseño ni dada por corregida. Capturas revisadas; wheel incluye fuentes/licencias.
Validación de Arturo con proveedor pendiente.

## Subtítulos ajustables y título en Waybar — 2026-09-16

Arturo observa dos pistas de subtítulos en una película: aparecen tras cambiar
audio/pista y esperar. Esperar al siguiente evento o datos de la pista es posible;
no se inspeccionó el archivo del proveedor, por lo que no se atribuye causa concreta.
No añadir retraso artificial, seek automático ni vincular subtítulos al audio.
Seleccionar sid ahora hace explícita sub_visibility (no la desactiva cambiar audio).

A−/porcentaje/A+ junto al selector: tamaño 50–250%, pasos de 10; sub_scale en
libmpv se aplica en el acto y antes de inicializar si aún no hay motor. QSettings
Tecnomata/IPTV guarda subtitleSizePercent; demo no persiste. No cambiar sid/aid
al ajustar. Botones habilitados si hay pistas. Control orientado a subtítulos
de texto (SRT/ASS); gráficos o texto quemado no equivalen a fuente ajustable.
Manual de referencia: https://mpv.io/manual/stable/#options-sub-scale

La barra retro usa WaybarPlayerLyrics.py → playerctl -a metadata --format
artist/title/status -F; CAVA lee audio por separado, por eso funcionaba el
ecualizador sin título. La app no exportaba MPRIS. mpris.py añade servicio DBus
de sesión org.mpris.MediaPlayer2.tecnomata_iptv.instance<PID>, path estándar.
Publica sólo título del catálogo, trackid sintético, duración/posición, estado
y volumen. Identity indica app; artista vacío para que se muestre sólo título.
Nunca publica xesam:url ni URL del stream, credenciales o metadata cruda MPV.
PropertiesChanged comunica título/estado. Qt signals llevan pause/play/stop/volume/
seek/raise del worker DBus al hilo GUI; no accede al motor desde DBus. Métodos
next/previous/OpenUri no se anuncian como disponibles. Sin bus, playback continúa.
Demo no exporta salvo mpris_enabled=True explícito en smoke. Servicio cierra
con ventana; media terminada/error/Stop limpia título. Requiere dbus-fast 5.0.22,
registrado en pyproject y requirements.lock; no requiere tocar Waybar.
Referencias: https://specifications.freedesktop.org/mpris/latest/Player_Interface.html
y https://dbus-fast.readthedocs.io/en/latest/high-level-service/index.html

56 pruebas pasan. smoke_subtitles usa dos audios/dos SRT ficticios: píxeles
visibles, 150% aumenta ancho >30%, segunda pista tiene primer evento a 5s
y espera al cambiar en 2s; aparece al avanzar a 6s sin cambiar audio. Captura
ficticia revisada. smoke_mpris valida título película/episodio con playerctl,
listener -F activo antes del servicio, controles pause/play/volume/stop y cierre.
No se inspecciona ni valida subtítulos del proveedor. Versión nueva probada,
reproducción real de Arturo se mantiene abierta para no perder posición; activar
actualización al cerrar/reabrir. Progreso aún pendiente.
