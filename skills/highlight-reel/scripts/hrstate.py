"""State for highlight-reel: Session → Game → Target → Deliverable.

Layout (under <output_folder>/_hr/, output_folder from the machine config):
  sessions/<name>/session.json        a day's queue: games + deliverables, priority
  games/<game id>/game.json           sport, sources, media.clips (segments), teams, calibration, stages
  games/<game id>/{frames,frames_4k,src2fps,sheets,grids,checks}/          survey output (shared)
  games/<game id>/targets/<id>/find.json                                   a player or team to find
  games/<game id>/deliverables/<id>/deliv.json + {shotlists,reframed,checks}/   one output reel

Local, never in the repo ($HR_HOME, default ~/.hr_work):
  config.json  machine settings (hrstate.py config)      library/  profiles (hrprofile.py, cameras.py)
  current.json the current session/game/target/deliv    registry.json known games and sessions

A "clip" is a segment of a source file: media.clips[<id>] = {path, in, out, camera, encoding, ...}.
Short files: id = file name, in 0, out duration. Long files: ids like GX010042@1872 (segment.py).

CLI (python3 hrstate.py ...):
  config [KEY [VALUE]]
  new-game --date YYYY-MM-DD --home NAME --away NAME --sport S --source DIR [--source DIR…]
           [--home-team ID] [--away-team ID] [--home-kit home] [--away-kit away] [--event TEXT]
  new-target ID --kind player|team [--player PLAYER_ID] --team TEAM_ID|home|away
  new-deliv ID --target TARGET_ID --type social_reel|recruiting_tape|goals_reel|season_reel
           [--aspects 9:16,1:1] [--finish ffmpeg|resolve] [--client ID] [--brand ID]
  new-session NAME            session add-game [GAME]      session add-deliv GAME DELIV [PRIORITY]
  use session|game NAME|PATH   use target|deliv ID          list [games|sessions]
  status                      next (the next unfinished unit of the current session; makes it current)
  [SCOPE] get KEY | set KEY VALUE | merge KEY FILE | done STAGE [NOTE] | reset STAGE | path [SUB]
      SCOPE = game (default) | target | deliv | session, optionally SCOPE:ID (e.g. deliv:alex-social)
  clean [GAME] [--force]      delete survey frames + reframes once every deliverable is exported
"""
import json, os, re, shutil, sys, time, tempfile

HOME = os.path.expanduser(os.environ.get('HR_HOME', '~/.hr_work'))
LIB = os.path.join(HOME, 'library')
CURRENT = os.path.join(HOME, 'current.json')
REGISTRY = os.path.join(HOME, 'registry.json')
CONFIG = os.path.join(HOME, 'config.json')

GAME_STAGES = ['ingest', 'survey']
TARGET_STAGES = ['find']
DELIV_STAGES = {'ffmpeg': ['select', 'direct', 'finish', 'export'],
                'resolve': ['select', 'direct', 'project', 'assemble', 'grade', 'title', 'export']}
GAME_SUBDIRS = ['frames', 'frames_4k', 'src2fps', 'sheets', 'grids', 'checks', 'targets', 'deliverables']
DELIV_SUBDIRS = ['shotlists', 'reframed', 'checks']
FILES = {'game': 'game.json', 'target': 'find.json', 'deliv': 'deliv.json', 'session': 'session.json'}


# ---------- io ----------
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


def _deep_merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _deep_merge(a[k], v)
        else:
            a[k] = v
    return a


def _now():
    return time.strftime('%Y-%m-%dT%H:%M:%S')


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', str(s).lower()).strip('-')


# ---------- machine config ----------
def config(key=None, default=None):
    c = _read(CONFIG, {})
    return c if key is None else c.get(key, default)


def tool(name):
    """Path of ffmpeg/ffprobe: config, else PATH, else Homebrew."""
    return config(name) or shutil.which(name) or f'/opt/homebrew/bin/{name}'


