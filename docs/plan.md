# Contrato de producto y fases

## Objetivo autorizado

Reemplazar el uso incómodo de IPTVnator + MPV externo con una app personal Linux
familiar para Arturo: TV en vivo, películas, series y reproducción en la misma
ventana. El proveedor actual acepta servidor, usuario y contraseña (Xtream).
Cambiar de canal debe reemplazar el contenido de una sola instancia de libmpv.
No debe aparecer una segunda ventana MPV ni aplicarse su regla flotante de Hyprland.
La app utiliza ventanas opacas; verificar la opacidad efectiva en el compositor.

## Alcance final

- Cuenta Xtream, validación y mensajes comprensibles, almacenamiento seguro optativo.
- TV: categorías, búsqueda, favoritos, guía EPG disponible y cambio de canal.
- Películas: categorías, búsqueda, portadas, ficha, reproducción y progreso.
- Series: categorías, búsqueda, ficha, temporadas, episodios y progreso.
- Video integrado, pausa, volumen, seek para VOD, pantalla completa, audio/subtítulos.
- Recuperación frente a red caída, timeout, formato incompatible y cierre correcto.
- Lanzador Linux y entorno reproducible; código versionado y documentación retomable.

## Fases y puertas de aceptación

| Fase | Trabajo | Evidencia necesaria para cerrar |
|---|---|---|
| 0 | Repo, estructura, contrato, fases y memoria | Arranque y cadena documental completos |
| 1 | Cliente Xtream y consultas sin bloquear Qt | Mocks: acceso válido/rechazado, errores saneados, tres catálogos y episodios |
| 2 | Prototipo Qt y un único video integrado | Dos videos locales alternados repetidamente; mismo motor/widget, frames reales, cero ventanas MPV |
| 3 | Validación del servicio de Arturo | Acceso real; canal, película y episodio; cambios sucesivos y audio, sin filtrar datos |
| 4 | Experiencia completa | Portadas/fichas, temporadas navegables, EPG, favoritos, progreso y controles de pistas |
| 5 | Estabilidad y entrega | Pruebas de desconexión/reconexión, cierre, catálogos grandes, empaquetado y remoto |

Cada sesión actualiza `SESSION.md` con qué está probado, qué falta y comando para
seguir. Si falta un insumo privado, continuar tareas independientes y dejar la
validación dependiente explícitamente pendiente.

## Estado de fases

0–3 completas; Arturo confirma video real de canales (y cambios), película y serie.
Fase 4 iniciada: precarga/caché en RAM de tres secciones y episodios, cuenta en
GNOME Keyring y restauración automática implementadas. Favoritos/recientes y audio/subtítulos implementados. Fichas/portadas, temporadas
navegables, EPG, progreso y seek siguen pendientes.

## Límites y criterio de cambio

No incluye DRM, grabación, catch-up, múltiples cuentas ni publicación comercial
en el primer alcance. Formatos y funciones dependen del proveedor. No prometer
fecha ni equivalencia completa con Smarters sin validación real.
Si la fase 2 falla en Wayland/OpenGL, resolver el motor antes de pulir la interfaz.
Si fase 3 falla, aislar API, transporte y formato antes de agregar funciones.
No convertir esta herramienta de ocio en una prioridad comercial del ecosistema.

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

Fase 4 avanza con información externa de resolución/fps/códec y selección de
audio/subtítulos; lista más compacta y tipografía inspirada en macOS. 37 pruebas
y smoke real de pistas ficticias pasan; validación del proveedor por Arturo pendiente.

Stop con pantalla negra e Ir al directo (reconexión de fuente live activa)
implementados; 39 pruebas y smoke real de cierre HTTP/framebuffer pasan.
No promete eliminar el retraso del proveedor; Arturo valida con canal deportivo.

Inicio/reproductor adaptados al ZIP Metro de Arturo: ver design.md. Favoritos
y últimos100 exitosos guardados localmente por cuenta; 45 pruebas, smoke real de
biblioteca y captura ficticia. Progreso/portadas/EPG pendientes; no telemetry falsa.

## Ajuste visual Springfield — 2026-09-16

Inicio conserva tres ejemplos locales incluso sin reproducción. Favoritos y últimos
se muestran sólo cuando existen datos. Navegación en cápsula y pestaña lateral
restauran la lista sin cambiar el motor. Ver [diseño](design.md).

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
