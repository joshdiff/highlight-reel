"""Shared state for the highlight-reel stages: one workspace + reel.json per game.

Workspace = <output_folder>/_hr/<team_name> - <event_name>/  holding reel.json and all
working files (frames/, frames_4k/, src2fps/, sheets/, grids/, shotlists/, reframed/).
The current workspace is remembered in $HR_HOME/current; every script uses it.

Three layers of data, none of it in the repo:
  $HR_HOME/config.json        machine/install: media_root, output_folder, power_grade_drx, camera_profile,
                              ffmpeg, ffprobe  (written by install.sh or /hr-config)
  $HR_HOME/players|teams/     profiles built up across games (hrprofile.py)
  <workspace>/reel.json       this game: settings (incl. player_id, team_id, kit), results of each stage
HR_HOME defaults to ~/.hr_work.

CLI (python3 hrstate.py ...):
  init --team T --event E --output DIR [--source DIR]   create (or reopen) a workspace, make it current
  use NAME|PATH        switch current workspace (NAME = substring of a registered workspace)
  list                 registered workspaces
  status               settings, stage progress, next stage
  path [SUB]           print workspace dir (or a subdir, created on demand)
  get KEY              dotted key, prints JSON
  set KEY VALUE        VALUE parsed as JSON, else stored as a string
  merge KEY FILE.json  deep-merge a JSON file into KEY
  done STAGE [NOTE]    mark a stage complete
  reset STAGE          mark a stage (and every later stage) not done
  config [KEY [VALUE]] show / read / write the machine config
"""
import json, os, sys, time, tempfile

HOME = os.path.expanduser(os.environ.get('HR_HOME', '~/.hr_work'))
CURRENT = os.path.join(HOME, 'current')
REGISTRY = os.path.join(HOME, 'registry.json')
CONFIG = os.path.join(HOME, 'config.json')
STAGES = ['setup', 'survey', 'find', 'select', 'direct', 'project', 'assemble', 'grade', 'title', 'export']
SUBDIRS = ['frames', 'frames_4k', 'src2fps', 'sheets', 'grids', 'shotlists', 'reframed', 'checks']


def _read(p, default):
    try:
        return json.load(open(p))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write(p, data):
    d = os.path.dirname(p); os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix='.tmp')
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, p)


def ws():
    """Current workspace dir (raises if none)."""
    env = os.environ.get('HR_WS')
    p = env or (open(CURRENT).read().strip() if os.path.exists(CURRENT) else '')
    if not p or not os.path.isdir(p):
        sys.exit('hrstate: no current workspace — run /hr-setup (or hrstate.py use NAME)')
    return p


def sub(name):
    p = os.path.join(ws(), name); os.makedirs(p, exist_ok=True); return p


def load():
    return _read(os.path.join(ws(), 'reel.json'), {})


