---
name: hr-config
description: Highlight reel — one-time machine setup (output folder, media root, default grade, ffmpeg, Python deps, Resolve MCP check, library migration). Run after cloning or installing the plugin; re-run to change any of it.
---

# hr-config — machine settings

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`

Machine settings live in `~/.hr_work/config.json` (set `HR_HOME` to move everything). They're local to this computer and never in the repo. `install.sh` asks the same questions in a terminal; this is the in-Claude version.

| key | what |
|---|---|
| `output_folder` | where finished reels go by default, and the work area `_hr/` (sessions, games, deliverables) |
| `media_root` | folder holding `<season>/<team>/<game>/` footage (used for pick-lists; any folder works) |
| `power_grade_drx` | default .drx for the Resolve path (optional) |
| `output_template` | default file naming when a client has none, e.g. `{team}/{date} {event}/{who}_{type}_{aspect}.mp4` |
| `ffmpeg`, `ffprobe` | binaries (default: PATH, then `/opt/homebrew/bin`) |

## Steps
1. `python3 $S/hrstate.py config`. If `$ARGUMENTS` gives a key/value, set just that and stop.
2. **Upgrade:** if `~/.hr_work/players`, `teams` or `cameras` exist (pre-1.0 layout), run `python3 $S/migrate.py`. It moves them into `~/.hr_work/library/` and makes a backup.
3. **Dependencies:** check and report each:
   - ffmpeg/ffprobe (`hrstate.tool`), and whether the build has `lut3d`, `loudnorm` and `sidechaincompress` (needed by /hr-finish);
   - Python: `python3 -c "import cv2, numpy, scipy, PIL"`. Fix with `python3 -m pip install --user opencv-python numpy scipy pillow`;
   - the DaVinci Resolve MCP (ToolSearch for `mcp__davinci-resolve__`). It's only needed for the Resolve path; the ffmpeg path works without it.
4. Ask (one AskUserQuestion round) only for missing settings: output folder, media root (look in `/Volumes` and home for `<season>/<team>/<game>` structures), default grade. Save each with `hrstate.py config KEY VALUE`.
5. Show the config and the library (`hrprofile.py list`, `library.py list`, `cameras.py list`). Next steps: `/hr-library` to add clients, brands, players and cameras; `/hr-session` to plan a day.
