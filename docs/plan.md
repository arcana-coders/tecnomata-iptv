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
