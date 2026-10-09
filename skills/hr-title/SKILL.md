---
name: hr-title
description: Highlight reel deliverable stage (Resolve path) — add the name lower third (from the player profile and the client brand) over the teaser via a nested Text+ title timeline, the only route that works through the Resolve MCP, and verify it on a captured frame.
---

# hr-title — lower third (Resolve)

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`. Uses the davinci-resolve MCP.

**Scope: deliverable.** Requires `assemble` done (grade may come before or after).

**Text:**
- player target: the profile's `lower_third` (`hrprofile.py show player <id>`); default line 1 = name, line 2 = "<team> - c/o <grad year>", fallback "#<number> | <team>";
- team target: line 1 = team name, line 2 = "vs <opponent>" (plus the score if the found scoring plays make it certain, e.g. "vs Rovers · 2–1 W"; omit if unsure).

**Style:** the deliverable's brand (`brand.json → lower_third`: font, colours, position) if set, else the defaults below.

`insert_title` fails, and `insert_fusion_title` lands at the unsettable playhead and can't be moved. So use a NESTED TITLE TIMELINE, once per aspect:
1. In `GRAPHICS`, create `TITLE_<deliv id>_<aspect>` at that aspect's resolution; `insert_fusion_title` "Text+".
2. `timeline` → `set_title_text` (pass `timeline_item_id`) with the two lines.
3. `fusion_comp` → `set_input` on `Template`: Center [0.5, 0.25], Size ~0.07 (or the brand's values). This gives a compact bar in the lower third, clear of the action.
4. `timeline` → `get_media_pool_item`. Back on the delivery timeline, `add_track` video, then `append_to_timeline` that item on the new track, record_frame 0, spanning the teaser (end frame exclusive) — or, with no teaser, the first ~2.3s (70 frames) of the opening play.
5. Verify with `timeline_frame capture` mid-title; readback alone is not proof. The bar must be readable and must not cover the player.
6. `hrstate.py deliv set title '{"text": ["...", "..."], "items": {"9:16": "..."}}'`; `hrstate.py deliv done title`.

## Known gaps
- Static style; no animated in/out. The watermark goes on as a separate track (brand `watermark`), not yet automated here.
