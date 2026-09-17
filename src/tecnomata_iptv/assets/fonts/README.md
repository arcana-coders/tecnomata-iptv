# Inter Variable 4.1

Fuente sin modificar del release oficial [rsms/inter v4.1](https://github.com/rsms/inter/releases/tag/v4.1),
archivo Inter-4.1.zip / InterVariable.ttf. Licencia SIL OFL 1.1 en LICENSE.txt.
SHA256: 4989b125924991b90d05b2d16e0e388c48f7d5bb8b30539bbf9c755278d0ccaf.
Carga privada al proceso Qt con QFontDatabase.addApplicationFont, sin instalación
global ni descarga al abrir app. Padre: README del repo y docs/design.md.

## Fuentes de los estilos del ZIP nuevo

Space Grotesk variable, Space Mono Regular y Epilogue variable se incluyen
privadamente y se cargan desde QFontDatabase. Descargadas de google/fonts oficial
(main/ofl/spacegrotesk, spacemono, epilogue); cada archivo tiene licencia SIL OFL
1.1 junto a él (`spacegrotesk-OFL.txt`, `spacemono-OFL.txt`, `epilogue-OFL.txt`).
Mcfly usa Space Grotesk/Space Mono; Retro usa Epilogue/Space Grotesk/Space Mono.
Springfield/Dog Eyes conservan Inter. No se instalan fuentes globalmente.
