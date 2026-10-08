---
name: hr-assemble
description: Highlight reel stage 7 — build the selects timeline and the delivery timeline in Resolve (teaser → sequences → full goal), at the deliverable's resolution and 29.97, and verify there are no gaps.
---

# hr-assemble — timelines

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (the scripts folder, wherever the skill is installed). Shared rules: `$S/../reference/quality-bar.md`. Uses the davinci-resolve MCP.

**Workspace:** if `$ARGUMENTS` names a game, `hrstate.py use "<game>"`; then `hrstate.py status`. Requires `project` done. Make sure the Resolve project in `resolve.project` is open.

## How append works
`media_pool` → `append_to_timeline` needs per clip `clip_id`, `start_frame`, `end_frame` (source frames), `record_frame` (relative), `track_index`. Source frame = round(source_seconds × source_fps) (fps from `media.clips`). record_frame accumulates in timeline frames = round(source_frames / source_fps × 29.97). Reframed clips are already trimmed: use 0 → (frame count − 1).

## Steps
1. **Selects** `_SELECTS_[player_number|Team]_[event_name]` (in `_SEQUENCES`): 1920×1080 from the ORIGINAL clips trimmed to each `select.sequence` window — kept for later re-use.
2. **Delivery** `[deliverable_type]_[event_name]`: create, then `timeline` → `set_setting` useCustomSettings=1, timelineResolutionWidth/Height (1080×1920 social; 1920×1080 otherwise). Read back resolution and timelineFrameRate (29.97 from hr-project — 59.94 sources conform cleanly; 24 judders).
   - social_reel: teaser reframe → each `select.sequence` reframe in order (finale last). Cuts only — the teaser carries its own whip-out.
   - 16:9: the original clips trimmed to the `select.sequence` windows.
3. `timeline` → `source_range_report`: no gaps, ranges as planned, total length = `select.total_s` ± 0.5s.
4. Write results: `hrstate.py merge resolve file.json` with `{"timelines": {"selects": "...", "delivery": "..."}, "items": [{"item_id": "...", "clip": "R7__1630_teaser", "record_frame": 0, "frames": 75}, ...]}` — `items` is the delivery timeline's video items in order. Then `hrstate.py done assemble "<N items, total s>"`.

## Done when
No gaps; order teaser → middle → finale; length within target; resolution/fps read back correctly.

## Known gaps
- No music track yet (bin exists). Audio from the clips is kept as-is; no levels/ducking.