def root():
    out = config('output_folder')
    if not out:
        sys.exit('hrstate: no output_folder configured — run install.sh or /hr-config')
    return os.path.join(out, '_hr')


# ---------- current pointers ----------
def current():
    return _read(CURRENT, {})


def _set_current(**kw):
    c = current(); c.update(kw); _write(CURRENT, c)


def _register(kind, name, path):
    r = _read(REGISTRY, {}); r.setdefault(kind, {})[name] = path; _write(REGISTRY, r)


def game_dir(gid=None):
    if gid:
        p = gid if os.path.isdir(gid) else (_read(REGISTRY, {}).get('games', {}).get(gid)
                                            or os.path.join(root(), 'games', gid))
    else:
        p = os.environ.get('HR_GAME') or current().get('game') or ''
    if not p or not os.path.isdir(p):
        sys.exit('hrstate: no current game — create one (new-game / /hr-session) or `hrstate.py use game NAME`')
    return p


def session_dir():
    p = current().get('session') or ''
    if not p or not os.path.isdir(p):
        sys.exit('hrstate: no current session — `hrstate.py new-session NAME` or `use session NAME`')
    return p


def target_dir(tid=None, gid=None):
    tid = tid or current().get('target')
    if not tid:
        sys.exit('hrstate: no current target — `hrstate.py use target ID`')
    return os.path.join(game_dir(gid), 'targets', tid)


def deliv_dir(did=None, gid=None):
    did = did or current().get('deliv')
    if not did:
        sys.exit('hrstate: no current deliverable — `hrstate.py use deliv ID`')
    return os.path.join(game_dir(gid), 'deliverables', did)


def _scope_dir(scope, sid=None):
    return {'game': lambda: game_dir(sid), 'target': lambda: target_dir(sid), 'deliv': lambda: deliv_dir(sid),
            'session': lambda: session_dir()}[scope]()


def sub(name, gid=None):
    """Game-level working dir (frames, sheets, …), created on demand."""
    p = os.path.join(game_dir(gid), name); os.makedirs(p, exist_ok=True); return p


def dsub(name, did=None):
    """Deliverable-level working dir (shotlists, reframed, checks), created on demand."""
    p = os.path.join(deliv_dir(did), name); os.makedirs(p, exist_ok=True); return p


# ---------- generic scoped state ----------
def load(scope='game', sid=None):
    return _read(os.path.join(_scope_dir(scope, sid), FILES[scope]), {})


def save(state, scope='game', sid=None):
    state['updated'] = _now()
    _write(os.path.join(_scope_dir(scope, sid), FILES[scope]), state)


def get(key, default=None, scope='game', sid=None):
    cur = load(scope, sid)
    for k in key.split('.') if key else []:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def set_(key, value, merge=False, scope='game', sid=None):
    s = load(scope, sid); cur = s; ks = key.split('.')
    for k in ks[:-1]:
        cur = cur.setdefault(k, {})
    if merge and isinstance(value, dict) and isinstance(cur.get(ks[-1]), dict):
        _deep_merge(cur[ks[-1]], value)
    else:
        cur[ks[-1]] = value
    save(s, scope, sid)


def stages_for(scope, sid=None):
    if scope == 'game':
        return GAME_STAGES
    if scope == 'target':
        return TARGET_STAGES
    return DELIV_STAGES[get('finish_path', 'ffmpeg', 'deliv', sid)]


def done(scope, stage, note='', sid=None):
    set_(f'stages.{stage}', {'at': time.strftime('%Y-%m-%d %H:%M'), 'note': note}, scope=scope, sid=sid)


def reset(scope, stage, sid=None):
    s = load(scope, sid); st = stages_for(scope, sid)
    for name in st[st.index(stage):]:
        s.get('stages', {}).pop(name, None)
    save(s, scope, sid)


