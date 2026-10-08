---
name: hr-ingest
description: Highlight reel game stage — turn a game's footage into clips: assign each file's camera and colour encoding, and split long continuous recordings (tripod halves, AI-camera full matches) into candidate moments using motion, crowd and whistle signals or the AI camera's event tags.
---

# hr-ingest — footage → clips

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`.

**Scope: game.** `hrstate.py status`; `use game "<game>"` if named.

## Steps
1. `python3 $S/cameras.py assign`. This probes every source of the game into `media.files`. Each short file becomes one clip (whole file); long files (longer than the pack's `segmentation.max_clip_s`) are listed in `media.long_files`. If any camera is UNKNOWN, stop this game, flag it (`hrstate.py set flags '["unknown camera: …"]'`) and move on; /hr-session or /hr-library adds the camera.
2. **Long files** (if `media.long_files` is non-empty):
   - **AI camera with an event-tag export** (Veo/Trace/Pixellot CSV or JSON): `python3 $S/segment.py --tags <file> --file <file id> [--offset SEC]`. Check the offset by viewing one tagged moment: if the tag time doesn't line up with the action, measure the shift and re-run with `--offset`.
   - **Otherwise:** `python3 $S/segment.py` (all long files; ~1 min per 10 min of footage). Each file gets ranked segments around motion + crowd + whistle peaks, padded by the pack's pre/post roll and capped at its `candidates_per_min`.
   - Read the plot `checks/segments_<file>.png`: candidates (green) should sit on the peaks, spread across the game and not bunched into one stretch. If a half has none, re-run with a higher `--per-min` for that file.
   - The segments are now ordinary clips (`<file>@<start>`) for survey and find. Times stay source-file seconds.
3. Note mixed frame rates (24/25 fps), VFR phone clips and portrait clips in the game note; later stages handle them.
4. `hrstate.py done ingest "<N files, M clips (K from segmentation), cameras>"`.

## Done when
No UNKNOWN cameras; every long file is segmented (or tagged); `media.clips` holds every usable clip.

## Known gaps
- **Unproven on real long recordings.** On a synthetic stand-in (one game's clips joined in shooting order with filler gaps), the segments covered the game's best plays only by taking ~50% of the file, with precision barely above random (78% vs 72% play). The first real continuous recording should be evaluated against short clips shot at the same game, before any tuning.
- Signals are generic. Sport-specific detectors would sharpen recall: ball-through-hoop, a volleyball hitting the floor, a scoreboard change.
- Very long files are decoded once at low resolution; a 90-minute 4K file takes several minutes.
