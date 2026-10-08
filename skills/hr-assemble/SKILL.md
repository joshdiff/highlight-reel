---
name: hr-assemble
description: Highlight reel deliverable stage (Resolve path) — build this deliverable's timeline(s) in the game's Resolve project, one per aspect (teaser → sequences → finale), at the right resolution and 29.97, and verify there are no gaps.
---

# hr-assemble — timelines

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`. Uses the davinci-resolve MCP.

**Scope: deliverable.** Requires `project` done; open the project in `hrstate.py get resolve.project`.

## How append works
`media_pool` → `append_to_timeline` needs, per clip: `clip_id`, `start_frame`, `end_frame` (source frames), `record_frame` (relative) and `track_index`.
- Source frame = round(source_seconds × source_fps), with fps from `media.clips`.
- record_frame accumulates in timeline frames = round(source_frames / source_fps × 29.97).
- Reframes are already trimmed: use 0 → (frame count − 1).

Mixed sources: 59.94/29.97 conform cleanly; 24/25 fps clips judder on 29.97, so prefer another angle or accept it and note it in `flags`. VFR phone clips used directly (16:9 from 16:9) should first be transcoded to constant-rate ProRes in `<deliverable>/reframed/` and imported instead of the original.

## Steps
1. **Per aspect**, create `<deliv id>_<aspect>` (e.g. `alex-social_9x16`) in `_SEQUENCES`. Then `timeline` → `set_setting` useCustomSettings=1 and timelineResolutionWidth/Height from the aspect (9:16 1080×1920, 1:1 1080×1080, 4:5 1080×1350, 16:9 1920×1080). Read back the resolution and timelineFrameRate (29.97).
2. **Content in `select` order:**
   - reframed aspects: the teaser reframe → each sequence's reframe (finale last);
   - 16:9 from 16:9 footage: the originals trimmed to the `select` windows.

   Cuts only; the teaser carries its own whip-out.
3. **Brand bumpers** (if the deliverable has a brand with intro/outro clips): import them into `BRAND` and place them first/last.
4. `timeline` → `source_range_report`: no gaps, ranges as planned, length = `select.total_s` (+ bumpers) ± 0.5s.
5. **Write results:** `hrstate.py deliv merge resolve file.json` with `{"timelines": {"9:16": "..."}, "items": {"9:16": [{"item_id": "...", "clip": "...", "record_frame": 0, "frames": 75}]}}`. Then `hrstate.py deliv done assemble "<aspects, total s>"`.

## Done when
For every aspect: no gaps, order teaser → middle → finale, length within the target, resolution and fps read back correctly.

## Known gaps
- No music track yet. Clip audio is kept as-is (no levels/ducking); the ffmpeg path (`/hr-finish`) does music + loudness.
