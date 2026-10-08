---
name: hr-direct
description: Highlight reel stage 5 — direct each selected clip (who the frame follows, shot by shot) as a shot list and render the 9:16 virtual camera with vcam.py, then check the subject stays in frame. No Resolve needed.
---

# hr-direct — shot lists and the virtual camera

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (the scripts folder, wherever the skill is installed). Shared rules: `$S/../reference/quality-bar.md`.

**Workspace:** if `$ARGUMENTS` names a game (or a single clip to redo), `hrstate.py use "<game>"`; then `hrstate.py status`. Requires `select` done. Read `get select` and `get find.clips`.

**social_reel only renders.** For recruiting_tape / goals_reel (16:9) don't render: re-check each window in `select.sequence` against the director rules below (a goal clip runs through the celebration, a pass clip through the reception), fix windows in `select` if needed, and mark done.

## 1. Write the shot list per clip
`<workspace>/shotlists/<clip>.json` (schema in the `vcam.py` docstring; `src` may be the clip name). `in`/`out_t` = the clip's window from `select`. Make a 5 fps grid over the window — `python3 $S/vgrid.py <clip> <in> <out> <clip>.jpg` — and read positions off its 0–100 ruler. Add a key at every change of subject or direction, and every ~0.4–0.8s while the subject moves; more keys during fast motion. Set `y` to her vertical position (usually 45–55).

### Director rules — who the frame follows
| Moment | Subject | Framing |
|---|---|---|
| She has the ball (possession / dribble) | HER | centre on her, ~8% lead room toward where she's running; zoom 1.3–1.4 when she's small in the source, 1.0–1.15 when close |
| 1v1 take-on | HER + defender | centre between them, punch in +0.15 zoom for the beat, ease back out after she's past |
| She SHOOTS | BALL | at the kick frame add a key with `"move":"fast"` on the ball (window reaches it ≤0.25s), lead toward the goal, follow the ball until the outcome |
| — outcome GOAL | BALL → NET → HER | hold on the ball in the net 0.4–0.6s; smooth pan back to her over ~0.8–1.2s; stay on her as she reacts/runs; when ≥2 teammates arrive widen to zoom 1.0 on the group; end 1–2s into the hug (≈3–5s after the goal) |
| — outcome SAVE / MISS | BALL → keeper/goal | hold the save or the ball going wide ~0.5s, then end (don't pan back) |
| She PASSES | BALL → RECEIVER | `"move":"fast"` to the ball, follow to the receiver, stay ~0.5–1s. If the receiver shoots/scores within ~3s (ASSIST), keep following the ball through the finish, then pan back to HER for the celebration if she joins it. Simple pass: end 0.5s after reception, unless she keeps running for a return ball (give-and-go) — then return to her when she receives |
| She RECEIVES | BALL → HER | start on the ball in flight (≤0.5s), lock onto her at first touch |
| She WINS the ball (tackle/interception) | HER + carrier → HER | centre on the duel, then follow her once she has it |

(team) On a PASS the receiver becomes the new subject — keep following the play, never return to the passer; on a GOAL pan back to whoever SCORED; the assist "return to her" rule is player-mode only; on a keeper SAVE the keeper is the subject from the shot onward.

**Constraints:** subject inside the middle 60% of the window except during a ≤0.25s whip; never chase a subject the camera operator didn't keep in the source frame — hold the last good x.

**Per source (check `media.clips.<clip>`):** zoom 1.0–1.5 on ≥4K sources; ≤1080p sources are capped at 1.15 by vcam (already upscaled ~1.8×) — prefer 4K angles when the same moment exists twice. Portrait sources (`orientation: portrait`, phones held upright) are already 9:16: vcam only zooms/pans inside them, so keep zoom ≤1.15 and x near 50 unless the player is at an edge. VFR clips are fine — vcam renders constant frame rate.

### Teaser (cold open)
Second shot list `shotlists/<clip>_teaser.json` with `"out": "<workspace>/reframed/<clip>_teaser_vc.mov"`: `in`/`out_t` from `select.teaser`; keys: her → `"move":"fast"` to the ball; `"freeze": {"t": <freeze_t>, "dur": <freeze_dur>}`, `"whip_out": true`.

## 2. Render and check
`python3 $S/vcam.py <shotlist>` for each (≈8s per clip). Output ProRes 422 HQ 10-bit, camera Log preserved, audio kept → `reframed/<clip>_vc.mov`.

Check every output with a 4 fps contact sheet into `checks/`:
`ffmpeg -i <out> -vf "fps=4,scale=270:480,tile=8x4" -frames:v 1 checks/<clip>_vc.jpg` (raise the tile rows for long clips). She (or the ball after a shot/pass) must be in frame at every sample; shots follow the ball; goals pan back to her and end on the celebration. Fix the keys and re-render if not.

## 3. Write results
`hrstate.py merge direct.renders file.json` with one entry per render: `{"R7__1630": {"shotlist": "...", "out": "...", "frames": 488, "fps": 59.94, "checked": true}, "R7__1630_teaser": {...}}`. Then `hrstate.py done direct "<N renders>"`.

## Done when
Every clip in `select` (plus the teaser) has a checked render whose contact sheet passes.

## Known gaps (next optimizations)
- Keys are hand-read from grids. Plan: seed a box on her and let an OpenCV tracker propose the x path; apply director rules on top.
- `vcam.py`: the 0.2s smoothing also softens "fast" whips (comment says it shouldn't); zoom isn't smoothed; y is fixed per clip.
- No `vcheck.py` — the contact-sheet check is a manual ffmpeg call.
