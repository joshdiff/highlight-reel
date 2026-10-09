---
name: hr-grade
description: Highlight reel deliverable stage (Resolve path) — give every clip its own correction (exposure, white balance, saturation only ever reduced) so the whole reel lands on one consistent neutral-standard look, whatever the light was; solved from Resolve's rendered frames with look.py, applied as one CDL node per clip on top of Resolve colour management.
---

# hr-grade — one consistent look, a correction per clip

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`. Uses the davinci-resolve MCP.

**Scope: deliverable.** Requires `assemble` done. Item IDs come from `hrstate.py deliv get resolve.items` (skip title/bumper items).

## The idea
Raw footage differs game to game and shot to shot (sun, cloud, late light, camera settings); the output must not. So there is no fixed grade. Resolve colour management (set in hr-project) does camera → Rec.709, and each clip gets ONE CDL node that `look.py` solves against a fixed **neutral-standard target**:
- **exposure:** the playing surface (grass/turf/hardwood — the sport pack's `surface.target_luma`) reflects about the same light in any weather, so its median luma is pinned to the target (soccer 0.36). No surface in view → frame median 0.40;
- **white balance:** near-neutral pixels (lines, white kit, overcast sky) are made grey;
- **saturation:** as recorded after the standard conversion, lowered only if >0.5% of pixels go neon. Never boosted — a videographer judged a saturation push "blown out, not natural".

The correction is in stops (scene-linear), so the ffmpeg path (hr-finish) uses the same solver and lands on the same look.

## Steps (per aspect timeline)
1. **Grade before the dissolves**, or remember that `item_index` counts transitions (clips at 0, 1, 3, 5, …). Fresh items have one node; that node carries the correction. A videographer-supplied creative grade (brand `grade.drx`) is NOT the default; if a client wants one, apply it after the look is solved and re-measure.
2. **Pass 0 — measure:** `timeline_frame capture` (quality "frame", max_width 270) two frames per clip, at ⅓ and ⅔ of each item, in clip order. Then
   `python3 $S/look.py batch <deliverable>/look.json --clips teaser,R7__1603,… --sport <sport> <frames in capture order>`
   — prints each clip's measured surface luma → target and its next correction; `look.json` keeps corrections and history.
3. **Apply:** for every clip not yet converged, `timeline_item_color` → `safe_set_cdl` on node 1 with that clip's `resolve_cdl` from look.json (Slope 1, Offset per channel, Power 1, Saturation).
4. **Repeat 2–3** (capture with the corrections on, `look.py batch` again on the same look.json) until every clip reports converged or is within ±0.015 of target — normally 2 passes; the solver uses each clip's measured response after the first step.
   - Resolve's frame renders wedge with "Error decoding full resolution media" after ~16 captures: save, load another project, load this one, set the timeline current, then capture (quality-bar Environment facts). Do this before each pass.
5. **Verify on the render** (hr-export does the final check): per play, the surface luma spread should be ≤0.03 and vivid <0.5%. Look at one frame per play: shirts their real colour, grass natural, the plays matching each other.
6. **Write results:** `hrstate.py deliv set grade '{"method": "look.py neutral standard", "look": <look.json contents>}'`, then `hrstate.py deliv done grade "<surface luma range, vivid max>"`. Add the typical correction to the camera profile notes (e.g. "C-Log3 overcast: −0.7 to −1.6 stops") — it says how that camera tends to expose, not a grade to reuse.

## Mixed cameras
Nothing special: colour management converts each clip from its own Input Color Space (hr-project step 5), and every clip is solved to the same target. HDR phone clips may hit the vivid ceiling first; the solver lowers their saturation.

## Done when
Every clip converged (or within ±0.015) and the rendered reel's per-play surface luma spread is ≤0.03 with vivid <0.5%.

## Known gaps
- Exposure is anchored on the playing surface; a reel of close-ups with almost no surface in view falls back to frame median luma, which is less stable.
- Contrast is left to Resolve's output transform; there is no per-clip contrast match yet.
- Captures are ~1.5s each in Resolve and wedge every ~16; a capture-free route (solve on the reframes with luts.py, then translate) would be faster but the two transforms differ, so it isn't used.
- Measured on one overcast game (FSA): surface luma per play went from a 0.155 spread (one fixed grade) to 0.016.
