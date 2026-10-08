"""Migrate local data from v0.3 to v1: profiles move into $HR_HOME/library/ (players become folders with
refs/), old workspace pointers are dropped. Safe to re-run; makes a backup first.

Usage: python3 migrate.py"""
import json, os, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate, hrprofile

H = hrstate.HOME
bk = os.path.join(H, f'backup-v03-{time.strftime("%Y%m%d-%H%M%S")}')
moved = []
os.makedirs(hrstate.LIB, exist_ok=True)
for kind in ('players', 'teams', 'cameras'):
    old = os.path.join(H, kind)
    if not os.path.isdir(old):
        continue
    shutil.copytree(old, os.path.join(bk, kind))
    for f in sorted(os.listdir(old)):
        if not f.endswith('.json'):
            continue
        d = json.load(open(os.path.join(old, f))); pid = f[:-5]
        if kind == 'players':
            p = json.loads(json.dumps(hrprofile.PLAYER_TEMPLATE)); hrstate._deep_merge(p, d)
            for g in p.get('games', []):            # v0.3 games had no 'game' key
                g.setdefault('game', f"{g.get('date')} {g.get('event')}")
            hrprofile.save('player', pid, p); hrprofile.refs_dir(pid)
        elif kind == 'teams':
            d.setdefault('sport', None); d.setdefault('client_id', None)
            hrprofile.save('team', pid, d)
        else:
            os.makedirs(os.path.join(hrstate.LIB, 'cameras'), exist_ok=True)
            hrstate._write(os.path.join(hrstate.LIB, 'cameras', f), d)
        moved.append(f'{kind}/{pid}')
    shutil.rmtree(old)
for f in ('current', 'registry.json'):
    p = os.path.join(H, f)
    if os.path.exists(p) and not (f == 'registry.json' and 'games' in hrstate._read(p, {})):
        os.makedirs(bk, exist_ok=True); shutil.move(p, os.path.join(bk, f))
print('migrated:', moved or 'nothing to migrate', '| backup:', bk if os.path.isdir(bk) else '-')
