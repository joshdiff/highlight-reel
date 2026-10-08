---
name: hr-export
description: Highlight reel deliverable stage — deliver the finished files (render from Resolve, or take the ffmpeg-finished files), name and place them by the client's template, verify each file, report, and write what this deliverable taught back into the player/team/camera profiles.
---

# hr-export — deliver, verify, learn

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`.

**Scope: deliverable.** Requires `finish` done (ffmpeg path) or `grade` + `title` done (Resolve path). Final paths: `python3 $S/naming.py` prints one path per aspect, from the client's template (never overwrites; adds _v2, _v3).

## 1. Produce the files
- **ffmpeg path:** `hr-finish` already wrote `deliv.finish.files {aspect: path}`. Move or copy each to its naming.py path.
- **Resolve path**, per aspect timeline:
  1. `render`: `set_format_and_codec` mp4/H264 → `set_mode` 1;
  2. `set_settings` one at a time: TargetDir and CustomName (from the naming.py path), ExportVideo, ExportAudio, FormatWidth, FormatHeight, FrameRate 29.97, VideoQuality;
  3. `add_job` → `start` → wait for the file to stop growing → `get_job_status` Complete → `verify_output` with expected_frames.

  Bitrates: 9:16 / 1:1 / 4:5 at 14000 kb/s; 16:9 at 20000 (recruiting: 25000).

## 2. Verify every file
- ffprobe: resolution, fps, bitrate, duration ≈ the timeline.
- `python3 $S/gradecheck.py --video <file> --n 8`
- Extract one frame per play into `<deliverable>/checks/export_NN.jpg` and look at them: right order, natural grade, lower third on the teaser, watermark/bumpers present if branded.

Write `hrstate.py deliv set export '{"files": {"9:16": "..."}, "verified": true, "stats": {...}}'` and `hrstate.py deliv done export`.

## 3. Report
Give:
- each file and its stats;
- each play with its beat (e.g. "take-on past #4, 7s") and what the camera did;
- anything uncertain: CANDIDATE clips not confirmed, flags, encoding mismatches, 24 fps judder.

Also add the report's flags to `deliv.flags` so `hrstate.py status` shows them.

## 4. Learn (this is how the next reel gets better)
- **player targets:**
  - `python3 $S/hrprofile.py learn <player_id> --game "<game id>" --target <target>` (idempotent; catches any find edits);
  - then record the outputs: `python3 $S/hrprofile.py output <player_id> "<game id>" <file>…`.
- **client feedback** later ("drop the defensive clip", "more assists"): `hrprofile.py feedback <player_id> keep|drop "<text>" --deliv <id> [--clip C]`. hr-select applies it from then on.
- **team:** add teammates you identified to `roster` and opponent colours under `opponents` (`hrprofile.py set team …`).
- **camera:** a note if a camera needed special handling (wrong picture profile, VFR, a CDL that worked).
- Never write any of this into the repo or the skill files.

## Done when
Every aspect's file is at its naming.py path, verified, and passes gradecheck. The report has been given, and learn has run.
