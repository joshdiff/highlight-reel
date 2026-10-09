---
name: hr-select
description: Highlight reel deliverable stage — choose and order the plays for one deliverable (teaser, sequences, finale) from its target's scored clips, using the sport pack's reel structure, the player's style and the client's past feedback; set source windows to hit the target length.
---

# hr-select — the running order

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`.

**Scope: deliverable.** `python3 $S/hrstate.py status`; `hrstate.py use deliv <id>` if `$ARGUMENTS` names one. Requires the deliverable's target to have `find` done. Read:
- `hrstate.py deliv get`: type, aspects, target, brand;
- `hrstate.py target get clips`: scored plays;
- `hrstate.py get sport`, then the pack's `deliverables.<type>` (`python3 $S/sports.py deliverable <sport> <type>`): target length, sequence lengths, teaser/finale rules, ordering;
- player targets: `hrprofile.py brief <player_id>`. Apply its client feedback (keep/drop verdicts are rules, e.g. "no defensive clips"), and use its style to favour the player's strengths in recruiting tapes.

## Rules
- **Pool:** clips with score ≥2 (≥3 preferred). Never a clip the client dropped before (feedback with a matching clip or kind).
- **social_reel:**
  - **Teaser (optional):** only when the pool has a goal/scoring play worth holding back — then the best one, and **finale:** that play in full. Otherwise set `"teaser": null`, open on the strongest play (the lower third goes over its first ~2s) and end on a strong play, without repeating one. A videographer said the freeze open shouldn't be on every reel.
  - **Middle:** the pack's `n_seq` sequences of `seq_s` length, strongest first, varied lengths, no two near-identical beats back to back.
  - **(team):** every scoring play is in (the best one as teaser + finale).
  - **Length:** `target_s` including the teaser if there is one (~2–2.5s).
- **recruiting_tape:** the pack's `order` groups; whole possessions/rallies; `target_s`.
- **scoring_reel:** every play whose event is in the pack's `events` list for it, chronological.
- **season_reel:** pool = `games[].best_clips` from the player profile for the season. Each entry has `game_dir`; read that game's `targets/*/find.json` for windows. Pick the best across games, balance across games, and sequence by quality. Games whose media is offline (drive unmounted) are skipped and noted.

## Windows (source-file seconds)
Window = `action_start − 0.5` → `action_end`, plus:
- scoring plays: the reaction/celebration, +3–5s after the score;
- passes: through the reception, +0.5s.

Clamp to the clip's segment (`media.clips.<clip>.in/out`). Teaser window: ~0.6s before `key_t` → ~0.25s after (outcome not shown).

## Write results
```json
{"total_s": 46.2,
 "teaser": {"clip": "R7__1630", "in": 3.6, "out": 4.45, "key_t": 4.2, "freeze_t": 4.45, "freeze_dur": 1.5},
 "sequence": [{"clip": "R7__1587", "in": 1.1, "out": 8.0, "role": "middle", "beat": "take-on past #4"},
              {"clip": "R7__1630", "in": 2.1, "out": 14.9, "role": "finale", "beat": "goal + celebration"}]}
```
For a season reel, add `"game": "<game id>"` to each item. Run `hrstate.py deliv set select "$(cat select.json)"`, then `hrstate.py deliv done select "<N plays, total s>"`.

## Done when
`total_s` is within the pack's target; with a teaser, the finale is its play in full (social); no two adjacent sequences share the same beat; every window is inside its segment; no client-dropped clip is included.

## Known gaps
- Ordering is judgement-only. Music-beat alignment of cuts is not implemented.
