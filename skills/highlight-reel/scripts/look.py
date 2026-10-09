"""Consistent output look: one target, a correction solved per clip.

Raw footage differs game to game (sun, cloud, late light, a different camera setting); the output should
not. Each clip gets its own correction — exposure and white balance in stops, plus saturation that is only
ever reduced — solved so its rendered frames hit the same NEUTRAL STANDARD target:

- exposure: the playing surface (sport pack `surface`: grass/turf, hardwood) reflects about the same amount
  of light in any weather, so its median Rec.709 luma is pinned to the pack's `target_luma`. Without a
  measurable surface (sky/close-ups, or a pack with no ground hue) the frame's median luma is used instead;
- white balance: near-neutral pixels off the surface (lines, white kit, overcast sky, concrete) are made grey;
- saturation: what the camera recorded after the standard conversion (1.0), lowered only if more than
  0.5% of pixels go neon (gradecheck "vivid"). Never boosted.

Corrections are scene-linear stops, so the same numbers drive both finishing paths:
- Resolve (colour-managed, DaVinci Intermediate timeline space): a CDL offset of 0.0733 × stops per
  channel on one node — an offset in DaVinci Intermediate is an exposure shift (`resolve_cdl`);
- ffmpeg: exposure and per-channel gains inside luts.py's scene-linear stage (`lut_args`).

The display tone curve's slope depends on brightness, so the first step assumes plain gamma 2.4 and every
later step uses the clip's measured response (secant on log luma vs stops, from `history`): measure →
solve → apply, passing each result's `point` back in `history`, until `converged` (usually 2–3 passes).

Usage: look.py measure [--sport S] IMG...
       look.py solve [--sport S] [--current '{"stops":0,"r":0,"b":0,"sat":1}'] IMG...   (frames of ONE clip)
       look.py batch STATE.json --clips A,B,C [--per 2] [--sport S] IMG...
           Resolve loop: IMG are frames captured from the timeline, `per` per clip in --clips order, each
           rendered with that clip's current correction in STATE (created if missing). Updates STATE
           {clip: {correction, history, converged, resolve_cdl}} and prints each clip's next correction;
           set every unconverged clip's `resolve_cdl`, capture again, repeat."""
import json, math, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DI_STOP = 0.07329248            # DaVinci Intermediate code values per stop
VIVID_MAX = 0.005
FRAME_LUMA = 0.40               # fallback target: median luma of the whole frame
SURFACE_DEFAULT = {'ground_hue': None, 'top_ignore': 0.1, 'target_luma': None}
ZERO = {'stops': 0.0, 'r': 0.0, 'b': 0.0, 'sat': 1.0}


def pack_surface(sport=None):
    try:
        import sports
        return dict(SURFACE_DEFAULT, **(sports.surface(sports.load(sport)) if sport else sports.surface()))
    except BaseException:
        return dict(SURFACE_DEFAULT)


