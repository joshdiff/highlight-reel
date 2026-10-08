"""Clients and brands — who the videographer works for, and how their reels look and where they go.
Local only: $HR_HOME/library/clients/<id>.json, $HR_HOME/library/brands/<id>/brand.json + assets.
(Players and teams: hrprofile.py. Cameras: cameras.py.)

Client: {name, contact, brand_id, teams[], players[], output_root, output_template,
         default_orders: [{"target": "player"|"team", "type": "social_reel", "aspects": ["9:16"], "finish": "ffmpeg"}],
         notes[]}
Brand:  {name, colors {primary, secondary, text}, font, logo,
         lower_third {position_y 0-1, size 0-1 (text height / frame height), style "bar"|"plain", show_logo},
         watermark {file, position tl|tr|bl|br, scale 0-1 of width, opacity 0-1},
         intro, outro, music {folder, volume_db, duck, license_note},
         loudness {social, landscape} (LUFS), grade {cdl {slope, offset, power, sat}, creative_lut}}

CLI (python3 library.py ...):
  list [clients|brands]          show client|brand ID          new client ID --name N [--brand B] [--output-root DIR] [--template T]
  new brand ID --name N [--primary #RRGGBB] [--secondary #RRGGBB] [--text #RRGGBB]
  set client|brand ID KEY VALUE  (dotted key; VALUE parsed as JSON, else a string)
  asset BRAND logo|watermark|intro|outro|font|music|creative_lut FILE   copy a file into the brand folder
  order CLIENT --target player|team --type T [--aspects 9:16,1:1] [--finish ffmpeg|resolve]   add a default order
"""
import json, os, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

BRAND_DEFAULT = {
    'name': 'Default', 'colors': {'primary': '#111111', 'secondary': '#FFFFFF', 'text': '#FFFFFF'}, 'font': None, 'logo': None,
    'lower_third': {'position_y': 0.78, 'size': 0.03, 'style': 'bar', 'show_logo': True},
    'watermark': None, 'intro': None, 'outro': None,
    'music': {'folder': None, 'volume_db': -16, 'duck': True, 'license_note': None},
    'loudness': {'social': -14, 'landscape': -16},
    'grade': {'cdl': {'slope': 1.0, 'offset': 0.0, 'power': 1.02, 'sat': 1.1}, 'creative_lut': None},
}


def _d(kind):
    d = os.path.join(hrstate.LIB, kind + 's'); os.makedirs(d, exist_ok=True); return d


def path(kind, cid):
    return os.path.join(_d('brand'), cid, 'brand.json') if kind == 'brand' else os.path.join(_d('client'), f'{cid}.json')


def load(kind, cid):
    p = path(kind, cid)
    if not os.path.exists(p):
        sys.exit(f'library: no {kind} {cid!r} — `library.py list {kind}s`')
    return json.load(open(p))


def save(kind, cid, d):
    d['id'] = cid; d['updated'] = time.strftime('%Y-%m-%d'); hrstate._write(path(kind, cid), d)


def brand(bid=None):
    """Brand with defaults filled in; asset paths made absolute. bid None → the default look."""
    b = json.loads(json.dumps(BRAND_DEFAULT))
    if bid:
        hrstate._deep_merge(b, load('brand', bid)); base = os.path.dirname(path('brand', bid))
        for k in ('font', 'logo', 'intro', 'outro'):
            if b.get(k) and not os.path.isabs(b[k]):
                b[k] = os.path.join(base, b[k])
        if b.get('watermark') and b['watermark'].get('file') and not os.path.isabs(b['watermark']['file']):
            b['watermark']['file'] = os.path.join(base, b['watermark']['file'])
        if b['music'].get('folder') and not os.path.isabs(b['music']['folder']):
            b['music']['folder'] = os.path.join(base, b['music']['folder'])
        if b['grade'].get('creative_lut') and not os.path.isabs(b['grade']['creative_lut']):
            b['grade']['creative_lut'] = os.path.join(base, b['grade']['creative_lut'])
    return b


