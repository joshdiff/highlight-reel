---
name: hr-export
description: Highlight reel stage 10 — render the delivery timeline to MP4 at the deliverable's spec, verify the file (ffprobe + frames per clip), write the final report, and update the player/team/camera profiles with what this game taught.
---

# hr-export — render, verify, report

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (the scripts folder, wherever the skill is installed). Shared rules: `$S/../reference/quality-bar.md`. Uses the davinci-resolve MCP.

**Workspace:** if `$ARGUMENTS` names a game, `hrstate.py use "<game>"`; then `hrstate.py status`. Requires `grade` and `title` done (if run standalone without them, say so and ask whether to export anyway).

## Steps
1. `render`: `set_format_and_codec` mp4/H264 → `set_mode` 1 → `set_settings` one at a time: TargetDir (`settings.output_folder`), CustomName (`settings.output_name` without .mp4), ExportVideo, ExportAudio, FormatWidth, FormatHeight, FrameRate, VideoQuality (kb/s) → `add_job` → `start` → wait for the file to stop growing → `get_job_status` Complete → `verify_output` with expected_frames.
   - social_reel 1080×1920, 14000 kb/s, 29.97 · recruiting_tape 1920×1080, 25000, 29.97 · goals_reel 1920×1080, 20000, 29.97
   - Never overwrite — if the file exists add `_v2`, `_v3`.
2. Verify the FILE: ffprobe resolution / fps / bitrate / duration; extract one frame per clip (mid-item, from `resolve.items` record frames) into `checks/export_NN.jpg` and look at them — right clip order, grade looks natural, lower third on the teaser.
3. `hrstate.py set export '{"file": "...", "width": .., "height": .., "fps": .., "kbps": .., "duration": ..}'`; `hrstate.py done export`.
4. **Final report:** the file and its stats; each clip with its beat (e.g. "take-on past #4, 7s") and what the camera did; anything uncertain (from stage notes — e.g. a CANDIDATE you couldn't confirm).
5. **Update the profiles** (this is how the next reel gets better — never write these details into the repo):
   - player: fill empty `appearance` fields with identifiers you actually relied on; add new `decoys`; `hrprofile.py note player <id> "<lesson>"` for anything that changed how you worked (a missed clip and why, a camera angle that hid the number); append to `games` {date, event, team_id, deliverable, output file, best_clips {clip: beat}}; add the season to the team membership if missing.
   - team: `kits.<kit>.hsv.<encoding>` already saved by hr-survey; add teammates you identified to `roster`; opponent colours under `opponents`.
   - camera: a note if a camera needed special handling (wrong picture profile, VFR, a CDL that worked).

## Done when
ffprobe matches the spec, the duration matches the delivery timeline, and the extracted frames look right.
