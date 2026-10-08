#!/bin/bash
# highlight-reel installer: checks dependencies, writes this machine's settings (~/.hr_work/config.json,
# or $HR_HOME) and links the skills into ~/.claude/skills so they run as /highlight-reel, /hr-setup, …
# Re-run any time. Nothing here is committed to the repo. (Plugin installs: run /hr-config in Claude instead.)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; S="$HERE/skills/highlight-reel/scripts"; DEST="$HOME/.claude/skills"
cfg() { python3 "$S/hrstate.py" config "$@"; }
ask() {  # ask KEY "Question" [default]
  local cur; cur=$(cfg "$1" | python3 -c 'import json,sys;print(json.load(sys.stdin) or "")')
  local def="${cur:-$3}"; read -r -p "$2${def:+ [$def]}: " v; v="${v:-$def}"
  [ -n "$v" ] && cfg "$1" "$v"
}

echo "== dependencies"
ok=1
for t in ffmpeg ffprobe; do
  p=$(command -v $t || ls /opt/homebrew/bin/$t 2>/dev/null || true)
  if [ -n "$p" ]; then echo "  $t: $p"; else echo "  $t: MISSING (brew install ffmpeg)"; ok=0; fi
done
if python3 -c "import cv2, numpy, scipy, PIL" 2>/dev/null; then echo "  python: cv2 numpy scipy pillow OK"
else echo "  python: missing modules → python3 -m pip install --user opencv-python numpy scipy pillow"; ok=0; fi
echo "  DaVinci Resolve + a Resolve MCP server are only needed for the Resolve finishing path."

for f in lut3d loudnorm sidechaincompress; do
  ff=$(command -v ffmpeg || echo /opt/homebrew/bin/ffmpeg)
  $ff -hide_banner -filters 2>/dev/null | grep -q " $f " || { echo "  ffmpeg lacks the $f filter (needed by /hr-finish)"; ok=0; }
done

echo "== library"
if [ -d "${HR_HOME:-$HOME/.hr_work}/players" ] || [ -d "${HR_HOME:-$HOME/.hr_work}/cameras" ]; then
  python3 "$S/migrate.py"
fi
mkdir -p "${HR_HOME:-$HOME/.hr_work}/library"/{players,teams,cameras,clients,brands}

echo "== this machine's settings (Enter keeps the value in brackets)"
ask media_root      "Media root (holds <season>/<team>/<game>/ folders)"
ask output_folder   "Output folder (finished reels + the _hr/ work area)"
ask power_grade_drx "Default power-grade .drx (optional)"
for t in ffmpeg ffprobe; do p=$(command -v $t || ls /opt/homebrew/bin/$t 2>/dev/null || true); [ -n "$p" ] && cfg $t "$p"; done

echo "== linking skills into $DEST"
mkdir -p "$DEST"
for d in "$HERE"/skills/*/; do
  n=$(basename "$d")
  if [ -e "$DEST/$n" ] && [ ! -L "$DEST/$n" ]; then echo "  skip $n: $DEST/$n exists and is not a link"; continue; fi
  ln -sfn "${d%/}" "$DEST/$n" && echo "  /$n"
done

echo "== next"
echo "  In Claude Code: /hr-library (clients, brands, players, teams, cameras), then /hr-session to plan a day"
[ $ok = 1 ] || echo "  (install the missing dependencies above first)"
