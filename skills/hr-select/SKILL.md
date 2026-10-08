---
name: hr-select
description: Highlight reel stage 4 — choose the reel from the scored clips (teaser, ordered middle sequences, full-goal finale) and set each clip's source window to hit the target length. No Resolve needed.
---

# hr-select — build the running order

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (the scripts folder, wherever the skill is installed). Shared rules: `$S/../reference/quality-bar.md`.

**Workspace:** if `$ARGUMENTS` names a game, `hrstate.py use "<game>"`; then `hrstate.py status`. Requires `find` done. Read `hrstate.py get find.clips` and `get settings`.

## social_reel
- **Teaser:** the best GOAL (else best shot). **Finale:** the same goal in full.
- **Middle:** 5–8 score-3/2 sequences, strongest take-ons and shots first after the teaser, varied lengths (3–9s), no two near-identical beats back to back.
- (team) Include EVERY goal (best one as teaser + finale, others in the middle with build-up and celebration), then saves / shots / combination play; spread screen time across players; 50–60s is fine with several goals.
- Target 40–50s total including the teaser (~2–2.5s).

## recruiting_tape
Goals (build-up + finish) → take-ons/skills → passing/defending, 2–3 min.

## goals_reel
Every goal, chronological, build-up → finish → celebration.

## Windows (source seconds)
Window = `action_start − 0.5` → `action_end`, plus for goals the celebration (+3–5s after the ball crosses the line); for a pass, through the reception (+0.5s). Clamp to the clip's duration. Teaser window: ~0.6s before `kick_t` → ~0.25s after (ball in flight, outcome not shown).

## Write results
```json
{"deliverable": "social_reel", "total_s": 46.2,
 "teaser": {"clip": "R7__1630", "in": 3.6, "out": 4.45, "kick_t": 4.2, "freeze_t": 4.45, "freeze_dur": 1.5},
 "sequence": [{"clip": "R7__1587", "in": 1.1, "out": 8.0, "role": "middle", "beat": "take-on past #4"},
              {"clip": "R7__1630", "in": 2.1, "out": 14.9, "role": "finale", "beat": "goal + celebration"}]}
```
`hrstate.py set select "$(cat select.json)"` (or `merge select select.json`). `total_s` = teaser (in→freeze + freeze_dur) + sum of windows. Then `hrstate.py done select "<N clips, total s>"`.

## Done when
`total_s` within the deliverable's target; finale is the full goal (social); no two adjacent sequences with the same beat type; every window inside its clip.

## Known gaps
- Ordering is judgement-only; could score "variety" and pacing explicitly.
- Music-beat alignment of cuts not implemented.
