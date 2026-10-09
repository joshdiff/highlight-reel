"""Camera encoding → Rec.709 display LUTs, generated from the published curves and gamuts (no downloads).
Used by finish.py (ffmpeg path) when the camera profile has no official `lut`. An official manufacturer
LUT set on the camera profile always wins.

Pipeline per encoding: code value → scene-linear (18% grey = 0.18) → gamut → Rec.709 (linear, D65)
→ exposure → filmic tone curve (ACES fit) → BT.1886 encode (1/2.4). HLG and PQ are scaled so diffuse
white (75% HLG / 203 nits PQ) lands at 0.9.

Curves/primaries: Canon Log 3 v1.2 + Cinema Gamut, Sony S-Log3 + S-Gamut3.Cine, Panasonic V-Log + V-Gamut,
Apple Log (Rec.2020), BT.2100 HLG and PQ (Rec.2020) — constants as published (cross-checked with the
colour-science library).

Usage: python3 luts.py ENCODING [--exposure 1.0] [--out FILE.cube]   prints the cached .cube path
       python3 luts.py --list"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

N = 33
D65 = (0.3127, 0.3290)
PRIM = {
    'rec709': ((0.640, 0.330), (0.300, 0.600), (0.150, 0.060)),
    'rec2020': ((0.708, 0.292), (0.170, 0.797), (0.131, 0.046)),
    'cinema_gamut': ((0.740, 0.270), (0.170, 1.140), (0.080, -0.100)),
    's_gamut3_cine': ((0.766, 0.275), (0.225, 0.800), (0.089, -0.087)),
    'v_gamut': ((0.730, 0.280), (0.165, 0.840), (0.100, -0.030)),
}


def rgb_to_xyz(prim, white=D65):
    xyz = lambda x, y: np.array([x / y, 1.0, (1 - x - y) / y])
    P = np.stack([xyz(*p) for p in prim], axis=1)
    S = np.linalg.solve(P, xyz(*white))
    return P * S


def gamut_matrix(src):
    return np.linalg.inv(rgb_to_xyz(PRIM['rec709'])) @ rgb_to_xyz(PRIM[src])


# ---- decoding: normalised code value (0-1) → scene-linear reflection (0.18 = grey) ----
def clog3(x):
    y = np.select([x < 0.097465473, x <= 0.15277891],
                  [-(10 ** ((0.12783901 - x) / 0.36726845) - 1) / 14.98325, (x - 0.12512219) / 1.9754798],
                  (10 ** ((x - 0.12240537) / 0.36726845) - 1) / 14.98325)
    return y * 0.9


def slog3(x):
    return np.where(x >= 171.2102946929 / 1023, (10 ** ((x * 1023 - 420) / 261.5)) * 0.19 - 0.01,
                    (x * 1023 - 95) * 0.01125 / (171.2102946929 - 95))


def vlog(x):
    return np.where(x < 0.181, (x - 0.125) / 5.6, 10 ** ((x - 0.598206) / 0.241514) - 0.00873)


def apple_log(p):
    R0, Rt, sig, beta, gam, dlt = -0.05641088, 0.01, 47.28711236, 0.00964052, 0.08550479, 0.69336945
    Pt = sig * (Rt - R0) ** 2
    return np.select([p >= Pt, p >= 0], [2 ** ((p - dlt) / gam) - beta, np.sqrt(np.clip(p, 0, None) / sig) + R0], R0)


def hlg(e):
    a, b = 0.17883277, 0.28466892; c = 0.5 - a * np.log(4 * a)
    lin = np.where(e <= 0.5, e ** 2 / 3, (np.exp((e - c) / a) + b) / 12)
    white = (np.exp((0.75 - c) / a) + b) / 12          # 75% HLG = diffuse white
    return lin * 0.9 / white


def pq(e):
    m1, m2, c1, c2, c3 = 0.1593017578125, 78.84375, 0.8359375, 18.8515625, 18.6875
    ep = np.clip(e, 0, 1) ** (1 / m2)
    nits = 10000 * (np.clip(ep - c1, 0, None) / (c2 - c3 * ep)) ** (1 / m1)
    return nits / 203 * 0.9                            # 203 nits = diffuse white (BT.2408)


ENC = {   # encoding → (decode, source gamut)
    'canon_clog3': (clog3, 'cinema_gamut'),
    'sony_slog3': (slog3, 's_gamut3_cine'),
    'panasonic_vlog': (vlog, 'v_gamut'),
    'apple_log': (apple_log, 'rec2020'),
    'rec2100_hlg': (hlg, 'rec2020'),
    'rec2100_pq': (pq, 'rec2020'),
}


def aces_fit(x):
    """Narkowicz ACES filmic fit (input pre-scaled by 0.6): soft shoulder, keeps highlights from clipping."""
    x = x * 0.6
    return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)


def build(enc, exposure=1.0, gains=(1.0, 1.0, 1.0)):
    dec, gam = ENC[enc]
    g = np.linspace(0, 1, N)
    b, gg, r = np.meshgrid(g, g, g, indexing='ij')        # .cube order: red fastest
    rgb = np.stack([r, gg, b], axis=-1).reshape(-1, 3)
    lin = np.einsum('ij,nj->ni', gamut_matrix(gam), dec(rgb))
    out = aces_fit(np.clip(lin * exposure * np.asarray(gains), 0, None)) ** (1 / 2.4)   # look.py: stops + WB
    return out


def cube_path(enc, exposure=1.0, out=None, gains=(1.0, 1.0, 1.0)):
    if enc not in ENC:
        sys.exit(f'luts: no built-in transform for {enc!r} (have {list(ENC)}); set an official LUT on the camera profile')
    tag = '' if tuple(gains) == (1.0, 1.0, 1.0) else '_g' + '-'.join(f'{g:.3f}' for g in gains)
    out = out or os.path.join(hrstate.root(), 'tmp', 'luts', f'{enc}_x{exposure:.4g}{tag}.cube')   # scratch
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        data = build(enc, exposure, gains)
        with open(out, 'w') as f:
            f.write(f'TITLE "{enc} to Rec.709 (highlight-reel built-in)"\nLUT_3D_SIZE {N}\n')
            f.writelines(f'{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n' for v in data)
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] == '--list':
        print('built-in transforms:', ', '.join(ENC)); sys.exit()
    exp = float(a[a.index('--exposure') + 1]) if '--exposure' in a else 1.0
    print(cube_path(a[0], exp, a[a.index('--out') + 1] if '--out' in a else None))