# ---------- creation ----------
def new_game(date, home, away, sport, sources, home_team=None, away_team=None,
             home_kit='home', away_kit='away', event=None):
    gid = f'{date} {home} vs {away}'
    p = os.path.join(root(), 'games', gid)
    for d in GAME_SUBDIRS:
        os.makedirs(os.path.join(p, d), exist_ok=True)
    g = _read(os.path.join(p, 'game.json'), {}) or {
        'id': gid, 'created': _now(), 'date': date, 'sport': sport, 'event': event or away,
        'teams': {'home': {'team_id': home_team, 'name': home, 'kit': home_kit},
                  'away': {'team_id': away_team, 'name': away, 'kit': away_kit}},
        'sources': [], 'media': {'clips': {}}, 'calibration': {}, 'stages': {}}
    g['sources'] = sorted(set(g.get('sources', []) + [os.path.abspath(s) for s in sources]))
    _write(os.path.join(p, 'game.json'), g)
    _register('games', gid, p); _set_current(game=p, target=None, deliv=None)
    return p


def team_key(team_id_or_side):
    """Find a game team by team_id or side ('home'/'away') → (side, entry)."""
    for side, t in (get('teams') or {}).items():
        if team_id_or_side in (side, t.get('team_id')):
            return side, t
    sys.exit(f'hrstate: team {team_id_or_side!r} is not in this game ({list(get("teams") or {})})')


def new_target(tid, kind, team, player=None):
    side, t = team_key(team)
    p = os.path.join(game_dir(), 'targets', tid); os.makedirs(p, exist_ok=True)
    f = os.path.join(p, 'find.json')
    if not os.path.exists(f):
        _write(f, {'id': tid, 'kind': kind, 'player_id': player, 'team_id': t.get('team_id'),
                   'side': side, 'clips': {}, 'stages': {}, 'created': _now()})
    _set_current(target=tid)
    return p


def new_deliv(did, target, dtype, aspects=None, finish='ffmpeg', client=None, brand=None):
    if not os.path.exists(os.path.join(game_dir(), 'targets', target or '-', 'find.json')):
        sys.exit(f'hrstate: no target {target!r} in this game — new-target first')
    p = os.path.join(game_dir(), 'deliverables', did)
    for d in DELIV_SUBDIRS:
        os.makedirs(os.path.join(p, d), exist_ok=True)
    f = os.path.join(p, 'deliv.json')
    if not os.path.exists(f):
        _write(f, {'id': did, 'target': target, 'type': dtype,
                   'aspects': aspects or (['9:16'] if dtype == 'social_reel' else ['16:9']),
                   'finish_path': finish, 'client_id': client, 'brand_id': brand,
                   'stages': {}, 'created': _now()})
    _set_current(deliv=did, target=target)
    return p


def new_session(name):
    p = os.path.join(root(), 'sessions', name); os.makedirs(p, exist_ok=True)
    f = os.path.join(p, 'session.json')
    if not os.path.exists(f):
        _write(f, {'id': name, 'created': _now(), 'games': [], 'queue': [], 'notes': []})
    _register('sessions', name, p); _set_current(session=p)
    return p


def session_add_game(gpath=None):
    gpath = game_dir(gpath); s = load('session')
    if gpath not in s['games']:
        s['games'].append(gpath)
    save(s, 'session')


def session_add_deliv(gpath, did, priority=5):
    gpath = game_dir(gpath); s = load('session')
    if gpath not in s['games']:
        s['games'].append(gpath)
    s['queue'] = [q for q in s['queue'] if not (q['game'] == gpath and q['deliv'] == did)]
    s['queue'].append({'game': gpath, 'deliv': did, 'priority': int(priority)})
    s['queue'].sort(key=lambda q: q['priority'])
    save(s, 'session')


# ---------- queue ----------
def _stages_done(path, fname):
    return _read(os.path.join(path, fname), {}).get('stages', {})


