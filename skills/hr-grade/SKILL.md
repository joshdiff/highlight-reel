---
name: hr-grade
description: Highlight reel deliverable stage (Resolve path) — apply the power-grade DRX to every item of the deliverable's timelines, disable the DRX's own colour-space-transform nodes, set SPARE-node CDLs per footage encoding, and measure luma/saturation/clipping on rendered frames.
---

# hr-grade — colour grade

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`. Uses the davinci-resolve MCP.

**Scope: deliverable.** Requires `assemble` done. Item IDs come from `hrstate.py deliv get resolve.items` (skip title/bumper items). With dissolves on the track, `item_index` counts the transitions too: clips sit at 0, 1, 3, 5, … — use `safe_copy_grade` by item id, and index-based calls only on the clip indexes. Copying the grade carries the disabled CST nodes and the CDL with it (measured). Grade file: the deliverable's brand grade if set, else `hrstate.py config power_grade_drx`.

## Why a fixed-node-tree DRX needs surgery
A power grade like the DarrenMostyn fixed node tree is a SELF-CONTAINED pipeline: node 1 "CAM>DWG" and node 17 "DWG>709" are its own Color Space Transforms. Its CAM>DWG is NOT set for every camera; on Canon Log 3 it clips ~25% of the frame, with or without colour management (measured). So disable those nodes and let Resolve colour management do camera→DWG→709 once.

## Mixed cameras
Group the items by source encoding (`media.clips.<clip>.encoding`; reframes use their source clip's). Colour management normalises every encoding into DaVinci WG, so one creative grade can serve all of them. Each group is still measured separately and gets its own SPARE CDL if its stats differ. HDR (HLG/PQ phone) clips usually need lower saturation; Rec.709 clips need less contrast than Log.

## Steps
1. Copy the .drx into the deliverable folder. `timeline_item_color` → `safe_apply_drx` on item 0 (confirm_token), then `safe_copy_grade` to every other video item (confirm_token). Do this for each aspect's timeline.
2. `grade_evidence_base` on item 0 → list the nodes whose tools include "OFX: Color Space Transform".
3. `graph` → `set_node_enabled` false on those nodes for EVERY item (`source:"item"`).
4. `safe_set_cdl` (dry-run first) on the node labelled "SPARE" of every item. Find it by label from step 2: node 16 in the DarrenMostyn DRX; for another DRX, its last empty node before the output CST. Start from the camera profile's note if a CDL worked before, else Slope 0.92, Power 1.05, Saturation 1.0 (the DRX and colour management already bring colour back; the SPARE CDL is for exposure, not for adding saturation).
5. Measure on rendered frames (`timeline_frame capture`, quality "frame", one mid-item per clip) with `python3 $S/gradecheck.py <frames…>`: mean luma 0.36–0.45, vivid <0.5%, clipped <1%. Adjust the group's SPARE CDL if out of range (slope for exposure; lower saturation if vivid is high, never raise it to fill a number), then re-measure. Look at the frames too: shirts their real colour, grass natural.
6. If reframes look flat/grey while an original at the same moment doesn't, their Input Color Space isn't the camera's; fix it per hr-project step 5.
7. **Write results:** `hrstate.py deliv set grade '{"drx": "...", "cst_nodes_disabled": [1,17], "spare_node": 16, "cdl": {"<encoding>": {...}}, "stats": {"<item_id>": {...}}}'`. Add a CDL that worked to the camera profile's notes so the next game starts from it. Then `hrstate.py deliv done grade "<stats range>"`.

## Done when
Every item's stats are in range.

## Known gaps
- A game-specific .drx graded by the videographer beats the generic one. If they supply one, use it and still do step 2.
- One CDL per encoding group; shot-to-shot balancing (sun vs. cloud) isn't done.
- A videographer judged a reel graded at SPARE saturation 2.7 "blown out, not natural" (pale-blue shirts at S 0.62, up to 10.7% vivid pixels), though it met the old mean-saturation floor. That floor is gone; the vivid ceiling replaces it.
- The best grade is the videographer's own: a still or .drx of a game they graded (Color page → Gallery → right-click a still → Export, or right-click the node graph → Export as .drx) replaces the generic DRX.
