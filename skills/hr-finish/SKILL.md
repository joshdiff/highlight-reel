---
name: hr-finish
description: Highlight reel deliverable stage (ffmpeg path, no NLE needed) — colour each play per camera encoding (official or built-in LUT + CDL), add the client brand (lower third, watermark, intro/outro), music ducked under game sound, loudness, and render every aspect to H.264; checks the grade; can also write an FCPXML handoff for another editor.
---

# hr-finish — finished files without an NLE

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`.

**Scope: deliverable** (`finish_path` = ffmpeg). Requires `direct` done. Brand: `python3 $S/library.py show brand <deliv brand_id>`; without a brand, the neutral default look is used.

## Steps
1. `python3 $S/finish.py` (all aspects; `--aspect 9:16` for one; `--music none|auto|FILE`; `--keep` keeps the intermediates). It does, per aspect:
   - **Plays:** each play's render for that aspect. 16:9 deliverables from 16:9 footage use the originals trimmed to the select windows.
   - **Colour per source encoding:**
     1. the camera profile's official `lut`, else the built-in transform (`luts.py`: Canon Log 3, S-Log3, V-Log, Apple Log, HLG, PQ; Rec.709 untouched);
     2. then the CDL: `deliv grade.cdl.<encoding>`, else the brand's, else slope 1.0 / power 1.02 / saturation 1.3;
     3. then the brand's creative LUT.
   - **Brand:** intro/outro bumpers, a lower third over the teaser (text from the player profile, style from the brand), and a watermark.
   - **Audio:**
     - music from the brand's folder, chosen per deliverable. It's on for social reels and off for recruiting/scoring reels unless set (`hrstate.py deliv set music <file|none>`);
     - ducked under the game audio;
     - loudness to the brand target (−14 LUFS social, −16 LUFS landscape).
   - **Encode:** H.264 high, CRF 18 capped at 14/20/25 Mb/s, 29.97 CFR, Rec.709 tags, faststart → `<deliverable>/finished/<aspect>.mp4`.
1b. **Consistent look:** each play's correction (exposure, white balance; saturation only lowered) is solved against the sport pack's neutral-standard target by `look.py` inside finish.py — frames rendered through the colour chain, measured, re-solved until converged — and cached in `deliv.grade.look`. The same target as the Resolve path, so both finishes match.
2. **Grade check** (printed per aspect: 8 sampled frames vs the bar: luma 0.36–0.45, vivid (extreme-saturation pixels) <0.5%, clipping <1%). Look at a contact sheet of the file too. Grass-heavy or overcast frames can sit just under the luma bar and still look right; trust the picture, but fix a whole reel that's dark, flat or clipped:
   ```
   hrstate.py deliv set grade.cdl.<encoding> '{"slope": 1.05, "offset": 0, "power": 1.0, "sat": 1.35}'
   python3 $S/finish.py --aspect <aspect>
   ```
   Brighten with slope >1 or power <1; add saturation up to ~1.5. If a camera consistently needs the same CDL, save it on the brand (`library.py set brand <id> grade.cdl '{…}'`) or note it on the camera profile.
3. **Optional handoff** for an editor who finishes in Final Cut / Premiere / Resolve: `python3 $S/timeline_export.py` → `<deliverable>/handoff/<id>.fcpxml`. It holds the clips in order, with a marker per play; colour stays camera-native.
4. `hrstate.py deliv done finish "<aspects, durations, grade ok/flags>"`; then /hr-export delivers the files.

## Done when
Every aspect has a finished file. The grade check passes, or its misses are judged fine by eye and noted. The lower third is visible on the teaser and the audio is audible and not clipped.

## Known gaps
- The built-in LUTs are neutral technical transforms. An official manufacturer LUT, or the videographer's own creative LUT, gives the house look.
- One CDL per encoding per reel; no shot-to-shot balancing.
- The FCPXML handoff is well-formed XML but hasn't been test-imported into Final Cut or Premiere yet.
- Plays are still joined with hard cuts here; the Resolve path blends them with 0.2s dissolves. Planned: ffmpeg `xfade` using the reframes' handles (vcam `"handles"`), trimming them like hr-assemble does.