def save(state):
    state['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    _write(os.path.join(ws(), 'reel.json'), state)


def get(key, default=None):
    cur = load()
    for k in key.split('.') if key else []:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _deep_merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _deep_merge(a[k], v)
        else:
            a[k] = v
    return a


def set_(key, value, merge=False):
    s = load(); cur = s; ks = key.split('.')
    for k in ks[:-1]:
        cur = cur.setdefault(k, {})
    if merge and isinstance(value, dict) and isinstance(cur.get(ks[-1]), dict):
        _deep_merge(cur[ks[-1]], value)
    else:
        cur[ks[-1]] = value
    save(s)


def config(key=None, default=None):
    c = _read(CONFIG, {})
    return c if key is None else c.get(key, default)


def tool(name):
    """Path of ffmpeg/ffprobe: config, else PATH, else Homebrew."""
    import shutil
    return config(name) or shutil.which(name) or f'/opt/homebrew/bin/{name}'


DEFAULT_HSV = {'canon_clog3': ((99, 30, 76), (116, 97, 180))}   # light-blue shirts; other encodings: calibrate
_warned = set()


def encoding_of(clip=None):
    """Colour encoding of a clip (from cameras.py assign), else the game's most common one."""
    if clip:
        e = get(f'media.clips.{clip}.encoding')
        if e:
            return e
    cams = get('media.encodings') or {}
    return max(cams, key=cams.get) if cams else 'canon_clog3'


def team_hsv(clip=None):
    """OpenCV HSV (H 0-180) range of our jersey FOR THIS CLIP'S ENCODING (Log and Rec.709 footage of the
    same shirt sit in different ranges): this game's calibration.team_hsv[enc], else the team profile's
    kits[settings.kit].hsv[enc], else the built-in default for that encoding."""
    enc = encoding_of(clip)
    h = (get('calibration.team_hsv') or {}).get(enc)
    if not h and get('settings.team_id'):
        import hrprofile
        h = hrprofile.kit_hsv(get('settings.team_id'), get('settings.kit', 'home'), enc)
    if h:
        return tuple(h['lo']), tuple(h['hi'])
    if enc not in DEFAULT_HSV and enc not in _warned:
        _warned.add(enc)
        print(f'hrstate: no jersey calibration for encoding {enc!r} — using the Canon Log default; '
              f'calibrate it (hr-survey step 3)', file=sys.stderr)
    return DEFAULT_HSV.get(enc, DEFAULT_HSV['canon_clog3'])


def _set_current(p):
    os.makedirs(HOME, exist_ok=True); open(CURRENT, 'w').write(p)
    reg = _read(REGISTRY, {}); reg[os.path.basename(p)] = p; _write(REGISTRY, reg)


def init(team, event, output, source=None):
    p = os.path.join(output, '_hr', f'{team} - {event}')
    for d in SUBDIRS:
        os.makedirs(os.path.join(p, d), exist_ok=True)
    _set_current(p)
    s = load()
    if not s:
        s = {'workspace': p, 'created': time.strftime('%Y-%m-%dT%H:%M:%S'),
             'settings': {'team_name': team, 'event_name': event, 'output_folder': output},
             'stages': {}}
    if source:
        s['settings']['source_folder'] = source
    save(s)
    return p


def status():
    s = load(); st = s.get('stages', {})
    print('workspace:', ws())
    for k, v in s.get('settings', {}).items():
        print(f'  {k}: {v}')
    nxt = None
    for name in STAGES:
        d = st.get(name)
        mark = f"done {d['at']}" + (f" — {d['note']}" if d.get('note') else '') if d else '-'
        print(f'  [{"x" if d else " "}] {name:9s} {mark}')
        if not d and nxt is None:
            nxt = name
    print('next stage:', nxt or 'none (reel complete)')


def main(a):
    if not a:
        print(__doc__); return
    cmd = a[0]
    if cmd == 'init':
        o = dict(zip(a[1::2], a[2::2]))
        print(init(o['--team'], o['--event'], o['--output'], o.get('--source')))
    elif cmd == 'use':
        reg = _read(REGISTRY, {})
        hit = a[1] if os.path.isdir(a[1]) else next((v for k, v in reg.items() if a[1].lower() in k.lower()), None)
        if not hit:
            sys.exit(f'no workspace matching {a[1]!r}; known: {list(reg)}')
        _set_current(hit); print(hit)
    elif cmd == 'list':
        cur = open(CURRENT).read().strip() if os.path.exists(CURRENT) else ''
        for k, v in _read(REGISTRY, {}).items():
            print(('* ' if v == cur else '  ') + k, '→', v, '' if os.path.isdir(v) else '(missing — drive unmounted?)')
    elif cmd == 'status':
        status()
    elif cmd == 'path':
        print(sub(a[1]) if len(a) > 1 else ws())
    elif cmd == 'get':
        print(json.dumps(get(a[1] if len(a) > 1 else ''), indent=2))
    elif cmd == 'set':
        try:
            v = json.loads(a[2])
        except json.JSONDecodeError:
            v = a[2]
        set_(a[1], v)
    elif cmd == 'merge':
        set_(a[1], json.load(open(a[2])), merge=True)
    elif cmd == 'done':
        set_(f'stages.{a[1]}', {'at': time.strftime('%Y-%m-%d %H:%M'), 'note': ' '.join(a[2:])})
    elif cmd == 'config':
        c = _read(CONFIG, {})
        if len(a) == 1:
            print(json.dumps(c, indent=2))
        elif len(a) == 2:
            print(json.dumps(c.get(a[1])))
        else:
            c[a[1]] = a[2]; _write(CONFIG, c)
    elif cmd == 'reset':
        s = load(); i = STAGES.index(a[1])
        for name in STAGES[i:]:
            s.get('stages', {}).pop(name, None)
        save(s)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
