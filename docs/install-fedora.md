# Instalación y recuperación — Fedora 44

Pertenece al [README](../README.md) y a [arquitectura](architecture.md).
Entorno probado: Fedora 44, Hyprland/Wayland, Python 3.14 y OpenGL funcional.

## Clonar y preparar Python

```bash
cd /home/tecnomata/tecnomata
git clone -o gitea ssh://git@192.168.1.175:2222/arturo/tecnomata-iptv.git
cd tecnomata-iptv
python -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install -e .
```

El clone usa rama `main`. Mantener memoria `asistente` como repo hermano para
los enlaces locales. `AGENTS.md` es un enlace a `CLAUDE.md`.

## libmpv

Preferir el paquete nativo `mpv-libs` de Fedora si está instalado. El ejecutable
`mpv` por sí solo no garantiza tener la biblioteca que necesita esta app.
En este equipo se eligió una extracción local del RPM oficial sin sudo, porque
el sistema ya tiene las dependencias multimedia. Reproducir desde el repo:

```bash
mkdir -p runtime/libmpv
curl --fail --location --connect-timeout 10 --max-time 60 --output runtime/mpv-libs.rpm https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/os/Packages/m/mpv-libs-0.41.0-5.fc44.x86_64.rpm
rpm -K runtime/mpv-libs.rpm
# Continuar sólo si rpm verifica correctamente firmas y digests.
rpm2cpio runtime/mpv-libs.rpm | cpio -idm --directory runtime/libmpv
ln -sfn libmpv.so.2 runtime/libmpv/usr/lib64/libmpv.so
ldd runtime/libmpv/usr/lib64/libmpv.so.2
```

Si ldd muestra dependencias faltantes, resolver con paquetes adecuados al sistema;
no copiar bibliotecas arbitrarias. El RPM es para Fedora 44 x86_64 y no un bundle
universal. Arquitectura registra procedencia/verificación del equipo original.
`run.sh` usa LD_LIBRARY_PATH local sólo en el proceso de la app.

## Cuenta recordada y arranque

Necesita servicio `org.freedesktop.secrets` disponible en la sesión del usuario.
En el equipo probado lo proporciona GNOME Keyring, desbloqueado con la sesión.
Si el almacén está bloqueado, Linux puede pedir desbloquearlo. No configurar un
backend de keyring en archivos de texto como sustituto.

```bash
./scripts/install-desktop.sh
./scripts/run.sh
```

Conectar mi servicio → introducir cuenta → Recordar mi cuenta activado.
La app guarda después de auth válida y autoentra al abrir. La cuenta es local,
no viene de Gitea. Olvidar cuenta borra el secret y cierra la cuenta/caché.
TV/películas/series se precargan en RAM; Actualizar listas las renueva.

## Pruebas y reanudación

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q
```

Actualmente 62 pruebas. Los mocks, nombres y cuentas de los tests son ficticios.
Las pruebas gráficas requieren sesión Wayland/X11 y videos locales; ver
[diagnóstico de playback](playback-troubleshooting.md). No subimos videos, RPM,
capturas ni entornos Python: viven en runtime/.venv, ignorados por Git.

Leer [SESSION](SESSION.md) antes de continuar fases. Para actualizar:

```bash
git pull --ff-only gitea main
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install -e .
```

No se ha validado instalación/ejecución en Windows ni en otra distribución Linux.

## Datos y diseño nuevos

Inter incluida en paquete, no instalación de fuentes global. ZIP de diseño original
y docs/design.md versionados. Favoritos/recientes son locales en XDG_DATA_HOME/
tecnomata-iptv/library.sqlite3 (default ~/.local/share/tecnomata-iptv/), no Git.
Para migrar biblioteca copiar ese archivo con app cerrada y conservar modo600;
reconectar la misma cuenta recupera scope. Secret Service se prepara aparte,
SQLite no contiene contraseña/servidor/usuario ni URLs. Progreso VOD/episodios implementado, con migración aditiva automática; ver [progreso](progress.md).

Los tres fondos originales de Inicio vienen empaquetados con la app; no requieren
descargas ni reproducción. Ver [diseño](design.md).

MPRIS requiere DBus de sesión y dbus-fast (incluido en requirements.lock).
Actualizar dependencias del venv después del pull. No cambiar Waybar. Preferencia
de tamaño de subtítulos vive en QSettings local, igual que el tema.