def measure(path, surface):
    a = np.asarray(Image.open(path).convert('RGB'), dtype=np.float32) / 255.0
    H = a.shape[0]; a = a[int(H * (surface.get('top_ignore') or 0)):]            # skip sky band for the surface
    full = np.asarray(Image.open(path).convert('RGB'), dtype=np.float32) / 255.0
    luma = lambda x: x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722
    mx, mn = full.max(axis=2), full.min(axis=2); s_full = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    import cv2
    hsv = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1] / 255.0, hsv[..., 2] / 255.0
    gh = surface.get('ground_hue')
    surf = np.zeros(h.shape, bool) if not gh else (h >= gh[0]) & (h <= gh[1]) & (s > 0.15) & (v > 0.08) & (v < 0.95)
    hf = cv2.cvtColor((full * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    neu = (hf[..., 1] / 255.0 < 0.12) & (hf[..., 2] / 255.0 > 0.35) & (hf[..., 2] / 255.0 < 0.95)
    out = {'frame_luma': float(np.median(luma(full))),
           'surface_frac': float(surf.mean()),
           'surface_luma': float(np.median(luma(a)[surf])) if surf.sum() > 200 else None,
           'neutral_frac': float(neu.mean()),
           'neutral_rgb': [float(full[..., c][neu].mean()) for c in range(3)] if neu.sum() > 200 else None,
           'vivid': float(((s_full > 0.75) & (mx > 0.25)).mean()),
           'clip': float((mx > 0.98).mean())}
    return out


def solve(paths, current=None, surface=None, history=None):
    """Next correction for one clip from its frames rendered WITH `current` applied."""
    cur = dict(ZERO, **(current or {})); surface = surface or pack_surface()
    st = [measure(p, surface) for p in paths]
    tgt = surface.get('target_luma')
    sl = [m['surface_luma'] for m in st if m['surface_luma'] is not None and m['surface_frac'] > 0.08]
    if tgt and len(sl) >= max(1, len(st) // 2):
        ref, basis = float(np.median(sl)), 'surface'
    else:
        ref, tgt, basis = float(np.median([m['frame_luma'] for m in st])), FRAME_LUMA, 'frame'
    pts = [h for h in (history or []) if abs(h['stops'] - cur['stops']) > 0.02]
    if pts:                                                                     # measured response of THIS clip
        h = pts[-1]; slope = (math.log2(max(ref, 1e-3)) - math.log2(max(h['luma'], 1e-3))) / (cur['stops'] - h['stops'])
        slope = float(np.clip(slope, 0.08, 1.0))
    else:
        slope = 1 / 2.4                                                         # first step: display gamma
    d = float(np.clip(math.log2(tgt / max(ref, 1e-3)) / slope, -1.5, 1.5))
    nr = [m['neutral_rgb'] for m in st if m['neutral_rgb'] and m['neutral_frac'] > 0.003]
    dr = db = 0.0
    if nr:
        r, g, b = np.median(np.array(nr), axis=0)
        dr, db = 0.8 * 2.4 * math.log2(g / max(r, 1e-3)), 0.8 * 2.4 * math.log2(g / max(b, 1e-3))
    vivid = max(m['vivid'] for m in st)
    nxt = {'stops': float(np.clip(cur['stops'] + d, -2.5, 2.5)),
           'r': float(np.clip(cur['r'] + dr, -0.6, 0.6)), 'b': float(np.clip(cur['b'] + db, -0.6, 0.6)),
           'sat': round(min(1.0, cur['sat'] * (0.9 if vivid > VIVID_MAX else 1.0)), 3)}
    return {'correction': {k: round(v, 3) for k, v in nxt.items()}, 'point': {'stops': cur['stops'], 'luma': ref},
            'converged': abs(ref - tgt) < 0.012 and abs(dr) < 0.06 and abs(db) < 0.06 and vivid <= VIVID_MAX,
            'basis': basis, 'measured_luma': round(ref, 3), 'target_luma': tgt, 'vivid_max': round(vivid, 4),
            'resolve_cdl': resolve_cdl(nxt), 'frames': st}


def resolve_cdl(c):
    o = [DI_STOP * (c['stops'] + c.get('r', 0)), DI_STOP * c['stops'], DI_STOP * (c['stops'] + c.get('b', 0))]
    return {'Slope': '1 1 1', 'Offset': ' '.join(f'{v:.4f}' for v in o), 'Power': '1 1 1',
            'Saturation': f"{c.get('sat', 1.0):.3f}"}


def lut_args(c):
    """Keyword arguments for luts.cube_path(enc, **lut_args(c)) on the ffmpeg path."""
    return {'exposure': round(2 ** c['stops'], 4), 'gains': (round(2 ** c.get('r', 0), 4), 1.0, round(2 ** c.get('b', 0), 4))}


if __name__ == '__main__':
    a = sys.argv[1:]
    opt = lambda k, dflt=None: a[a.index(k) + 1] if k in a else dflt
    sport, cur = opt('--sport'), json.loads(opt('--current', 'null') or 'null')
    imgs = [x for i, x in enumerate(a[1:], 1) if not x.startswith('--') and not a[i - 1].startswith('--')]
    surf = pack_surface(sport)
    if a and a[0] == 'measure':
        print(json.dumps({os.path.basename(p): measure(p, surf) for p in imgs}, indent=1))
    elif a and a[0] == 'batch':
        sf, clips, per = a[1], opt('--clips').split(','), int(opt('--per', 2))
        imgs = [x for x in imgs if x != sf]
        if len(imgs) != per * len(clips):
            sys.exit(f'look: {len(imgs)} frames for {len(clips)} clips x {per}')
        st = json.load(open(sf)) if os.path.exists(sf) else {}
        for i, c in enumerate(clips):
            e = st.setdefault(c, {'correction': dict(ZERO), 'history': []})
            r = solve(imgs[i * per:(i + 1) * per], e['correction'], surf, e['history'])
            e['history'].append(r['point'])
            e.update(converged=r['converged'], basis=r['basis'], measured_luma=r['measured_luma'],
                     target_luma=r['target_luma'], vivid_max=r['vivid_max'])
            if not r['converged']:
                e['correction'] = r['correction']
            e['resolve_cdl'] = resolve_cdl(e['correction'])
            print(f"{c:22s} {r['basis']:7s} luma {r['measured_luma']:.3f} -> {r['target_luma']}  "
                  f"{'converged' if r['converged'] else 'next ' + json.dumps(e['correction'])}")
        json.dump(st, open(sf, 'w'), indent=1)
    elif a and a[0] == 'solve':
        r = solve(imgs, cur, surf); r.pop('frames')
        print(json.dumps(r, indent=1))
    else:
        sys.exit(__doc__)
