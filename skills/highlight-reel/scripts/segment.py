"""Find candidate moments inside long continuous recordings (tripod/operator full halves, AI-camera
full-match files) and add them to the game as clips (segments) that survey and find then work on.

Signals, on a 0.5s grid over the whole file (one low-res decode + one audio decode, chunked in parallel):
  motion   — mean frame difference (play vs dead ball)
  crowd    — audio loudness (RMS dB) — cheers after scoring plays
  whistle  — share of audio energy in the 2.5–4.5 kHz whistle band
Each signal is z-scored against its rolling 2-min median/MAD (adapts to the venue), combined, and the
peaks become segments: [peak − pre_roll, peak + post_roll] from the sport pack, merged when they overlap,
ranked, capped at the pack's candidates_per_min. AI-camera event tags (CSV/JSON) become segments directly.

Usage:
  python3 segment.py [--file FILE_ID ...] [--per-min N] [--dry]     all long files of the game by default
  python3 segment.py --tags TAGS.csv|json --file FILE_ID [--offset SEC]
      tags: rows with a time (seconds or [HH:]MM:SS) and an optional label/type column
Writes media.clips["<file id>@<start s>"] = {file, path, in, out, score, signals, source}, plus
media.files[<id>].segmented and a signal plot checks/segments_<file>.png."""
import csv, json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

STEP = 0.5          # seconds per analysis bin
VW, VH = 160, 90    # analysis frame size
SR = 16000


def _seg_cfg():
    try:
        import sports
        sg = sports.current().get('segmentation', {})
    except SystemExit:
        sg = {}
    return {'pre': sg.get('pre_roll_s', 8), 'post': sg.get('post_roll_s', 5), 'gap': sg.get('merge_gap_s', 3),
            'per_min': sg.get('candidates_per_min', 1.5), 'min_len': sg.get('typical_play_s', [4, 25])[0]}


