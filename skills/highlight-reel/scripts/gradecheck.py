"""Grade check on rendered frames: mean luma (Rec.709 weights), mean HSV saturation and clipped share
(any channel > 0.98) per frame, against the quality bar. Shared by the Resolve and ffmpeg paths.

Usage: python3 gradecheck.py IMG...                  frames already captured
       python3 gradecheck.py --video FILE [--n 8]    sample N frames evenly from a rendered file
       add --json for machine-readable output; exit code 1 if any frame is out of range."""
import json, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

LUMA = (0.36, 0.45); SAT_MIN = 0.35; CLIP_MAX = 0.01


def stats(img):
    a = np.asarray(img.convert('RGB'), dtype=np.float32) / 255.0
    luma = float((a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722).mean())
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = float(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0).mean())
    clip = float((mx > 0.98).mean())
    ok = LUMA[0] <= luma <= LUMA[1] and sat >= SAT_MIN and clip < CLIP_MAX
    return {'luma': round(luma, 3), 'sat': round(sat, 3), 'clip_pct': round(clip * 100, 2), 'ok': ok}


def sample_video(path, n=8):
    dur = float(subprocess.run([hrstate.tool('ffprobe'), '-v', 'error', '-show_entries', 'format=duration',
                                '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip())
    d = tempfile.mkdtemp(); out = []
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
    res = {name: stats(Image.open(p)) for name, p in frames}
    if as_json:
        print(json.dumps(res, indent=2))
    else:
        print(f"{'frame':28s} luma  sat   clip%  (bar: luma {LUMA[0]}–{LUMA[1]}, sat ≥{SAT_MIN}, clip <{CLIP_MAX * 100:.0f}%)")
        for k, v in res.items():
            print(f"{k[:28]:28s} {v['luma']:.3f} {v['sat']:.3f} {v['clip_pct']:5.2f}  {'ok' if v['ok'] else 'OUT'}")
    sys.exit(0 if all(v['ok'] for v in res.values()) else 1)


if __name__ == '__main__':
    main(sys.argv[1:])