def next_unit():
    """Next unfinished unit of the current session: game stages for every game first (the expensive,
    shared work), then each needed target's find, then deliverables in priority order."""
    s = load('session')
    for g in s['games']:
        st = _stages_done(g, 'game.json')
        for stage in GAME_STAGES:
            if stage not in st:
                return {'scope': 'game', 'game': g, 'id': os.path.basename(g), 'stage': stage}
    for q in s['queue']:
        tgt = _read(os.path.join(q['game'], 'deliverables', q['deliv'], 'deliv.json'), {}).get('target')
        if tgt and 'find' not in _stages_done(os.path.join(q['game'], 'targets', tgt), 'find.json'):
            return {'scope': 'target', 'game': q['game'], 'id': tgt, 'stage': 'find'}
    for q in s['queue']:
        d = _read(os.path.join(q['game'], 'deliverables', q['deliv'], 'deliv.json'), {})
        for stage in DELIV_STAGES[d.get('finish_path', 'ffmpeg')]:
            if stage not in d.get('stages', {}):
                return {'scope': 'deliv', 'game': q['game'], 'id': q['deliv'], 'stage': stage}
    return None


def _use_unit(u):
    _set_current(game=u['game'])
    if u['scope'] == 'target':
        _set_current(target=u['id'])
    elif u['scope'] == 'deliv':
        d = _read(os.path.join(u['game'], 'deliverables', u['id'], 'deliv.json'), {})
        _set_current(deliv=u['id'], target=d.get('target'))


# ---------- status ----------
def _mark(stages, names):
    return ' '.join(('✓' if n in stages else '·') + n for n in names)


def _game_board(g):
    gj = _read(os.path.join(g, 'game.json'), {})
    teams = ' vs '.join(t['name'] for t in gj.get('teams', {}).values())
    cams = gj.get('media', {}).get('cameras', {})
    lines = [f"GAME {gj.get('id', os.path.basename(g))}  [{gj.get('sport')}]  {teams}  "
             f"clips={len(gj.get('media', {}).get('clips', {}))} cameras={cams or '-'}",
             f"   {_mark(gj.get('stages', {}), GAME_STAGES)}"]
    td = os.path.join(g, 'targets')
    for t in sorted(x for x in os.listdir(td) if os.path.isdir(os.path.join(td, x))) if os.path.isdir(td) else []:
        tj = _read(os.path.join(td, t, 'find.json'), {})
        who = tj.get('player_id') or f"team {tj.get('team_id') or tj.get('side')}"
        lines.append(f"   target {t:18s} {who:20s} {_mark(tj.get('stages', {}), TARGET_STAGES)}")
    dd = os.path.join(g, 'deliverables')
    for d in sorted(x for x in os.listdir(dd) if os.path.isdir(os.path.join(dd, x))) if os.path.isdir(dd) else []:
        dj = _read(os.path.join(dd, d, 'deliv.json'), {})
        out = (dj.get('export') or {}).get('files') or ''
        lines.append(f"   deliv  {d:18s} {dj.get('type', ''):15s} {','.join(dj.get('aspects', []))} "
                     f"[{dj.get('finish_path')}] {_mark(dj.get('stages', {}), DELIV_STAGES[dj.get('finish_path', 'ffmpeg')])}"
                     + (f"  → {out}" if out else ''))
        for f in dj.get('flags', []):
            lines.append(f"          ! {f}")
    return lines


def status():
    c = current()
    if c.get('session') and os.path.isdir(c['session']):
        s = load('session')
        print(f"SESSION {s['id']}  ({len(s['games'])} games, {len(s['queue'])} deliverables)")
        for g in s['games']:
            print('\n'.join(_game_board(g)))
        u = next_unit()
        print('next:', f"{u['scope']} {u['id']} → {u['stage']}" if u else 'nothing — session complete')
    elif c.get('game') and os.path.isdir(c['game']):
        print('\n'.join(_game_board(c['game'])))
    else:
        print('no current session or game')
    print('current:', {k: (os.path.basename(v) if v and os.sep in str(v) else v) for k, v in c.items()})


