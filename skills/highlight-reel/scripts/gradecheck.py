"""Grade check on rendered frames, against the quality bar. Shared by the Resolve and ffmpeg paths.
- exposure: with the playing surface in view (sport pack `surface`), its median luma within ±0.03 of the pack's
  target_luma — the same anchor look.py solves to; otherwise mean Rec.709 luma 0.36–0.45;
- vivid: share of pixels pushed to extreme saturation (HSV S > 0.75 with V > 0.25) — neon shirts and grass.
  A natural grade keeps this under 0.5%. (A reel judged "blown out" by its videographer measured 1.7% mean,
  10.7% max, with pale-blue shirts at S 0.62.) This replaces the old mean-saturation floor, which rewarded
  pushing colour on overcast footage;
- clip: share of pixels with any channel > 0.98;
- sat: mean HSV saturation, reported for reference only (no bar).

Usage: python3 gradecheck.py IMG...                  frames already captured
       python3 gradecheck.py --video FILE [--n 8]    sample N frames evenly from a rendered file
       add --json for machine-readable output; exit code 1 if any frame is out of range."""
import json, os, shutil, subprocess, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

LUMA = (0.36, 0.45); VIVID_MAX = 0.005; CLIP_MAX = 0.01


SURF_TOL = 0.03


def stats(img, path=None):
    a = np.asarray(img.convert('RGB'), dtype=np.float32) / 255.0
    luma = float((a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722).mean())
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = float(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0).mean())
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    vivid = float(((s > 0.75) & (mx > 0.25)).mean())
    clip = float((mx > 0.98).mean())
    surf_l, tgt = None, None
    if path:
        import look
        sf = look.pack_surface(); tgt = sf.get('target_luma')
        m = look.measure(path, sf) if tgt else {}
        if m.get('surface_luma') is not None and m.get('surface_frac', 0) > 0.08:
            surf_l = m['surface_luma']
    expo_ok = abs(surf_l - tgt) <= SURF_TOL if surf_l is not None else LUMA[0] <= luma <= LUMA[1]
    ok = expo_ok and vivid < VIVID_MAX and clip < CLIP_MAX
    return {'luma': round(luma, 3), 'surface_luma': None if surf_l is None else round(surf_l, 3),
            'sat': round(sat, 3), 'vivid_pct': round(vivid * 100, 2), 'clip_pct': round(clip * 100, 2), 'ok': ok}


def sample_video(path, n=8):
    dur = float(subprocess.run([hrstate.tool('ffprobe'), '-v', 'error', '-show_entries', 'format=duration',
                                '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip())
    d = hrstate.tmp('gradecheck'); out = []
    for i in range(n):
        t = dur * (i + 0.5) / n; f = os.path.join(d, f'g_{i:02d}.png')
        subprocess.run([hrstate.tool('ffmpeg'), '-nostdin', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', path,
                        '-frames:v', '1', f], check=True)
        out.append((f'{t:.1f}s', f))
    return out


def main(a):
    as_json = '--json' in a; a = [x for x in a if x != '--json']
    if a and a[0] == '--video':
        n = int(a[a.index('--n') + 1]) if '--n' in a else 8
        frames = sample_video(a[1], n)
    else:
        frames = [(os.path.basename(p), p) for p in a]
    res = {name: stats(Image.open(p), p) for name, p in frames}
    if a and a[0] == '--video':
        shutil.rmtree(os.path.dirname(frames[0][1]), ignore_errors=True)
    if as_json:
        print(json.dumps(res, indent=2))
    else:
        print(f"{'frame':28s} surf   luma  vivid% clip%  sat   (bar: surface ±{SURF_TOL} of the pack target, else luma "
              f"{LUMA[0]}–{LUMA[1]}; vivid <{VIVID_MAX * 100:.1f}%, clip <{CLIP_MAX * 100:.0f}%; sat for reference)")
        for k, v in res.items():
            sl = f"{v['surface_luma']:.3f}" if v['surface_luma'] is not None else '  -  '
            print(f"{k[:28]:28s} {sl}  {v['luma']:.3f} {v['vivid_pct']:5.2f}  {v['clip_pct']:5.2f}  {v['sat']:.3f}  "
                  f"{'ok' if v['ok'] else 'OUT'}")
    sys.exit(0 if all(v['ok'] for v in res.values()) else 1)


if __name__ == '__main__':
    main(sys.argv[1:])
