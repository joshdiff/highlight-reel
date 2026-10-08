#!/bin/bash
# Usage: survey.sh [SOURCE_FOLDER]   (default: settings.source_folder of the current workspace)
# Per clip, into the current workspace: 5 frames at 10/25/50/75/90% (frames/ 1280w, frames_4k/ full-res),
# info.txt (name,width,height,fps,nb_frames,duration) and 2 fps thumbnails (src2fps/).
# Re-running clears only this workspace's survey output. Parallel over clips.
# Clips whose camera profile is type "export" (already-edited renders) are skipped.
S="$(cd "$(dirname "$0")" && pwd)"
WS=$(python3 "$S/hrstate.py" path) || exit 1
SRC="${1:-$(python3 "$S/hrstate.py" get settings.source_folder | python3 -c 'import json,sys;print(json.load(sys.stdin) or "")')}"
[ -d "$SRC" ] || { echo "source folder not found: $SRC"; exit 1; }
FF=$(python3 -c "import sys;sys.path.insert(0,'$S');import hrstate;print(hrstate.tool('ffmpeg'))"); FP=$(python3 -c "import sys;sys.path.insert(0,'$S');import hrstate;print(hrstate.tool('ffprobe'))")
rm -rf "$WS/frames" "$WS/frames_4k" "$WS/src2fps" "$WS/sheets"
mkdir -p "$WS/frames" "$WS/frames_4k" "$WS/src2fps" "$WS/sheets"
one() {
  f="$1"; n=$(basename "$f"); n="${n%.*}"
  mkdir -p "$WS/frames/$n" "$WS/frames_4k/$n" "$WS/src2fps/$n"
  dur=$($FP -v error -show_entries format=duration -of csv=p=0 "$f")
  info=$($FP -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_frames -of csv=p=0 "$f")
  echo "$n,$info,$dur,$f" > "$WS/frames/$n/info.txt"
  i=0
  for p in 0.10 0.25 0.50 0.75 0.90; do
    t=$(python3 -c "print($dur*$p)")
    $FF -nostdin -v error -y -ss "$t" -i "$f" -frames:v 1 -q:v 2 "$WS/frames_4k/$n/frame_$i.jpg"
    $FF -nostdin -v error -y -i "$WS/frames_4k/$n/frame_$i.jpg" -vf scale=1280:-2 -q:v 3 "$WS/frames/$n/frame_$i.jpg"
    i=$((i+1))
  done
  $FF -nostdin -v error -hwaccel videotoolbox -i "$f" -an -vf "fps=2,scale=480:270" -q:v 5 "$WS/src2fps/$n/t_%04d.jpg"
}
export -f one; export FF FP WS
# camera detection first (fast, metadata only): unknown cameras stop the survey; export-type clips are skipped
python3 "$S/cameras.py" assign "$SRC" || exit 1
python3 - "$S" <<'PY' | tr '\n' '\0' | xargs -0 -P 6 -I{} bash -c 'one "$@"' _ {}
import sys; sys.path.insert(0, sys.argv[1]); import hrstate
for c in (hrstate.get('media.clips') or {}).values():
    if c.get('use', True): print(c['path'])
PY
echo "workspace: $WS"
echo "clips: $(ls "$WS/frames" | wc -l | tr -d ' ')  frames: $(find "$WS/frames" -name 'frame_*.jpg' | wc -l | tr -d ' ')"
