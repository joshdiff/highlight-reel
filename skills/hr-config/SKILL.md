---
name: hr-config
description: Highlight reel — one-time install/machine setup (media root, output folder, power-grade .drx, ffmpeg, Python deps, Resolve MCP check). Run after cloning or installing the plugin; re-run to change any of it.
---

# hr-config — install & machine settings

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`

Machine settings live in `~/.hr_work/config.json` (override the folder with `HR_HOME`) — local to this computer, never in the repo. `install.sh` asks the same questions in a terminal; this is the in-Claude version.

## Settings
| key | what | example |
|---|---|---|
| `media_root` | folder holding `<season>/<team>/<game>/` clip folders | `/Volumes/Footage/Media` |
| `output_folder` | where reels and per-game workspaces (`_hr/`) go | `/Volumes/Footage/Output` |
| `power_grade_drx` | default power-grade .drx (optional) | `~/Grades/MyFixedNodeTree.drx` |
| `ffmpeg`, `ffprobe` | binaries (default: PATH, then `/opt/homebrew/bin`) | |

## Steps
1. `python3 $S/hrstate.py config` — show what's set. If `$ARGUMENTS` names a key/value, set just that and stop.
2. **Dependencies** — check and report each: `ffmpeg -version`, `ffprobe -version` (resolve via `hrstate.tool`), `python3 -c "import cv2, numpy, scipy, PIL"` (fix: `python3 -m pip install --user opencv-python numpy scipy pillow`), and the DaVinci Resolve MCP (ToolSearch for `mcp__davinci-resolve__` tools; if absent, say the Resolve stages 6–10 need it — stages 1–5 work without).
3. Ask (one `AskUserQuestion` round) only for missing settings: media root (offer mounted volumes / folders that contain `<season>/<team>/<game>` structure — look with `ls /Volumes`), output folder, grade .drx (offer "none"). Save each: `python3 $S/hrstate.py config KEY VALUE`.
4. **Cameras** — `python3 $S/cameras.py list`. If none, probe one recent game folder (`python3 $S/cameras.py probe <folder>`) and create a profile per camera found (see `/hr-profile` → cameras); ask the user which camera and colour profile (Log / HDR / standard) each unknown group is.
5. Show the final config, the profiles that exist (`hrprofile.py list`, `cameras.py list`), and suggest `/hr-profile` to add a player and `/highlight-reel` to make a reel.
