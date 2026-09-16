#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
applications_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$applications_dir"
cat > "$applications_dir/tecnomata-iptv.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Tecnomata IPTV
Comment=TV en vivo, películas y series con video integrado
Exec="$project_root/scripts/run.sh"
Icon=video-display
Terminal=false
Categories=AudioVideo;Video;Player;
StartupNotify=true
EOF
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$applications_dir"
fi
