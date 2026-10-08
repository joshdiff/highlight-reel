"""Team-colour player blobs + ball candidates (OpenCV). The ONE place jersey colour is defined:
the range comes from reel.json calibration.team_hsv (default: light-blue shirts on Canon Log 3).

Usage: python3 detect.py IMG...   prints the biggest blobs per image."""
import os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

SKY = 0.15  # default share of the frame top to ignore (sky / stands); sport packs set surface.top_ignore


def _surface():
    try:
        import sports
        return sports.surface()
    except Exception:
        return {}


def team_mask(bgr, rng=None):
    lo, hi = rng or hrstate.team_hsv()
    m = cv2.inRange(cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV), np.array(lo), np.array(hi))
    m[:int(m.shape[0] * _surface().get('top_ignore', SKY))] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))


def team_blobs(bgr, rng=None, min_area=40):
    """Blobs sorted by area: x0,y0,x1,y1,w,h,cx,cy,area (pixels of the given image)."""
    m = team_mask(bgr, rng); H = m.shape[0]
    n, _, st, cen = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, w, h, a = (int(v) for v in st[i])
        if a < min_area or w > h * 3 or h > H * 0.7:
            continue
        out.append(dict(x0=x, y0=y, x1=x + w, y1=y + h, w=w, h=h, area=a,
                        cx=float(cen[i][0]), cy=float(cen[i][1])))
    return sorted(out, key=lambda b: -b['area'])


def ball_cands(bgr):
    """Noisy small-round-blob candidates — hints only. Size/saturation limits and the ground-ring hue
    come from the sport pack (soccer: white ball ringed by grass; indoor courts: no ring test)."""
    sf = _surface(); bl = sf.get('ball', {}); gh = sf.get('ground_hue', [30, 90]) if sf else [30, 90]
    lo_a, hi_a, max_sat = bl.get('min_area', 6), bl.get('max_area', 220), bl.get('max_sat', 90)
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY); hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    th = cv2.morphologyEx(g, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    _, m = cv2.threshold(th, 22, 255, cv2.THRESH_BINARY); m[:int(m.shape[0] * sf.get('top_ignore', 0.18))] = 0
    n, _, st, cen = cv2.connectedComponentsWithStats(m); out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if not (lo_a <= a <= hi_a) or max(w, h) > 2.2 * min(w, h):
            continue
        circ = a / (np.pi * (max(w, h) / 2) ** 2 + 1e-6)
        if circ < 0.45 or hsv[y:y + h, x:x + w, 1].mean() > max_sat:
            continue
        if gh:
            r = max(w, h); ring = hsv[max(0, y - r):y + h + r, max(0, x - r):x + w + r]
            if ((ring[..., 0] > gh[0]) & (ring[..., 0] < gh[1])).mean() < 0.35:
                continue
        out.append(dict(x=float(cen[i][0]), y=float(cen[i][1]), r=max(w, h) / 2))
    return out


if __name__ == '__main__':
    for p in sys.argv[1:]:
        b = team_blobs(cv2.imread(p)); print(p, len(b))
        for x in b[:10]:
            print('  ', x)
