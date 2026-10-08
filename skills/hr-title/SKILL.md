---
name: hr-title
description: Highlight reel stage 9 — add the name lower third over the teaser via a nested Text+ title timeline (the only route that works through the Resolve MCP), and verify it on a captured frame.
---

# hr-title — lower third

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (the scripts folder, wherever the skill is installed). Shared rules: `$S/../reference/quality-bar.md`. Uses the davinci-resolve MCP.

**Workspace:** if `$ARGUMENTS` names a game, `hrstate.py use "<game>"`; then `hrstate.py status`. Requires `assemble` done (grade may come before or after).

`insert_title` fails and `insert_fusion_title` lands at the unsettable playhead and can't be moved — so use a NESTED TITLE TIMELINE:
1. In `GRAPHICS` create `TITLE_[player_number|Team]_[event_name]` at the delivery resolution; `insert_fusion_title` "Text+".
2. `timeline` → `set_title_text` (pass `timeline_item_id`):
   - player mode: line 1 `[player_name]`, line 2 `[team_name] - c/o [grad_year]` (fallback `#[player_number] | [team_name]`).
   - team mode: line 1 `[team_name]`, line 2 `vs [event_name]` (plus the score if the goals found make it clear, e.g. "vs Rovers · 2–1 W" — omit if unsure).
3. `fusion_comp` → `set_input` on `Template`: Center [0.5, 0.25], Size ~0.07 — a compact name bar in the lower third, clear of the action.
4. `timeline` → `get_media_pool_item`; back on the delivery timeline `add_track` video, then `append_to_timeline` that item on track 2, record_frame 0, spanning the teaser (end frame exclusive).
5. Verify with `timeline_frame capture` mid-teaser — readback alone is not proof. The bar must be readable and not cover her.
6. `hrstate.py set title '{"timeline": "...", "item_id": "...", "text": ["...", "..."], "frames": [0, N]}'`; `hrstate.py done title`.

## Known gaps
- Single static style; no animated in/out or team-colour accent.
