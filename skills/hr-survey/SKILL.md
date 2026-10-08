---
name: hr-survey
description: Highlight reel stage 2 — extract survey frames + 2 fps thumbnails for every clip in the game folder, detect team-colour players, and build overview and torso-crop ID sheets. No Resolve needed.
---

# hr-survey — frames, detection, sheets

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (the scripts folder, wherever the skill is installed). Shared rules: `$S/../reference/quality-bar.md`.

**Workspace:** if `$ARGUMENTS` names a game, `python3 $S/hrstate.py use "<game>"`. Then `python3 $S/hrstate.py status`. Requires `setup` done (needs `settings.source_folder`); if not, tell the user to run `/hr-setup` and stop.

## Steps
1. **Frames.** `bash $S/survey.sh` (run in background; ~3–5 min for 100+ 4K clips). It first runs `cameras.py assign` (stops if any camera is UNKNOWN — add a camera profile, see /hr-profile) and skips `export`-type clips. Per clip into the workspace: 5 frames at 10/25/50/75/90% (`frames/` 1280w, `frames_4k/` full-res), `info.txt`, and 2 fps thumbnails (`src2fps/`). Clears only this workspace's previous survey.
2. **Calibrate jersey colour — once per encoding present** (`hrstate.py get media.encodings`). The same shirt sits in a different HSV range on Log vs Rec.709 vs HLG footage, so the range is stored per encoding. Skip an encoding when the team profile already has `kits.<kit>.hsv.<encoding>` (`hrprofile.py show team <team_id>`). Otherwise: pick 2–3 frames of that encoding where our shirts are clearly visible, sample shirt pixels with OpenCV (HSV, H 0–180), set a range covering them with margin, and check with `python3 $S/detect.py <frame>` + drawn boxes (shirts boxed; grass, sky, opponents not). Save it to BOTH this game and the team profile so the next game skips this:
   `hrstate.py set calibration.team_hsv.<encoding> '{"lo":[h,s,v],"hi":[h,s,v]}'` and `hrprofile.py set team <team_id> kits.<kit>.hsv.<encoding> '{"lo":[…],"hi":[…]}'`.
   Note the opponent's colours: `hrprofile.py set team <team_id> opponents.<event_name> '{"shirt":"…"}'`.
3. **Detect.** `python3 $S/scan.py` → `sheets/blobs.json` (each clip detected with its own encoding's range) and `media.clips.*.looks` (flat|contrasty). It prints ENCODING MISMATCH for Log clips that look contrasty (camera was in a standard profile) or Rec.709 clips that look flat — fix the clip's encoding (`hrstate.py set media.clips.<clip>.encoding rec709`), re-run scan, and if a whole camera was mis-set, note it on the camera profile.
4. **Sheets.** `python3 $S/crops.py` → `sheets/crops_NN.jpg` (4K torso crops, top 3 team-colour players per frame, 10 clips/sheet). `python3 $S/sheets.py` → `sheets/sheet_N.jpg` overviews.
5. `hrstate.py done survey "<N clips, M sheets, calibration used>"`.

## Done when
`media.clips` count equals the number of video files in the source folder; every clip has 5 frames; sheets exist; detection boxes land on our shirts in a spot check of one crop sheet.

## Known gaps (next optimizations)
- Only 5 samples per clip feed detection — the 2 fps thumbnails aren't scanned yet. On the first real run this missed three of the best clips (a goal and two long dribbles). Plan: scan `src2fps/` for team-colour blob size near camera + motion to rank clips.
- No audio analysis — cheers/whistle peaks are a cheap goal signal.
- Calibration is manual; could auto-fit from shirt boxes.
- AI panoramic cameras (Veo/Trace) need a different survey: one long clip per half, not many short clips.
