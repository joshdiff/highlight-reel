"""Player and team profiles — what we know about who we're filming, kept across games.

Stored locally (never in the repo): $HR_HOME/players/<id>.json and $HR_HOME/teams/<id>.json
(HR_HOME defaults to ~/.hr_work). Schemas: see examples/ in the repo.

CLI (python3 hrprofile.py ...):
  list [players|teams]                 all profiles, one line each
  show player|team ID                  full JSON
  new player ID --name "Full Name" [--team TEAM_ID --number N] [--grad YEAR]
  new team ID --name "Team Name" [--folder "media folder name"] [--color "light blue"]
  set player|team ID KEY VALUE         dotted key; VALUE parsed as JSON, else a string
  merge player|team ID FILE.json       deep-merge a JSON file
  note player|team ID "text"           append a dated lesson to notes[]
  brief PLAYER_ID [TEAM_ID]            the ID brief hr-find works from (number on that team, kit, look, decoys)
  rm player|team ID                    delete a profile
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

KINDS = {'player': 'players', 'team': 'teams'}


def _dir(kind):
    d = os.path.join(hrstate.HOME, KINDS[kind]); os.makedirs(d, exist_ok=True); return d


def _path(kind, pid):
    return os.path.join(_dir(kind), f'{pid}.json')


def load(kind, pid):
    p = _path(kind, pid)
    if not os.path.exists(p):
        sys.exit(f'hrprofile: no {kind} profile {pid!r} — `hrprofile.py list {KINDS[kind]}`')
    return json.load(open(p))


def save(kind, pid, data):
    data['id'] = pid; data['updated'] = time.strftime('%Y-%m-%d')
    hrstate._write(_path(kind, pid), data)


def all_(kind):
    return {f[:-5]: json.load(open(os.path.join(_dir(kind), f)))
            for f in sorted(os.listdir(_dir(kind))) if f.endswith('.json')}


def new_player(pid, name, team=None, number=None, grad=None):
    p = {'name': name, 'grad_year': grad, 'nickname': None,
         'lower_third': {'line1': name, 'line2': None},
         'appearance': {'hair': None, 'build': None, 'boots': None, 'accessories': [], 'other': []},
         'teams': [], 'decoys': [], 'notes': [], 'games': []}
    if team:
        p['teams'].append({'team_id': team, 'number': number, 'position': None, 'seasons': [], 'active': True})
    save('player', pid, p); return p


def new_team(pid, name, folder=None, color=None):
    t = {'name': name, 'media_folder': folder or name, 'club': None, 'age_group': None,
         'kits': {'home': {'shirt': color, 'shorts': None, 'socks': None, 'hsv': {}}},
         'roster': {}, 'opponents': {}, 'notes': []}
    save('team', pid, t); return t


def kit_hsv(team_id, kit='home', encoding='canon_clog3'):
    """Calibrated jersey range for this kit on footage of this encoding (kits.<kit>.hsv.<encoding>)."""
    p = _path('team', team_id)
    if not os.path.exists(p):
        return None
    return ((json.load(open(p)).get('kits', {}).get(kit) or {}).get('hsv') or {}).get(encoding)


def membership(player, team_id=None):
    ts = player.get('teams', [])
    if team_id:
        ts = [t for t in ts if t['team_id'] == team_id] or ts
    act = [t for t in ts if t.get('active')]
    return (act or ts or [None])[0]


def brief(pid, team_id=None):
    p = load('player', pid); m = membership(p, team_id) or {}
    t = load('team', m['team_id']) if m.get('team_id') and os.path.exists(_path('team', m['team_id'])) else {}
    kit = t.get('kits', {}).get('home', {})
    a = p.get('appearance', {})
    look = '; '.join(str(v) if not isinstance(v, list) else ', '.join(v)
                     for v in a.values() if v)
    lines = [f"{p['name']} — #{m.get('number', '?')} for {t.get('name', m.get('team_id', '?'))}"
             + (f", {m['position']}" if m.get('position') else ''),
             f"  kit: {kit.get('shirt') or '?'} shirt" + (f", {kit['shorts']} shorts" if kit.get('shorts') else '')
             + (f", {kit['socks']} socks" if kit.get('socks') else ''),
             f"  look: {look or '(none recorded — identify by number alone, then record what you see)'}",
             f"  decoys: {'; '.join(p.get('decoys', [])) or 'none recorded'}"]
    if t.get('roster'):
        lines.append('  team numbers seen: ' + ', '.join(f'#{k} {v}' for k, v in t['roster'].items()))
    for n in p.get('notes', [])[-5:]:
        lines.append(f"  note {n['date']}: {n['text']}")
    return '\n'.join(lines)


def _set(d, key, value, merge=False):
    cur = d; ks = key.split('.')
    for k in ks[:-1]:
        cur = cur.setdefault(k, {})
    if merge and isinstance(value, dict) and isinstance(cur.get(ks[-1]), dict):
        hrstate._deep_merge(cur[ks[-1]], value)
    else:
        cur[ks[-1]] = value


def main(a):
    if not a:
        print(__doc__); return
    cmd = a[0]
    if cmd == 'list':
        for kind in ([{'players': 'player', 'teams': 'team'}[a[1]]] if len(a) > 1 else ['player', 'team']):
            print(KINDS[kind] + ':')
            for pid, d in all_(kind).items():
                extra = ''
                if kind == 'player':
                    m = membership(d) or {}
                    extra = f"#{m.get('number', '?')} {m.get('team_id', '')}"
                else:
                    extra = (d.get('kits', {}).get('home') or {}).get('shirt') or ''
                print(f'  {pid:20s} {d["name"]:28s} {extra}')
    elif cmd == 'show':
        print(json.dumps(load(a[1], a[2]), indent=2))
    elif cmd == 'new':
        kind, pid = a[1], a[2]; o = dict(zip(a[3::2], a[4::2]))
        if os.path.exists(_path(kind, pid)):
            sys.exit(f'{kind} {pid} exists — use set/merge')
        if kind == 'player':
            new_player(pid, o['--name'], o.get('--team'), int(o['--number']) if o.get('--number') else None,
                       int(o['--grad']) if o.get('--grad') else None)
        else:
            new_team(pid, o['--name'], o.get('--folder'), o.get('--color'))
        print(_path(kind, pid))
    elif cmd in ('set', 'merge'):
        kind, pid, key = a[1], a[2], a[3]; d = load(kind, pid)
        if cmd == 'set':
            try:
                v = json.loads(a[4])
            except json.JSONDecodeError:
                v = a[4]
        else:
            v = json.load(open(a[4]))
        _set(d, key, v, merge=cmd == 'merge'); save(kind, pid, d)
    elif cmd == 'note':
        kind, pid = a[1], a[2]; d = load(kind, pid)
        d.setdefault('notes', []).append({'date': time.strftime('%Y-%m-%d'), 'text': ' '.join(a[3:])})
        save(kind, pid, d)
    elif cmd == 'brief':
        print(brief(a[1], a[2] if len(a) > 2 else None))
    elif cmd == 'rm':
        os.remove(_path(a[1], a[2])); print('removed', a[1], a[2])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
