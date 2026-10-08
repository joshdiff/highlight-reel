---
name: hr-find
description: Highlight reel stage 3 — identify the featured player (number + identifiers, reject decoys) or the team's moments, then score each clip's action from a 5 fps grid. Writes find.clips to reel.json. No Resolve needed.
---

# hr-find — who, where, and how good

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (the scripts folder, wherever the skill is installed). Shared rules: `$S/../reference/quality-bar.md`. Start from the profiles: `python3 $S/hrprofile.py brief <settings.player_id> <settings.team_id>` (number on THIS team, kit, look, decoys, recent lessons) and `hrprofile.py show team <team_id>` (roster, opponent colours). A player with an empty look is normal: identify by number alone, and note what you see for hr-export to save.

**Workspace:** if `$ARGUMENTS` names a game, `hrstate.py use "<game>"`; then `hrstate.py status`. Requires `survey` done.

"She" below = the featured player (player mode) or the team_jersey_color player on the ball (team mode).

## A. (player) Identify the player — torso crops, then confirm densely
1. Read every `sheets/crops_NN.jpg`.
2. Mark each clip: **CONFIRMED** (number legible on a team_jersey_color shirt), **CANDIDATE** (her `appearance` identifiers from the profile — hair, boots, sleeves, accessories — but number not seen), or **NO**.
3. **Decoys:** everything in the profile's `decoys`, plus always: the same number on the opponent's shirt, teen numbers (#17 for #7). Reject them. Record any NEW decoy you meet in the clip notes so hr-export can add it to the profile.
4. The 5-sample pass MISSES clips (on the first real run: a goal and two long dribbles). For every CANDIDATE and every clip whose overview frames show a team_jersey_color player close to camera with the ball, run `python3 $S/vgrid.py <clip> 0 <duration> <clip>_2fps.jpg 2` and look for the number. Promote to CONFIRMED only when the number is seen in some frame of the same continuous action.

## A-team. (team) Find the moments instead of a player
Skip number ID. From the overview sheets and `src2fps/` thumbnails flag: goals (ball in net, several team_jersey_color players converging/hugging, a centre-circle restart in the next clip), shots and keeper saves, take-ons, multi-pass moves into the box, big tackles/blocks. Confirm it's OUR team's moment by shirt colour — never include goals conceded (an opponent's shot appears only if our keeper's save is the highlight).

## B. Score from the 5 fps grid (not from samples)
For each CONFIRMED clip (team: each flagged clip): `python3 $S/vgrid.py <clip> <a> <b> <clip>.jpg` over the action and classify:
- **3** = GOAL, SHOT, or TAKE-ON (beats a defender with the ball), she is the ball carrier
- **2** = clear on-ball run / receive-and-dribble / tackle won and carried
- **1** = off-ball, scramble she isn't driving, or too far to read → drop

## C. Write results
One entry per clip examined (including NO/1, so a re-run doesn't redo them), via a JSON file + `hrstate.py merge find.clips file.json`:
```json
{"R7__1630": {"status": "CONFIRMED", "score": 3, "event": "goal", "goal": true,
              "action_start": 2.6, "action_end": 10.8, "kick_t": 4.2, "scorer": "#7",
              "beat": "dribble past #4, left-foot finish far post", "notes": "number seen 3.0–3.6s"}}
```
Times are source seconds. `action_start`/`action_end` = whole move, first touch → outcome. Then `hrstate.py done find "<N confirmed, M candidates, K goals>"`.

## Done when
Every clip has a status; every kept clip (score ≥2) has action_start/end, event, beat; every goal has kick_t.

## Known gaps (next optimizations)
- Number reading is visual-only from sheets; no OCR or re-ID tracking across frames.
- The dense check depends on judgement of "close to camera with the ball" — should be driven by a ranked list from hr-survey.
