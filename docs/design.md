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
