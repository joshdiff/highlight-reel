---
name: hr-assemble
description: Highlight reel deliverable stage (Resolve path) — build this deliverable's timeline(s) in the game's Resolve project, one per aspect (teaser → sequences → finale), from the ORIGINAL clips trimmed in the timeline and framed with Inspector Pan/Tilt/Zoom keyframes (no rendered copies), at the right resolution and 29.97, with dissolves, and verify there are no gaps.
---

# hr-assemble — timelines from the originals

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`. Uses the davinci-resolve MCP.

**Scope: deliverable.** Requires `project` done; open the project in `hrstate.py get resolve.project`.

## How it works
Resolve's scripting API cannot write transform keyframes (`add_keyframe` → "'NoneType' object is not callable" on 21.1), but a timeline IMPORT can carry them. `timeline_export.py` writes one FCPXML per aspect that:
- places each play's ORIGINAL file trimmed to its `select` window (source in/out in the timeline — no copy, no render), using the file's own start timecode so Resolve links it;
- frames it with **Inspector keyframes** — Position X/Y (Pan/Tilt) and Zoom — from vcam's operator path (dead zone, eased follow, whips), reduced to the fewest keys within 3 px of the path. They land on the clip exactly like hand-set keyframes and can be edited in the Inspector;
- holds the teaser's cliffhanger as a **freeze-frame retime** of the original (Resolve shows it as a compound clip in the pool), game sound muted;
- marks each play's beat.

Measured on Resolve Studio 21.1 (synthetic 4K test pattern vs vcam's ffmpeg render of the same shot list): framing within 0 px when the camera holds, ~half a frame of timing during moves; the freeze holds still; imported clips link and render.

## Steps
1. **Write the timelines:** `python3 $S/timeline_export.py` → one `<game>/tmp/timelines/<deliv>_<aspect>.fcpxml` per aspect (scratch), and `deliv.timelines.<aspect>` (name, items, total_s). It refuses an aspect that needs framing but has no shot list (→ hr-direct).
2. **Import each** with `timeline` → `import_timeline_checked` {path, `import_source_clips: true`, `require_temp_path: false`, `timeline_name`: the name printed}. Rules (all measured):
   - `import_source_clips` MUST be true. With false, every item comes in offline — even Resolve's own exported FCPXML of the same files. With true, a clip already in the pool is reused, not duplicated.
   - The name must not exist yet (Resolve returns nothing for a repeat). For a re-run, add " v2", " v3"… (`timeline_export.py --out` with an edited file, or rename the old timeline first); never delete an old timeline.
   - Expect `media.linked == media.total`. Anything offline: check the drive is mounted and the path in `media.clips` is current.
3. **Tidy and colour:** move the timeline to `_SEQUENCES` and the imported source clips to `FOOTAGE` (`media_pool` → `move_clips`). Every source clip whose encoding differs from the project input gets its own "Input Color Space" (`media_pool_item` → `set_clip_property`) from `media.clips.<clip>.encoding` → cameras.py ENCODINGS; read it back. The freeze compound inherits its clip's setting.
4. **Timeline settings:** `timeline` → `set_setting` useCustomSettings=1 and timelineResolutionWidth/Height from the aspect (9:16 1080×1920, 1:1 1080×1080, 4:5 1080×1350, 16:9 1920×1080) if the import didn't set them; read back resolution and timelineFrameRate (29.97).
5. **Blend the cuts between plays:** `timeline_item` → `add_transition` on each play except the last, `options` {"type": "Cross Dissolve", "category": "simple", "position": "end", "alignment": "center", "duration": 6} (0.2s). The originals supply the handle frames, and the shot lists' 0.2s handles keep the framing right through the dissolve. The teaser's freeze hard-cuts into the first play (no dissolve there). Transitions count in `item_index`, so add them from the last cut backwards; read back with `timeline` → `get_items` (kind "transition"). Viewers called straight cuts between plays "choppy".
6. **Brand bumpers** (if the brand has intro/outro clips): import them into `BRAND` and place them first/last.
7. **Check:** `timeline` → `source_range_report`: no gaps, source ranges = the `select` windows, length = `deliv.timelines.<aspect>.total_s` (+ bumpers) ± 0.5s. Capture one frame mid-play per play (`timeline_frame capture`, max_width 270) and compare with the hr-direct contact sheets — same framing.
8. **Write results:** `hrstate.py deliv merge resolve file.json` with `{"timelines": {"9:16": "..."}, "items": {"9:16": [{"item_id": "...", "clip": "...", "role": "play|teaser|freeze", "record_frame": 0, "frames": 75}]}}`. Then `hrstate.py deliv done assemble "<aspects, total s>"`.

Mixed sources: 59.94/29.97 conform cleanly; 24/25 fps clips judder on 29.97, so prefer another angle or accept it and note it in `flags`.

## Done when
For every aspect: all items linked to the original files, no gaps, order teaser → freeze → middle → finale, keyframed framing matching the direct check, a dissolve on every play-to-play cut, length within the target, resolution and fps read back correctly.

## Known gaps
- Keyframes are linear between keys; the follow path's curves need ~10 keys per second of camera movement. Fewer, eased keys (closer to hand keyframing) would be easier to edit.
- The teaser whip blur isn't reproduced in Resolve (hard cut out of the freeze).
- No music track yet. Clip audio is kept as-is (no levels/ducking); the ffmpeg path (`/hr-finish`) does music + loudness.
