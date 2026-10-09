---
name: hr-direct
description: Highlight reel deliverable stage — direct each selected play (who the frame follows, shot by shot, by the sport pack's director rules) as a shot list for every requested aspect (9:16, 1:1, 4:5, 16:9) and check the subject stays in frame. The Resolve path turns it into Inspector keyframes on the original clip (no render); the ffmpeg path renders it with vcam.py.
---

# hr-direct — shot lists and the virtual camera

**Never copy the footage.** The shot list is the framing; on the Resolve path it becomes Pan/Tilt/Zoom keyframes on the original clip in the timeline (hr-assemble), exactly as an editor would keyframe it by hand. Only the ffmpeg path renders, into scratch that is deleted when the session is cleaned.

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`.

**Scope: deliverable.** `python3 $S/hrstate.py status`; `use deliv <id>` if named. Requires `select` done. Read `hrstate.py deliv get select` and `deliv get aspects`. **Director rules: the "Director rules" table in `$S/../../../sports/<sport>/pack.md`.** Follow it exactly; it decides who the frame follows at every moment.

**What gets directed:** every aspect that differs from the source's own shape. A 16:9 deliverable from 16:9 footage needs no framing: re-check each window against the director rules (a scoring clip runs through the reaction, a pass clip through the reception), fix windows in `select` if needed, and mark done. 9:16, 1:1 and 4:5 always render.

## 1. Shot list per play
`<deliverable>/shotlists/<clip>.json` (`hrstate.py deliv path shotlists`), schema in the `vcam.py` docstring:
- `src`: the clip id.
- `in`/`out_t`: the window from `select`, in source-file seconds.
- `aspect`: one of the deliverable's aspects. For several aspects, write one shot list each (`<clip>_1x1.json` …). Wider aspects need fewer keys because more stays in frame.

Make a 5 fps grid over the window, `python3 $S/vgrid.py <clip> <in> <out> <clip>.jpg`, and read positions off its 0–100 ruler (source width). Add a key at every change of subject or direction, and every ~0.4–0.8s while the subject moves; add more keys during fast motion. Each key may set `y` (0–100) when the action moves vertically (volleyball attacks, basketball rims). Otherwise set the shot list's default `y` to the subject's vertical position.

Then **track the on-ball phase densely:** `python3 $S/track.py <shotlist>` follows the player at 8 fps from `in` to the first ball key or `"move":"fast"` (the shot or pass) and replaces your player keys there, keeping their zoom and every key after. Hand-read keys at 2–5 fps lose a close subject when the operator swings fast (in testing, a close take-on lost the player from the 9:16 window four times with 2 fps keys; tracked, they stayed in every sample). Pass `--x0 X` when the first frame has a decoy nearer the centre (e.g. an opponent with the same number). Run it before the check; the contact sheet still decides.

**Constraints (all sports):**
- The subject stays inside the middle 60% of the window, except during a ≤0.25s whip (`"move":"fast"`).
- Never chase a subject the camera operator didn't keep in the source frame; hold the last good x.
- Zoom 1.0 by default; 1.1 at most for a player who is tiny in a wide shot. No punch-ins: viewers judged 1.1–1.35 "too zoomed in" — 9:16 already crops to a third of the width. Prefer the 4K angle when the same moment exists twice.
- **Motion:** vcam moves the window like a camera operator (`FOLLOW` in vcam.py): still while the subject stays inside a centre dead zone, a critically damped ease when it must follow, speed and acceleration limits, stiffening near the edge so the subject never leaves. Keys say where the subject is; they no longer drive the window directly, so dense or jittery keys don't make jittery video. Only `"move":"fast"` whips bypass it. Viewers judged the raw key-following "jumpy/choppy" (the window slid a median 12–50% of the source width per second on top of the operator's own pans; with the follow model it is ~2%).
- **Handles:** set `"handles": 0.2` on every play's shot list (not the teaser) so the framing also covers the 0.2s dissolves either side of the cut (clamped at the ends of the file).

**Per source** (`media.clips.<clip>`):
- Portrait phone clips are already 9:16. For them, vcam only zooms and pans inside the frame.
- VFR clips: fine on the ffmpeg path (vcam renders constant frame rate). On the Resolve path a VFR phone clip plays at its conformed rate; flag it if it judders.
- Very wide AI-camera sources (`camera_type` ai_panoramic) need more keys and a higher base zoom (up to 1.3). The subject is small in a panorama.

## 2. Teaser (cold open — only if `select.teaser` is set)
Write a second shot list, `<clip>_teaser.json`, with `in`/`out_t` from `select.teaser`. Keys: the player → `"move":"fast"` to the ball, then `"freeze": {"t": <freeze_t>, "dur": <freeze_dur>}` and `"whip_out": true` (the whip blur is rendered on the ffmpeg path only; in Resolve the freeze is a retime of the original and the teaser hard-cuts into the first play).

## 3. Check the framing (both paths)
`python3 $S/vcam.py <shotlist> --check` for each: renders a small preview in scratch, writes a 4 fps contact sheet to `<deliverable>/checks/<shotlist name>.jpg`, deletes the preview, and prints how many Resolve keyframes the path reduces to. Read every sheet:
- the subject (or the ball after a shot/pass/attack) is in frame at every sample;
- the outcome is held;
- scoring plays pan back to the scorer and end on the reaction.

Fix the keys and re-check if any sheet fails.

**ffmpeg path only:** then render each with `python3 $S/vcam.py <shotlist>` (≈8s per clip) → `<deliverable>/reframes/<shotlist name>_vc.mov`, ProRes 422 HQ 10-bit, Log preserved, audio kept. These are scratch intermediates for finish.py, deleted with the session. The Resolve path renders nothing.

## 4. Write results
Run `hrstate.py deliv merge direct.shots file.json` with one entry per shot list. `role` is `teaser` for the cold open, else `play`; hr-assemble (timeline_export.py) and finish.py match them by clip + aspect + role. On the ffmpeg path add each render's `"out"`:
```json
{"R7__1630_teaser_9x16": {"clip": "R7__1630", "aspect": "9:16", "role": "teaser", "shotlist": "…", "checked": true},
 "R7__1630_9x16": {"clip": "R7__1630", "aspect": "9:16", "role": "play", "shotlist": "…", "checked": true}}
```
Then `hrstate.py deliv done direct "<N shot lists>"`.

## Done when
Every play in `select` (plus the teaser) has a checked shot list for every aspect that needs one (and, on the ffmpeg path, a render).

## Known gaps
- `track.py` follows shirt colour, so in a crowd of teammates it can jump to the biggest nearby one; ball and outcome keys are still hand-read from grids. Planned: an appearance-based tracker seeded from the profile's reference crops.