# ---------- jersey colour per clip ----------
DEFAULT_HSV = {'canon_clog3': ((99, 30, 76), (116, 97, 180))}   # light-blue shirts; other encodings: calibrate
_warned = set()


def encoding_of(clip=None):
    """Colour encoding of a clip (from cameras.py assign), else the game's most common one."""
    if clip:
        e = get(f'media.clips.{clip}.encoding')
        if e:
            return e
    encs = get('media.encodings') or {}
    return max(encs, key=encs.get) if encs else 'canon_clog3'


def team_hsv(clip=None, team=None):
    """OpenCV HSV (H 0-180) range of a team's shirt FOR THIS CLIP'S ENCODING. team = team_id or side;
    default = the current target's team, else home. Order: game calibration.team_hsv.<side>.<enc>,
    else the team profile's kits.<kit>.hsv.<enc>, else the built-in default."""
    if team is None:
        tj = _read(os.path.join(game_dir(), 'targets', current().get('target') or '-', 'find.json'), {})
        team = tj.get('side') or 'home'
    side, t = team_key(team)
    enc = encoding_of(clip)
    h = (get(f'calibration.team_hsv.{side}') or {}).get(enc)
    if not h and t.get('team_id'):
        import hrprofile
        h = hrprofile.kit_hsv(t['team_id'], t.get('kit', 'home'), enc)
    if h:
        return tuple(h['lo']), tuple(h['hi'])
    if (side, enc) not in _warned:
        _warned.add((side, enc))
        print(f'hrstate: no shirt calibration for {side} ({t.get("name")}) on {enc!r} — using the default; '
              f'calibrate it (hr-survey)', file=sys.stderr)
    return DEFAULT_HSV.get(enc, DEFAULT_HSV['canon_clog3'])


def calibrated(team, enc):
    """True when a real calibration exists for this team on this encoding (not the fallback)."""
    side, t = team_key(team)
    if (get(f'calibration.team_hsv.{side}') or {}).get(enc):
        return True
    if t.get('team_id'):
        import hrprofile
        return bool(hrprofile.kit_hsv(t['team_id'], t.get('kit', 'home'), enc))
    return False


# ---------- cleanup ----------
def clean(gid=None, force=False):
    g = game_dir(gid); dd = os.path.join(g, 'deliverables')
    delivs = [x for x in os.listdir(dd) if os.path.isdir(os.path.join(dd, x))] if os.path.isdir(dd) else []
    pending = [d for d in delivs if 'export' not in _stages_done(os.path.join(dd, d), 'deliv.json')]
    if pending and not force:
        sys.exit(f'not cleaning: deliverables not exported yet: {pending} (use --force)')
    freed = 0
    for p in [os.path.join(g, x) for x in ('frames', 'frames_4k', 'src2fps', 'grids')] + \
             [os.path.join(dd, d, 'reframed') for d in delivs]:
        if os.path.isdir(p):
            for r, _, fs in os.walk(p):
                freed += sum(os.path.getsize(os.path.join(r, f)) for f in fs)
            shutil.rmtree(p)
    set_('cleaned', _now(), sid=g)
    print(f'freed {freed / 1e9:.2f} GB in {os.path.basename(g)}')


# ---------- CLI ----------
def _val(x):
    try:
        return json.loads(x)
    except json.JSONDecodeError:
        return x


def _opts(a):
    o = {}
    for k, v in zip(a[0::2], a[1::2]):
        o.setdefault(k, []).append(v)
    return o


