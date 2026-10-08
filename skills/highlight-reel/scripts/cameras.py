"""Cameras & footage types — a game can mix several (a cinema/mirrorless body in Log, a phone in HDR,
an action cam, an AI sports camera), so camera is decided PER CLIP.

Camera profiles: $HR_HOME/library/cameras/<id>.json (local, never in the repo; see examples/camera.example.json)
  {"name": "Canon EOS R7", "type": "mirrorless",           # mirrorless|cinema|phone|action|ai_panoramic|export|other
                                                             # export = already-edited renders: skipped by the survey
   "match": {"prefix": ["R7_"], "brand": "CAEP", "codec": "hevc"},   # every given field must match
                                                             # (also: make, model, transfer, min_aspect)
   "encoding": "canon_clog3",                                # key of ENCODINGS below
   "notes": ["full-range HEVC 4:2:2 10-bit"]}

Metadata rarely says whether footage is Log (Canon writes no transfer tag), so `encoding` comes from the
profile; `looks` (flat vs contrasty frames, from the survey) is a cross-check that flags a camera shot in
its non-Log profile.

CLI (python3 cameras.py ...):
  probe DIR|FILE...     ffprobe every clip, match to profiles, group unknown signatures (fast; no frames)
  assign [DIR...]       probe the current game's sources → media.files (per file), media.clips (one per
                        short file), media.cameras / encodings / long_files
  list                  camera profiles
  new ID [--from-preset P] --name N --type T --encoding E [--prefix P] [--brand B] [--codec C]
         [--make M] [--model M] [--transfer T] [--lut FILE.cube]   (lut: official Log→Rec.709 LUT for /hr-finish)
  presets               camera presets shipped in the repo (suggested for unknown cameras by probe)
  encodings             known encodings and their Resolve input colour space
"""
import json, os, re, subprocess, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

# encoding → Resolve "Input Color Space" short name (long "X / Y" forms are rejected), is it log/HDR,
# and the frame-look we expect. Names marked verify=True: read back after setting; adjust here if Resolve
# reports a different spelling.
ENCODINGS = {
    'canon_clog3': {'resolve': 'Canon Cinema Gamut/Canon Log 3', 'kind': 'log'},
    'canon_clog2': {'resolve': 'Canon Cinema Gamut/Canon Log 2', 'kind': 'log', 'verify': True},
    'sony_slog3':  {'resolve': 'S-Gamut3.Cine/S-Log3', 'kind': 'log'},
    'panasonic_vlog': {'resolve': 'Panasonic V-Gamut/V-Log', 'kind': 'log', 'verify': True},
    'fuji_flog2':  {'resolve': 'FujiFilm F-Gamut/F-Log2', 'kind': 'log', 'verify': True},
    'dji_dlog':    {'resolve': 'DJI D-Gamut/D-Log', 'kind': 'log', 'verify': True},
    'apple_log':   {'resolve': 'Apple Log', 'kind': 'log', 'verify': True},
    'rec2100_hlg': {'resolve': 'Rec.2100 HLG', 'kind': 'hdr', 'verify': True},
    'rec2100_pq':  {'resolve': 'Rec.2100 ST2084', 'kind': 'hdr', 'verify': True},
    'rec709':      {'resolve': 'Rec.709 Gamma 2.4', 'kind': 'sdr'},
}
VIDEO_EXT = ('.mp4', '.mov', '.mxf', '.m4v')


def _dir():
    d = os.path.join(hrstate.LIB, 'cameras'); os.makedirs(d, exist_ok=True); return d


def profiles():
    return {f[:-5]: json.load(open(os.path.join(_dir(), f))) for f in sorted(os.listdir(_dir())) if f.endswith('.json')}


def _rate(r):
    try:
        n, d = r.split('/'); return float(n) / float(d) if float(d) else 0.0
    except Exception:
        return 0.0


