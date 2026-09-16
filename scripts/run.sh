#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -d "$project_root/runtime/libmpv/usr/lib64" ]]; then
  export LD_LIBRARY_PATH="$project_root/runtime/libmpv/usr/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
exec "$project_root/.venv/bin/tecnomata-iptv" "$@"