def main(a):
    if not a:
        print(__doc__); return
    cmd = a[0]
    if cmd == 'config':
        c = _read(CONFIG, {})
        if len(a) == 1:
            print(json.dumps(c, indent=2))
        elif len(a) == 2:
            print(json.dumps(c.get(a[1])))
        else:
            c[a[1]] = a[2]; _write(CONFIG, c)
    elif cmd == 'new-game':
        o = _opts(a[1:]); f = lambda k, d=None: o.get(k, [d])[0]
        print(new_game(f('--date'), f('--home'), f('--away'), f('--sport', 'soccer'), o.get('--source', []),
                       f('--home-team'), f('--away-team'), f('--home-kit', 'home'), f('--away-kit', 'away'),
                       f('--event')))
    elif cmd == 'new-target':
        o = _opts(a[2:]); f = lambda k, d=None: o.get(k, [d])[0]
        print(new_target(a[1], f('--kind', 'player'), f('--team', 'home'), f('--player')))
    elif cmd == 'new-deliv':
        o = _opts(a[2:]); f = lambda k, d=None: o.get(k, [d])[0]
        asp = f('--aspects')
        print(new_deliv(a[1], f('--target'), f('--type', 'social_reel'), asp.split(',') if asp else None,
                        f('--finish', 'ffmpeg'), f('--client'), f('--brand')))
    elif cmd == 'new-session':
        print(new_session(a[1]))
    elif cmd == 'session' and len(a) > 1 and a[1] in ('add-game', 'add-deliv'):
        if a[1] == 'add-game':
            session_add_game(a[2] if len(a) > 2 else None)
        else:
            session_add_deliv(a[2], a[3], a[4] if len(a) > 4 else 5)
    elif cmd == 'use':
        kind, name = a[1], a[2]
        if kind in ('game', 'session'):
            reg = _read(REGISTRY, {}).get(kind + 's', {})
            hit = name if os.path.isdir(name) else next((v for k, v in reg.items() if name.lower() in k.lower()), None)
            if not hit:
                sys.exit(f'no {kind} matching {name!r}; known: {list(reg)}')
            _set_current(**{kind: hit}, **({'target': None, 'deliv': None} if kind == 'game' else {}))
            print(hit)
        elif kind == 'target':
            _set_current(target=name); print(target_dir(name))
        elif kind == 'deliv':
            d = _read(os.path.join(deliv_dir(name), 'deliv.json'), {})
            _set_current(deliv=name, target=d.get('target')); print(deliv_dir(name))
    elif cmd == 'list':
        reg = _read(REGISTRY, {})
        for kind in ([a[1]] if len(a) > 1 else ['sessions', 'games']):
            print(kind + ':')
            for k, v in reg.get(kind, {}).items():
                print('  ', k, '' if os.path.isdir(v) else '(missing — drive unmounted?)')
    elif cmd == 'status':
        status()
    elif cmd == 'next':
        u = next_unit()
        if u:
            _use_unit(u)
        print(json.dumps(u))
    elif cmd == 'clean':
        rest = [x for x in a[1:] if x != '--force']
        clean(rest[0] if rest else None, '--force' in a)
    else:
        scope, sid = 'game', None
        if cmd.split(':')[0] in FILES:
            scope, _, sid = cmd.partition(':'); sid = sid or None; a = a[1:]; cmd = a[0] if a else ''
        if cmd == 'get':
            print(json.dumps(get(a[1] if len(a) > 1 else '', scope=scope, sid=sid), indent=2))
        elif cmd == 'set':
            set_(a[1], _val(a[2]), scope=scope, sid=sid)
        elif cmd == 'merge':
            set_(a[1], json.load(open(a[2])), merge=True, scope=scope, sid=sid)
        elif cmd == 'done':
            done(scope, a[1], ' '.join(a[2:]), sid)
        elif cmd == 'reset':
            reset(scope, a[1], sid)
        elif cmd == 'path':
            d = _scope_dir(scope, sid)
            if len(a) > 1:
                d = os.path.join(d, a[1]); os.makedirs(d, exist_ok=True)
            print(d)
        else:
            sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
