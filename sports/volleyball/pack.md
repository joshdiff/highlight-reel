# Volleyball pack

## What a highlight is
Point-winning contacts by the featured player: kills, aces, stuff blocks, plus the dig or set that made a kill possible. Each rally is a natural clip with a clear start (serve) and end (ball on the floor). A highlight should show the whole sequence that leads to the player's contact, not just the contact.

## Finding moments
- **Point won by us:** all six same-shirt players converging; a referee pointing toward the other side; a scoreboard change.
- **Rally end:** the ball hitting the floor, then players walking back to serve positions (dead time, 15–25s between rallies). In continuous recordings this rhythm makes rallies easy to segment.
- **Long rallies** (many contacts) that we win are highlights even when no single contact stands out.
- **Watch the net zone and the front-row attackers** around the third contact.

## Identification
Numbers are on the front and back. The **libero wears a different colour** from teammates: if the featured player is a libero, calibrate their shirt as its own kit (kits.libero). Hair is usually tied back, but its colour and length still help. Knee pads, shoes and sleeves are secondary cues. Players rotate every point, so court position is not an identifier.

## Scoring (events in pack.json)
- **3:** kill, ace, stuff block, long rally won, dig → kill, set → kill, back-row attack
- **2:** tip/roll score, dig, block touch
- **1:** serve receive (recruiting only), off the ball

## Reel structure
- **Social:** 5–9 rallies of 3–8s, 30–45s total. Teaser (optional — only for a standout kill; otherwise open on the best rally): best kill, frozen at the hand–ball contact. Finale: that rally in full, through the huddle.
- **Recruiting:** 3–5 min, grouped by skill, primary position skill first (hitters: attacking; setters: setting; liberos/DS: passing and defense). Then serving, blocking, and a few full rallies.
- **Scoring reel:** every point won by the player, in chronological order.

## Director rules — who the frame follows
| Moment | Subject | Framing |
|---|---|---|
| Serve (player serving) | PLAYER → BALL | on the server through the toss and contact; `"move":"fast"` to the ball crossing the net; hold where it lands on an ace |
| Approach + attack | PLAYER | follow the approach; **raise `y`** with the jump so hand, ball and net top stay in frame; at contact `"move":"fast"` to the ball → the floor where it lands; hold ~0.5s |
| — KILL | FLOOR → PLAYER | pan back to the attacker for the reaction, widen to zoom 1.0 as the team huddles; end ~1.5s into the huddle |
| Block | PLAYER + attacker at the net | centre on the net between them, y high; follow the ball down after a stuff |
| Dig | BALL → PLAYER → BALL | centre on the digger at contact, then follow the ball up to the setter and through the attack; for a digger's reel, come back to them on the point celebration |
| Set (setter reel) | PLAYER → BALL → HITTER | on the setter at the set; follow the ball to the hitter and through the attack |

The ball travels high, so vertical framing needs `y` keyframes. Use 30–40 when the ball is above the net, and 50–60 during floor play. Keep zoom at 1.0 (≤1.1) during rallies; the ball moves faster than the frame can follow at higher zoom.
(team) The frame follows the ball through the rally and settles on the player who wins the point.
