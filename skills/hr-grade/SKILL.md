---
name: hr-grade
description: Highlight reel stage 8 — apply the power-grade DRX to every clip on the delivery timeline, disable the DRX's own colour-space-transform nodes, set the SPARE-node CDL, and measure luma/saturation/clipping on rendered frames.
---

# hr-grade — colour grade

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (the scripts folder, wherever the skill is installed). Shared rules: `$S/../reference/quality-bar.md`. Uses the davinci-resolve MCP.

**Workspace:** if `$ARGUMENTS` names a game, `hrstate.py use "<game>"`; then `hrstate.py status`. Requires `assemble` done. Item IDs: `resolve.items` (skip any title item).

## Why the DRX needs surgery
The DarrenMostyn .drx is a SELF-CONTAINED pipeline: node 1 "CAM>DWG" and node 17 "DWG>709" are its own Color Space Transforms, and its CAM>DWG is NOT set for Canon Log 3 — on Canon footage it clips ~25% of the frame with or without colour management (measured). So disable those and let Resolve colour management do Log→DWG→709 once.

## Mixed cameras
Group the delivery items by source encoding (`media.clips.<clip>.encoding`; reframes use their source clip's). Colour management normalises every encoding into DaVinci WG, so one creative grade can serve all — but each group is measured, and gets its own SPARE CDL if its stats differ. HDR (HLG/PQ phone) clips usually need lower saturation; Rec.709 clips need less contrast than Log. Record CDL per group.

## Steps
1. Copy `settings.power_grade_drx` to the workspace; `timeline_item_color` → `safe_apply_drx` on item 0 (confirm_token); `safe_copy_grade` to every other video item (confirm_token).
2. `grade_evidence_base` on item 0 → list nodes whose tools include "OFX: Color Space Transform".
3. `graph` → `set_node_enabled` false on those nodes for EVERY item (`source:"item"`).
4. `safe_set_cdl` (dry-run first) on the node labelled "SPARE" (node 16 in the DarrenMostyn DRX — find it by label from step 2; for another DRX use its last empty node before the output CST) of every item: Slope 0.92, Power 1.05, Saturation 2.4.
5. Measure on rendered frames (`timeline_frame capture`, quality "frame", one per item, mid-clip): mean luma 0.36–0.45, mean HSV saturation ≥0.35, clipped (max channel >0.98) <1%. Adjust the SPARE CDL if out of range, re-measure.
6. If the reframes look flat/grey while an original at the same moment doesn't, their Input Color Space isn't the camera Log — fix per hr-project step 6.
7. Write results: `hrstate.py set grade '{"drx": "...", "cst_nodes_disabled": [1,17], "spare_node": 16, "cdl": {"<encoding>": {...}}, "stats": {"<item_id>": {"encoding": .., "luma": .., "sat": .., "clip_pct": ..}}}'`. A CDL that works for a camera is worth keeping: add it to that camera profile's notes (`cameras.py` profile JSON, `notes`). Then `hrstate.py done grade "<stats range>"`.

## Done when
Every item's stats are in range.

## Known gaps (next optimizations)
- The luma/sat/clip measurement is manual — make a script that takes the captured frames and prints the table.
- A game-specific .drx the user graded themselves would beat the generic one — if they supply one, use it and still do step 2.
- Per-shot balancing (clouds vs. sun between clips) isn't done; one CDL fits all.
