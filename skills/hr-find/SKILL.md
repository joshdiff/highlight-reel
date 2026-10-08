---
name: hr-find
description: Highlight reel target stage — find a player (number + learned look, rejecting decoys) or a team's moments in a surveyed game, score every play by the sport pack, and record sightings so the player profile learns. Writes the target's find.json.
---

# hr-find — who, where, and how good

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`.

**Scope: target.** `python3 $S/hrstate.py status`. If `$ARGUMENTS` names a game/target: `hrstate.py use game "<game>"` then `use target <id>`. Requires game stage `survey` done. `hrstate.py target get` shows the target (kind, player_id, team side).

**Sport rules:** read `$S/../../../sports/<sport>/pack.md` (`hrstate.py get sport`). Its events, scoring and identification sections override anything generic here.

"They" below = the featured player (player target) or the target team's player on the ball (team target).

## 0. Load what we already know
- `python3 $S/hrprofile.py brief <player_id> <team_id>`: number on THIS team, kits, look, **best cues ranked by past reliability**, what misled us before, decoys, client feedback, flags.
- `python3 $S/hrprofile.py refsheet <player_id> --kit <kit>`: Read the image. These are confirmed past sightings; compare every candidate against them.
- A player with no refs and an empty look is normal for a first game: identify by number alone, and record what you see.
- If the brief has a flag (e.g. a possible haircut), treat that cue as unreliable until confirmed.

## 1. (player) Identify — crop sheets, then confirm densely
1. `python3 $S/crops.py --team <side>` → `sheets/<side>/crops_NN.jpg` + `crops_meta.json`. Read every sheet next to the refsheet.
   Then `python3 $S/subject.py --team <side>` (~1 min per 100 clips; 4 parallel jobs) → `sheets/subject/subj_NN.jpg` + `subj_meta.json`: the player the camera operator is following, once per second, for every clip. Read all of them too. They show a whole possession, so on-ball moments, look cues and the back number turn up where the 5 crop samples caught nothing (in testing they surfaced 3 of a reel's 7 plays that the crop sheets missed). Their `subj_meta.json` boxes work as `ref` boxes.
2. Check cues in the order the brief ranks them (e.g. "hair 90%, number 40%" means look at hair first). Mark each clip:
   - **CONFIRMED:** the number legible on the right shirt, OR two independent strong cues that match the refs.
   - **CANDIDATE:** one cue matches.
   - **NO.**
3. **Decoys:** everything in the profile's decoys, plus always the same number on the other team and similar numbers (#17/#7, #3/#23/#33). Reject them, and record any NEW decoy in the target's `decoys_met`.
4. The 5-sample pass misses clips. For every CANDIDATE, every clip where the subject strips show them on the ball, and every clip where a target-team player is close to camera with the ball, run `python3 $S/vgrid.py <clip> <in> <out> <clip>_2fps.jpg 2` over the segment and look for the number. Promote to CONFIRMED only when it's seen in the same continuous action.

## 1-team. (team) Find the moments instead of a player
Skip number ID. From the overview sheets (`python3 $S/sheets.py`) and the `src2fps/` thumbnails, flag the pack's events using its "signals" list. Confirm it's the TARGET team's moment by shirt colour. Never include points or goals conceded, unless the target's save/block/dig is the highlight.

## 2. Score from the 5 fps grid (not from samples)
For each CONFIRMED clip (team: each flagged clip): `python3 $S/vgrid.py <clip> <a> <b> <clip>.jpg` over the action. Classify with the pack's `events` (each carries its score: 3 = highlight, 2 = solid, 1 = drop). Record the whole move: action_start → action_end, first touch → outcome.

## 3. Write results — every examined clip, so learning is complete
Write a JSON file and run `hrstate.py target merge clips file.json`:
```json
{"R7__1630": {"status": "CONFIRMED", "score": 3, "event": "goal", "scoring": true,
              "action_start": 2.6, "action_end": 10.8, "key_t": 4.2,
              "beat": "dribble past #4, left-foot finish far post",
              "cues": ["number", "hair"],
              "ref": {"t": 1.625, "box": [1482, 792, 1620, 1023]},
              "observed": {"footwear": "white boots"},
              "foot": "left", "area": "left half-space"},
 "R7__1549": {"status": "NO", "misled_by": ["#17 teammate"]}}
```
Field notes:
- `key_t` is the decisive contact: kick, shot release, attack contact.
- `cues` lists ONLY the cues that actually confirmed this sighting. `misled_by` is set when a clip looked like them but wasn't.
- `ref` is one clear sighting per confirmed clip: the `t` and `box_src` of their tile in `crops_meta.json` (key `"<clip>:<n>"`), or a box you measured on a 4K frame. Choose views that show the cues well.
- `observed` holds look details worth remembering (fields like hair, footwear, accessories). Use `foot`/`hand`, `position` and `area` when visible.

Then `hrstate.py target set decoys_met '[…]'` if any, then:
```
python3 $S/hrprofile.py learn <player_id> --game "<game id>" --target <target id>
python3 $S/hrstate.py target done find "<N confirmed, M candidates, K scoring plays>"
```
`learn` saves the references, updates cue reliability, the dated look, play style and game history. It's safe to re-run.

## Done when
Every clip has a status. Every kept clip (score ≥2) has action_start/end, event, beat and key_t. Every CONFIRMED clip has cues, and most have a ref. `learn` ran for player targets.

## Known gaps (next optimizations)
- No automatic re-ID yet. Planned: `reid.py` ranks crop tiles by similarity to the reference gallery, so the dense check starts with the likeliest clips.
- Sponsor boards and banners in a shirt-like colour get detected as players. Needs a shape/texture filter in detect.py.
