"""Team-colour player blobs + ball candidates (OpenCV). The ONE place jersey colour is defined:
the range comes from reel.json calibration.team_hsv (default: light-blue shirts on Canon Log 3).

Usage: python3 detect.py IMG...   prints the biggest blobs per image."""
import os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

SKY = 0.15  # ignore the top of frame (sky / far stands)


def team_mask(bgr, rng=None):
    lo, hi = rng or hrstate.team_hsv()
    m = cv2.inRange(cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV), np.array(lo), np.array(hi))
    m[:int(m.shape[0] * SKY)] = 0
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
    """Noisy small-white-round-on-grass candidates — hints only."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY); hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    th = cv2.morphologyEx(g, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    _, m = cv2.threshold(th, 22, 255, cv2.THRESH_BINARY); m[:int(m.shape[0] * 0.18)] = 0
    n, _, st, cen = cv2.connectedComponentsWithStats(m); out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if not (6 <= a <= 220) or max(w, h) > 2.2 * min(w, h):
            continue
        circ = a / (np.pi * (max(w, h) / 2) ** 2 + 1e-6)
        if circ < 0.45:
            continue
        r = max(w, h); ring = hsv[max(0, y - r):y + h + r, max(0, x - r):x + w + r]
        if ((ring[..., 0] > 30) & (ring[..., 0] < 90)).mean() < 0.35 or hsv[y:y + h, x:x + w, 1].mean() > 90:
            continue
        out.append(dict(x=float(cen[i][0]), y=float(cen[i][1]), r=r / 2))
    return out


if __name__ == '__main__':
    for p in sys.argv[1:]:
        b = team_blobs(cv2.imread(p)); print(p, len(b))
        for x in b[:10]:
            print('  ', x)
