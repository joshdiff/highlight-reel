---
name: hr-survey
description: Highlight reel stage 2 — extract survey frames + 2 fps thumbnails for every clip in the game folder, detect team-colour players, and build overview and torso-crop ID sheets. No Resolve needed.
---

# hr-survey — frames, detection, sheets

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (the scripts folder, wherever the skill is installed). Shared rules: `$S/../reference/quality-bar.md`.

**Workspace:** if `$ARGUMENTS` names a game, `python3 $S/hrstate.py use "<game>"`. Then `python3 $S/hrstate.py status`. Requires `setup` done (needs `settings.source_folder`); if not, tell the user to run `/hr-setup` and stop.

## Steps
1. **Frames.** `bash $S/survey.sh` (run in background; ~3–5 min for 100+ 4K clips). Per clip into the workspace: 5 frames at 10/25/50/75/90% (`frames/` 1280w, `frames_4k/` full-res), `info.txt`, and 2 fps thumbnails (`src2fps/`). Clears only this workspace's previous survey.
2. **Calibrate jersey colour** (skip when the shirts are light blue on Canon Log 3 — the default range — or `calibration.team_hsv` is already set). Pick 2–3 frames where our team's shirts are clearly visible, sample shirt pixels with OpenCV (HSV, H 0–180), and set a range covering them with margin: `hrstate.py set calibration.team_hsv '{"lo":[h,s,v],"hi":[h,s,v]}'`. Check by running `python3 $S/detect.py <frame>` and drawing the boxes: shirts boxed, grass/sky/opponents not. Also note the opponent's colours in `calibration.opponent` (text).
3. **Detect.** `python3 $S/scan.py` → `sheets/blobs.json` and `media.clips` (path, size, fps, frames, duration per clip).
4. **Sheets.** `python3 $S/crops.py` → `sheets/crops_NN.jpg` (4K torso crops, top 3 team-colour players per frame, 10 clips/sheet). `python3 $S/sheets.py` → `sheets/sheet_N.jpg` overviews.
5. `hrstate.py done survey "<N clips, M sheets, calibration used>"`.

## Done when
`media.clips` count equals the number of video files in the source folder; every clip has 5 frames; sheets exist; detection boxes land on our shirts in a spot check of one crop sheet.

## Known gaps (next optimizations)
- Only 5 samples per clip feed detection — the 2 fps thumbnails aren't scanned yet. On the first real run this missed three of the best clips (a goal and two long dribbles). Plan: scan `src2fps/` for team-colour blob size near camera + motion to rank clips.
- No audio analysis — cheers/whistle peaks are a cheap goal signal.
- Calibration is manual; could auto-fit from user-confirmed shirt boxes.
