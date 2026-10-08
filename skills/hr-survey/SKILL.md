---
name: hr-survey
description: Highlight reel game stage — survey every usable clip/segment of a game once (frames, 2 fps thumbnails), calibrate each team's shirt colour per footage encoding (saved to the team profile), detect both teams' players and build overview sheets. Shared by every target and deliverable of the game. No Resolve needed.
---

# hr-survey — frames, shirt calibration, detection

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`.

**Scope: game.** `python3 $S/hrstate.py status`; `hrstate.py use game "<game>"` if `$ARGUMENTS` names one. Requires game stage `ingest` done (cameras assigned, long files segmented). This is the expensive step; it runs once per game, however many players, teams and deliverables come from it.

## Steps
1. **Frames.** `python3 $S/survey.py` (run in the background; ~3–5 min per 100 4K clips/segments). For every usable clip, sampled within the segment's own time range:
   - 5 frames at 10/25/50/75/90% → `frames/` (1280w) and `frames_4k/` (full res);
   - 2 fps thumbnails → `src2fps/`.

   It skips `export`-type clips and clips already surveyed. `--only CLIP…` redoes specific clips.
2. **Calibrate shirt colours: each team that has a target, once per encoding present** (`hrstate.py get media.encodings`). The same shirt sits in a different HSV range on Log, Rec.709 and HLG footage.
   - **Skip** when the team profile already has it: `hrprofile.py show team <team_id>` → `kits.<kit>.hsv.<encoding>`.
   - **Otherwise:**
     1. Pick 2–3 frames of that encoding where the shirts are clearly visible.
     2. Sample shirt pixels with OpenCV (HSV, H 0–180) and set a range covering them with margin.
     3. Check with `python3 $S/detect.py <frame>` plus drawn boxes: shirts boxed; grass, court, sky, crowd, banners and the other team not.
   - **Save it to both places**, so the next game with this kit skips it:
     ```
     hrstate.py set calibration.team_hsv.<side>.<encoding> '{"lo":[h,s,v],"hi":[h,s,v]}'
     hrprofile.py set team <team_id> kits.<kit>.hsv.<encoding> '{"lo":[…],"hi":[…]}'
     ```
     A team without a profile (e.g. an opponent nobody ordered reels for) needs no calibration unless it has a target. Note its shirt colour on the target team's profile: `hrprofile.py set team <team_id> opponents.<name> '{"shirt":"…"}'`.
3. **Detect.** `python3 $S/scan.py` → `sheets/blobs_<side>.json` for every calibrated team. It also flags ENCODING MISMATCH: a Log clip that looks contrasty, or Rec.709 that looks flat (the camera's picture profile was set differently). Fix with `hrstate.py set media.clips.<clip>.encoding <enc>`, re-run scan, and if the whole camera was mis-set, add a note to the camera profile.
4. **Overview sheets.** `python3 $S/sheets.py` → `sheets/sheet_N.jpg`. Crop sheets are made per target in hr-find (`crops.py --team <side>`).
5. `hrstate.py done survey "<N clips, encodings, teams calibrated>"`.

## Done when
Every usable clip has 5 frames and thumbnails; every team with a target is calibrated for every encoding; a spot check of one crop sheet shows boxes on shirts.

## Known gaps (next optimizations)
- Only the 5 samples feed detection; the 2 fps thumbnails aren't scanned yet. Planned: rank clips by team-colour size near camera + motion + audio peaks.
- Calibration is manual. It could auto-fit from boxes the user confirms once per kit.