def all_(kind):
    d = _d(kind); out = {}
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f, 'brand.json') if kind == 'brand' else os.path.join(d, f)
        if os.path.isfile(p) and p.endswith('.json'):
            out[f[:-5] if kind == 'client' else f] = json.load(open(p))
    return out


def _set(d, key, v):
    cur = d; ks = key.split('.')
    for k in ks[:-1]:
        cur = cur.setdefault(k, {})
    cur[ks[-1]] = v


def main(a):
    if not a:
        print(__doc__); return
    cmd = a[0]; o = dict(zip(a[3::2], a[4::2])) if len(a) > 3 else {}
    if cmd == 'list':
        for kind in ([a[1].rstrip('s')] if len(a) > 1 else ['client', 'brand']):
            print(kind + 's:')
            for cid, d in all_(kind).items():
                extra = (f"brand={d.get('brand_id')} orders={len(d.get('default_orders', []))}" if kind == 'client'
                         else f"{d.get('colors', {}).get('primary', '')} logo={'y' if d.get('logo') else '-'} "
                              f"music={'y' if (d.get('music') or {}).get('folder') else '-'}")
                print(f"  {cid:18s} {d.get('name', ''):28s} {extra}")
    elif cmd == 'show':
        print(json.dumps(brand(a[2]) if a[1] == 'brand' else load(a[1], a[2]), indent=2))
    elif cmd == 'new':
        kind, cid = a[1], a[2]
        if os.path.exists(path(kind, cid)):
            sys.exit(f'{kind} {cid} exists — use set')
        if kind == 'client':
            d = {'name': o['--name'], 'contact': None, 'brand_id': o.get('--brand'), 'teams': [], 'players': [],
                 'output_root': o.get('--output-root'), 'output_template': o.get('--template'),
                 'default_orders': [], 'notes': []}
        else:
            d = {'name': o['--name'], 'colors': {'primary': o.get('--primary', '#111111'),
                                                  'secondary': o.get('--secondary', '#FFFFFF'),
                                                  'text': o.get('--text', '#FFFFFF')}}
            os.makedirs(os.path.join(_d('brand'), cid, 'music'), exist_ok=True)
        save(kind, cid, d); print(path(kind, cid))
    elif cmd == 'set':
        kind, cid, key = a[1], a[2], a[3]; d = load(kind, cid)
        try:
            v = json.loads(a[4])
        except json.JSONDecodeError:
            v = a[4]
        _set(d, key, v); save(kind, cid, d)
    elif cmd == 'asset':
        bid, kind, src = a[1], a[2], a[3]; d = load('brand', bid); base = os.path.dirname(path('brand', bid))
        if kind == 'music':
            os.makedirs(os.path.join(base, 'music'), exist_ok=True)
            shutil.copy2(src, os.path.join(base, 'music', os.path.basename(src)))
            d.setdefault('music', {})['folder'] = 'music'
        else:
            name = f'{kind}{os.path.splitext(src)[1].lower()}'; shutil.copy2(src, os.path.join(base, name))
            if kind == 'watermark':
                d['watermark'] = {**(d.get('watermark') or {'position': 'tr', 'scale': 0.12, 'opacity': 0.7}), 'file': name}
            elif kind == 'creative_lut':
                d.setdefault('grade', {})['creative_lut'] = name
            else:
                d[kind] = name
        save('brand', bid, d); print('added', kind, 'to', bid)
    elif cmd == 'order':
        cid = a[1]; o = dict(zip(a[2::2], a[3::2])); d = load('client', cid)
        d.setdefault('default_orders', []).append({'target': o.get('--target', 'player'), 'type': o['--type'],
                                                   'aspects': (o.get('--aspects') or '').split(',') if o.get('--aspects') else None,
                                                   'finish': o.get('--finish', 'ffmpeg')})
        save('client', cid, d)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