def _video_chunk(args):
    path, t0, dur = args
    p = subprocess.run([hrstate.tool('ffmpeg'), '-nostdin', '-v', 'error', '-hwaccel', 'videotoolbox',
                        '-ss', f'{t0:.3f}', '-t', f'{dur:.3f}', '-i', path, '-an',
                        '-vf', f'fps={1 / STEP},scale={VW}:{VH},format=gray', '-f', 'rawvideo', '-'],
                       capture_output=True)
    fr = np.frombuffer(p.stdout, np.uint8)
    return fr[:len(fr) // (VW * VH) * VW * VH].reshape(-1, VH, VW).astype(np.float32)


def video_motion(path, duration, workers=4):
    n = max(1, min(workers * 2, int(duration // 120) or 1)); step = duration / n
    with ThreadPoolExecutor(workers) as ex:
        chunks = list(ex.map(_video_chunk, [(path, i * step, step) for i in range(n)]))
    frames = np.concatenate([c for c in chunks if len(c)]) if any(len(c) for c in chunks) else np.zeros((1, VH, VW))
    d = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    return np.concatenate([[d[0] if len(d) else 0], d])


def audio_signals(path):
    p = subprocess.run([hrstate.tool('ffmpeg'), '-nostdin', '-v', 'error', '-i', path, '-vn', '-ac', '1',
                        '-ar', str(SR), '-f', 's16le', '-'], capture_output=True)
    a = np.frombuffer(p.stdout, np.int16).astype(np.float32) / 32768
    hop = int(SR * STEP); n = len(a) // hop
    if n == 0:
        return np.zeros(1), np.zeros(1)
    w = a[:n * hop].reshape(n, hop)
    rms = 20 * np.log10(np.sqrt((w ** 2).mean(axis=1)) + 1e-6)
    spec = np.abs(np.fft.rfft(w * np.hanning(hop), axis=1)) ** 2
    f = np.fft.rfftfreq(hop, 1 / SR)
    band = spec[:, (f >= 2500) & (f <= 4500)].sum(axis=1) / (spec[:, f >= 200].sum(axis=1) + 1e-9)
    return rms, band


def robust_z(x, win_s=120):
    """z-score against a rolling median/MAD so the baseline follows the venue's noise and light."""
    k = max(3, int(win_s / STEP)) | 1; pad = k // 2
    xp = np.pad(x, pad, mode='reflect') if len(x) > pad else np.pad(x, pad, mode='edge')
    from numpy.lib.stride_tricks import sliding_window_view
    sw = sliding_window_view(xp, k)[:len(x)]
    if len(x) > 20000:            # very long files: subsample the window for speed
        sw = sw[:, ::4]
    med = np.median(sw, axis=1); mad = np.median(np.abs(sw - med[:, None]), axis=1)
    gmad = np.median(np.abs(x - np.median(x))) + 1e-6
    mad = np.maximum(mad, 0.25 * gmad)              # flat stretches (gaps, edges) must not explode the z-score
    return (x - med) / (1.4826 * mad)


def smooth(x, s=1.5):
    k = max(1, int(s / STEP)) | 1
    return np.convolve(np.pad(x, k // 2, mode='reflect' if len(x) > k else 'edge'), np.ones(k) / k, mode='valid')


def candidates(motion, rms, whistle, duration, cfg, per_min=None):
    n = min(len(motion), len(rms))
    motion, rms, whistle = motion[:n], rms[:n], whistle[:n]
    zm, za, zw = robust_z(smooth(motion)), robust_z(smooth(rms)), robust_z(smooth(whistle, 1.0))
    # crowd reaction comes AFTER the play: look back a few seconds for the motion that caused it
    look = int(4 / STEP)
    zm_back = np.array([zm[max(0, i - look):i + 1].max() for i in range(n)])
    score = 0.45 * np.clip(za, 0, None) + 0.25 * np.clip(zw, 0, None) + 0.30 * np.clip(zm_back, 0, None)
    keep = int(np.ceil((per_min or cfg['per_min']) * duration / 60))
    order = np.argsort(-score); taken = []
    pre, post = int(cfg['pre'] / STEP), int(cfg['post'] / STEP)
    for i in order:                                   # non-maximum suppression: skip a peak only when an
        if score[i] <= 0.5 or len(taken) >= keep * 2:  # already-chosen window [t-pre, t+post] covers it
            break
        if all(not (j - pre <= i <= j + post) for j in taken):
            taken.append(i)
    segs = []
    for i in sorted(taken):
        t = i * STEP
        a, b = max(0.0, t - cfg['pre']), min(duration, t + cfg['post'])
        segs.append([a, b, float(score[i]), {'peak_t': round(t, 2), 'crowd_z': round(float(za[i]), 2),
                                             'whistle_z': round(float(zw[i]), 2), 'motion_z': round(float(zm_back[i]), 2)}])
    merged = []
    for s in segs:                                   # merge overlaps / near-touching
        if merged and s[0] - merged[-1][1] <= cfg['gap']:
            m = merged[-1]; m[1] = max(m[1], s[1])
            if s[2] > m[2]:
                m[2], m[3] = s[2], s[3]
        else:
            merged.append(s)
    merged.sort(key=lambda s: -s[2])
    return merged[:keep], score


def plot(path_png, score, segs):
    from PIL import Image, ImageDraw
    W, H = 1600, 220; n = len(score); im = Image.new('RGB', (W, H), (15, 15, 15)); d = ImageDraw.Draw(im)
    mx = max(1e-6, float(np.percentile(score, 99.5)))
    pts = [(int(i * W / n), H - 20 - int(min(1, score[i] / mx) * (H - 40))) for i in range(0, n, max(1, n // W))]
    for a, b, *_ in segs:
        d.rectangle([int(a / STEP * W / n), 0, int(b / STEP * W / n), H - 20], fill=(40, 70, 40))
    d.line(pts, fill=(0, 220, 255), width=1)
    for m in range(0, int(n * STEP / 60) + 1, 5):
        x = int(m * 60 / STEP * W / n); d.line([(x, H - 20), (x, H - 12)], fill=(200, 200, 200)); d.text((x + 2, H - 14), f'{m}m', fill=(200, 200, 200))
    im.save(path_png)


def _add(fid, segs, source, labels=None):
    media = hrstate.get('media'); f = media['files'][fid]; clips = media['clips']
    for k in [k for k, c in clips.items() if c.get('file') == fid and c.get('source') == source]:
        del clips[k]                                  # re-running replaces this source's segments
    for i, (a, b, sc, sig) in enumerate(segs):
        cid = f'{fid}@{int(a)}'
        c = {k: f[k] for k in ('path', 'camera', 'encoding', 'camera_type', 'orientation', 'use', 'width', 'height', 'fps', 'vfr', 'range')}
        c.update({'file': fid, 'in': round(a, 3), 'out': round(b, 3), 'duration': round(b - a, 3),
                  'score': round(sc, 3), 'signals': sig, 'source': source, 'rank': i + 1})
        if labels:
            c['label'] = labels[i]
        clips[cid] = c
    f['segmented'] = {'source': source, 'n': len(segs)}
    hrstate.set_('media', media)


def segment_file(fid, cfg, per_min=None, dry=False):
    f = hrstate.get(f'media.files.{fid}')
    dur = float(f['duration'])
    with ThreadPoolExecutor(2) as ex:
        fv = ex.submit(video_motion, f['path'], dur); fa = ex.submit(audio_signals, f['path'])
        motion, (rms, whistle) = fv.result(), fa.result()
    segs, score = candidates(motion, rms, whistle, dur, cfg, per_min)
    png = os.path.join(hrstate.sub('checks'), f'segments_{hrstate.slug(fid)}.png'); plot(png, score, segs)
    if not dry:
        _add(fid, segs, 'signals')
    return segs, png


def _t(s):
    s = str(s).strip()
    if re.fullmatch(r'[\d.]+', s):
        return float(s)
    parts = [float(p) for p in s.split(':')]
    return sum(p * 60 ** i for i, p in enumerate(reversed(parts)))


def read_tags(path):
    if path.lower().endswith('.json'):
        rows = json.load(open(path)); rows = rows.get('events', rows) if isinstance(rows, dict) else rows
    else:
        rows = list(csv.DictReader(open(path, newline='', encoding='utf-8-sig')))
    out = []
    for r in rows:
        r = {k.lower().strip(): v for k, v in r.items()}
        tk = next((k for k in r if k in ('time', 'timestamp', 'start', 'seconds', 'offset', 't', 'clip start')), None)
        if tk is None:
            continue
        lab = next((r[k] for k in ('label', 'type', 'event', 'name', 'tag', 'description') if r.get(k)), '')
        out.append((_t(r[tk]), str(lab)))
    return out


def main(a):
    cfg = _seg_cfg()
    o = {}; files = []
    i = 0
    while i < len(a):
        if a[i] == '--file':
            i += 1
            while i < len(a) and not a[i].startswith('--'):
                files.append(a[i]); i += 1
            continue
        if a[i] in ('--tags', '--per-min', '--offset'):
            o[a[i]] = a[i + 1]; i += 2; continue
        o[a[i]] = True; i += 1
    if '--tags' in o:
        if len(files) != 1:
            sys.exit('--tags needs exactly one --file')
        fid = files[0]; dur = float(hrstate.get(f'media.files.{fid}.duration'))
        off = float(o.get('--offset', 0)); tags = read_tags(o['--tags'])
        segs = [[max(0, t + off - cfg['pre']), min(dur, t + off + cfg['post']), 1.0, {'tag_t': t + off}] for t, _ in tags]
        _add(fid, segs, 'tags', [lab for _, lab in tags])
        print(f'{fid}: {len(segs)} tagged segments'); return
    files = files or (hrstate.get('media.long_files') or [])
    if not files:
        print('no long files in this game — nothing to segment'); return
    for fid in files:
        segs, png = segment_file(fid, cfg, float(o['--per-min']) if '--per-min' in o else None, '--dry' in o)
        tot = sum(b - a for a, b, *_ in segs)
        print(f'{fid}: {len(segs)} segments, {tot / 60:.1f} min of {hrstate.get(f"media.files.{fid}.duration") / 60:.1f} → plot {png}')


if __name__ == '__main__':
    main(sys.argv[1:])