def signature(path):
    """Everything we can learn from metadata alone."""
    o = json.loads(subprocess.run(
        [hrstate.tool('ffprobe'), '-v', 'error', '-show_entries',
         'format=duration:format_tags:stream=codec_type,codec_name,profile,width,height,r_frame_rate,avg_frame_rate,'
         'pix_fmt,color_range,color_transfer,color_primaries:stream_tags', '-of', 'json', path],
        capture_output=True, text=True).stdout or '{}')
    v = next((s for s in o.get('streams', []) if s.get('codec_type') == 'video'), {})
    ft = {k.lower(): str(val) for k, val in o.get('format', {}).get('tags', {}).items()}
    st = {k.lower(): str(val) for k, val in v.get('tags', {}).items()}
    tags = {**ft, **st}
    name = os.path.splitext(os.path.basename(path))[0]
    m = re.match(r'^([A-Za-z]+[A-Za-z0-9]*?_+|[A-Za-z]+)', name)
    r, avg = _rate(v.get('r_frame_rate', '0/1')), _rate(v.get('avg_frame_rate', '0/1'))
    make = tags.get('com.apple.quicktime.make') or tags.get('make') or ''
    model = tags.get('com.apple.quicktime.model') or tags.get('model') or ''
    return {
        'name': name, 'path': path, 'prefix': m.group(1) if m else '',
        'brand': ft.get('compatible_brands', '') + ' ' + ft.get('major_brand', ''),
        'make': make.strip(), 'model': model.strip(), 'codec': v.get('codec_name', ''),
        'profile': v.get('profile', ''), 'pix_fmt': v.get('pix_fmt', ''),
        'width': v.get('width'), 'height': v.get('height'),
        'fps': round(avg or r, 3), 'vfr': bool(r and avg and abs(r - avg) > 0.05),
        'range': v.get('color_range', ''), 'transfer': v.get('color_transfer', ''),
        'primaries': v.get('color_primaries', ''), 'duration': float(o.get('format', {}).get('duration', 0) or 0),
    }


def guess_encoding(sig):
    """Only what metadata can prove: HLG/PQ transfers. Log is never provable from tags."""
    return {'arib-std-b67': 'rec2100_hlg', 'smpte2084': 'rec2100_pq'}.get(sig['transfer'])


def _matches(sig, m):
    if not m:
        return False
    if m.get('prefix') and not any(sig['name'].startswith(x) for x in m['prefix']):
        return False
    if m.get('brand') and m['brand'] not in sig['brand']:
        return False
    for k in ('codec', 'make', 'model', 'transfer'):
        if m.get(k) and m[k].lower() not in (sig.get(k) or '').lower():
            return False
    if m.get('min_aspect') and (sig['width'] or 0) / max(1, sig['height'] or 1) < m['min_aspect']:
        return False
    return True


def match(sig, profs=None):
    for cid, p in (profs if profs is not None else profiles()).items():
        if _matches(sig, p.get('match', {})):
            return cid
    return None


PRESETS_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'presets', 'cameras'))


def presets():
    if not os.path.isdir(PRESETS_DIR):
        return {}
    return {f[:-5]: json.load(open(os.path.join(PRESETS_DIR, f))) for f in sorted(os.listdir(PRESETS_DIR)) if f.endswith('.json')}


def suggest(sig):
    """Preset ids whose match rules fit this signature (suggestions only — confirm the picture profile)."""
    return [pid for pid, p in presets().items() if _matches(sig, p.get('match', {}))]


