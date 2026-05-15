#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
OUT="${OUT:-$HERE/dist}"
mkdir -p "$OUT"

echo "[build] Blender: $BLENDER"
echo "[build] Output:  $OUT"

"$BLENDER" --background --factory-startup \
    --python "$HERE/build_daguerreotype.py" -- \
    --out "$OUT"

echo "[build] done. Artifacts:"
ls -lh "$OUT"