def files_in(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            out += [os.path.join(p, f) for f in sorted(os.listdir(p))
                    if f.lower().endswith(VIDEO_EXT) and not f.startswith('._')]
        else:
            out.append(p)
    return out


def probe(paths):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:
        sigs = list(ex.map(signature, files_in(paths)))
    profs = profiles()
    for s in sigs:
        s['camera'] = match(s, profs)
        enc = profs[s['camera']]['encoding'] if s['camera'] else guess_encoding(s)
        s['encoding'] = enc
    return sigs


def summary(sigs):
    known = Counter(s['camera'] for s in sigs if s['camera'])
    unknown = defaultdict(list)
    for s in sigs:
        if not s['camera']:
            key = (s['prefix'], s['make'] or '-', s['model'] or '-', s['codec'], f"{s['width']}x{s['height']}",
                   s['fps'], 'VFR' if s['vfr'] else 'CFR', s['transfer'] or '-')
            unknown[key].append(s)
    profs = profiles()
    lines = []
    for cid, n in known.most_common():
        p = profs[cid]
        lines.append(f"  {cid:14s} {n:4d} clips  {p['name']} [{p.get('type')}] encoding={p['encoding']}")
    for k, group in unknown.items():
        sug = suggest(group[0])
        lines.append(f"  UNKNOWN       {len(group):4d} clips  prefix={k[0]!r} make={k[1]} model={k[2]} {k[3]} {k[4]} "
                     f"{k[5]}fps {k[6]} transfer={k[7]}  e.g. {group[0]['name']}"
                     + (f"\n                 suggested presets: {', '.join(sug)}" if sug else ''))
    fps = Counter(s['fps'] for s in sigs); res = Counter(s['height'] for s in sigs)
    lines.append(f"  frame rates: {dict(fps)}   heights: {dict(res)}   VFR clips: {sum(s['vfr'] for s in sigs)}")
    return '\n'.join(lines), bool(unknown)


LONG_DEFAULT_S = 180   # files longer than this are "long" (continuous recording) unless the sport pack says otherwise


def assign(folders=None, long_s=None):
    """Probe every source of the current game. media.files[<file id>] holds each file's signature;
    short files also become one clip each (media.clips[<id>] = whole file, in 0 → out duration);
    long files are flagged for segment.py, which adds their clips. Ids stay unique across cards
    (a second R7__0001 from another folder becomes <folder>-R7__0001)."""
    folders = folders or hrstate.get('sources') or []
    if long_s is None:
        try:
            import sports
            long_s = sports.load(hrstate.get('sport')).get('segmentation', {}).get('max_clip_s', LONG_DEFAULT_S)
        except Exception:
            long_s = LONG_DEFAULT_S
    sigs = probe(folders)
    media = hrstate.get('media') or {}
    files, clips = media.get('files', {}), media.get('clips', {})
    by_path = {f['path']: fid for fid, f in files.items()}
    profs = profiles()
    for sg in sigs:
        fid = by_path.get(sg['path'])
        if not fid:
            fid = sg['name']
            if fid in files and files[fid]['path'] != sg['path']:
                fid = f"{hrstate.slug(os.path.basename(os.path.dirname(sg['path'])))}-{sg['name']}"
        sg['id'] = fid
        f = files.setdefault(fid, {})
        f.update({k: sg[k] for k in ('path', 'camera', 'encoding', 'width', 'height', 'fps', 'vfr', 'range', 'duration')})
        f['camera_type'] = profs[sg['camera']].get('type') if sg['camera'] else None
        f['orientation'] = 'portrait' if (sg['height'] or 0) > (sg['width'] or 0) else 'landscape'
        f['use'] = f['camera_type'] != 'export'
        f['long'] = (sg['duration'] or 0) > long_s
        if not f['long']:
            c = clips.setdefault(fid, {})
            c.update({k: f[k] for k in f if k != 'long'}, file=fid, **{'in': 0.0, 'out': round(sg['duration'], 3)})
        else:   # long-file clips come from segment.py; refresh their file properties
            for c in clips.values():
                if c.get('file') == fid:
                    c.update({k: f[k] for k in ('path', 'camera', 'encoding', 'camera_type', 'orientation', 'use')})
    media.update(files=files, clips=clips,
                 cameras=dict(Counter(f.get('camera') or 'unknown' for f in files.values())),
                 encodings=dict(Counter(f.get('encoding') or 'unknown' for f in files.values() if f['use'])),
                 long_files=[fid for fid, f in files.items() if f['long'] and f['use']])
    hrstate.set_('media', media)
    return sigs


def main(a):
    if not a:
        print(__doc__); return
    cmd = a[0]
    if cmd == 'probe':
        text, unk = summary(probe(a[1:])); print(text)
        if unk:
            print('→ create a profile for each UNKNOWN group (cameras.py new …) — ask the user which camera and colour profile it is.')
    elif cmd == 'assign':
        sigs = assign(a[1:] or None); text, unk = summary(sigs); print(text)
        lf = hrstate.get('media.long_files') or []
        if lf:
            print(f'  long files (need segment.py): {len(lf)}')
        if unk:
            sys.exit('unknown cameras present — add profiles, then re-run assign')
    elif cmd == 'list':
        for cid, p in profiles().items():
            print(f"  {cid:14s} {p['name']:24s} [{p.get('type')}] {p['encoding']:12s} match={p.get('match')}")
    elif cmd == 'new':
        cid = a[1]; o = dict(zip(a[2::2], a[3::2]))
        base = presets().get(o.get('--from-preset'), {}) if o.get('--from-preset') else {}
        if o.get('--from-preset') and not base:
            sys.exit(f"no preset {o['--from-preset']!r}; see `cameras.py presets`")
        enc = o.get('--encoding', base.get('encoding'))
        if enc not in ENCODINGS:
            sys.exit(f"unknown encoding; one of {list(ENCODINGS)}")
        m = dict(base.get('match', {}))
        m.update({k: o[f'--{k}'] for k in ('brand', 'codec', 'make', 'model', 'transfer') if o.get(f'--{k}')})
        if o.get('--prefix'):
            m['prefix'] = o['--prefix'].split(',')
        if not m:
            sys.exit('give at least one match field (--prefix/--brand/--codec/--make/--model/--transfer)')
        p = {'id': cid, 'name': o.get('--name', base.get('name', cid)), 'type': o.get('--type', base.get('type', 'other')),
             'match': m, 'encoding': enc, 'lut': o.get('--lut'), 'notes': list(base.get('notes', []))}
        hrstate._write(os.path.join(_dir(), f'{cid}.json'), p); print(os.path.join(_dir(), f'{cid}.json'))
    elif cmd == 'presets':
        for pid, p in presets().items():
            print(f"  {pid:16s} {p['name']:44s} [{p['type']}] {p['encoding']:12s} match={p['match']}")
    elif cmd == 'encodings':
        for k, v in ENCODINGS.items():
            print(f"  {k:15s} {v['kind']:4s} → {v['resolve']}" + ('  (verify name on read-back)' if v.get('verify') else ''))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
