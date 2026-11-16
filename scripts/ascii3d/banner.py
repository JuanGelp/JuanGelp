"""Header banner 960x340: 3D starfield, ringed gas giant, Gargantua-style black hole, Jπ HUD."""
from __future__ import annotations

import numpy as np

from core import (BG0, BG1, BOX0, EDGE0, EDGE1, DARK, MID, BRIGHT, GOLD, Grid, animated_layers,
                  esc, fmt, hash2, lum_cls, ramp_char, smoothstep, svg_doc)

W, H = 960, 340
N, DUR = 16, 1.0            # 16 frames / 1.0 s (16 FPS)
G = Grid(192, 31, 0, 0, 5.0, 8.0)   # 192x31 cells (5x8 px, font 8.33 px) over y in [0..248]
SX, SY = 2, 2
PX, PY = G.samples(SX, SY)
TAU = 2 * np.pi

# ═══════════════════════════════════ GAS GIANT ═══════════════════════════════════
P_CX, P_CY, P_R = 178, 126, 76
ROLL, ELEV = -0.28, 0.35


def ring_density(r):
    d = np.zeros_like(r)
    d = np.where((r > 1.22) & (r < 1.48), 0.30 + 0.14 * smoothstep(1.22, 1.48, r), d)        # C ring
    b = (r >= 1.48) & (r < 1.92)
    d = np.where(b, 0.88 + 0.12 * np.sin(r * 74.0) * np.sin(r * 25.0), d)                    # B ring
    d = np.where((r >= 1.92) & (r < 2.04), 0.0, d)                                            # Cassini division
    a = (r >= 2.04) & (r < 2.28)
    d = np.where(a, 0.66 + 0.08 * np.sin(r * 115.0), d)                                       # A ring
    d = np.where((r > 2.18) & (r < 2.21), 0.04, d)                                            # Encke gap
    d = np.where((r > 2.33) & (r < 2.36), 0.44, d)                                            # F ring
    return d


def planet(t):
    cr, sr, ce, se = np.cos(ROLL), np.sin(ROLL), np.cos(ELEV), np.sin(ELEV)
    X = (PX - P_CX) / P_R
    Y = -(PY - P_CY) / P_R
    Xr, Yr = X * cr + Y * sr, -X * sr + Y * cr
    Lv = np.array([-0.58, 0.40, 0.71]); Lv /= np.linalg.norm(Lv)
    lx, ly = Lv[0] * cr + Lv[1] * sr, -Lv[0] * sr + Lv[1] * cr
    Lp = np.array([lx, ly * ce + Lv[2] * se, -ly * se + Lv[2] * ce])

    rho2 = Xr ** 2 + Yr ** 2
    inside = rho2 < 1
    Z = np.sqrt(np.clip(1 - rho2, 0, 1))
    Px, Py, Pz = Xr, Yr * ce + Z * se, -Yr * se + Z * ce
    lat = np.arcsin(np.clip(Py, -1, 1))
    lon = np.arctan2(Px, Pz)
    ndl = Px * Lp[0] + Py * Lp[1] + Pz * Lp[2]
    lam = np.clip(ndl, 0, 1)

    u = (lon + np.pi) / TAU
    # Focused dynamic wave in the illuminated equatorial belt + anticyclonic vortex
    eq_belt = (np.abs(lat - 0.14) < 0.22) & (lam > 0.22)
    so_belt = (np.abs(lat + 0.24) < 0.16) & (lam > 0.22)
    wave1 = np.where(eq_belt, 0.16 * np.cos(TAU * (u * 3 - t / DUR) + lat * 7), 0.0)
    wave2 = np.where(so_belt, 0.14 * np.cos(TAU * (u * 4 + t / DUR) - lat * 6), 0.0)
    alb = 0.70 + 0.19 * np.cos(lat * 11.0 + 0.35) + 0.09 * np.cos(lat * 26 + 1.1) + wave1 + wave2
    hint = np.zeros(PX.shape, np.int8)

    # Anticyclonic vortex (Great Spot) rotating on the sunlit hemisphere
    lv, pv = -0.35, -0.32
    dl, dp = (lon - lv) * np.cos(pv) / 0.34, (lat - pv) / 0.16
    q = np.sqrt(dl ** 2 + dp ** 2)
    ang = np.arctan2(dp, dl)
    spiral = 0.5 + 0.5 * np.cos(2 * ang + 6.0 * q - TAU * t / DUR)
    vort = (q < 1) & inside
    alb = np.where(vort, 0.72 + 0.30 * spiral * (1 - 0.45 * q), alb)
    alb = np.where((q >= 0.95) & (q < 1.28) & inside, alb * 0.48, alb)
    hint = np.where(vort & (spiral > 0.42), 2, hint)

    # Ring shadow on cloud tops
    s_ = np.where(np.abs(Lp[1]) > 1e-3, -Py / Lp[1], -1)
    qx, qz = Px + s_ * Lp[0], Pz + s_ * Lp[2]
    rshadow = np.where(s_ > 0, ring_density(np.hypot(qx, qz)), 0)

    rim = (1 - Z) ** 2.6 * np.clip(ndl + 0.55, 0, 1)
    Ls = alb * (0.06 + 0.94 * lam ** 0.78) * (1 - 0.78 * rshadow) + 0.82 * rim
    hint = np.where(inside & (rim > 0.15), 2, hint)

    # Ring plane with z-buffer occlusion and planet shadow
    rx, rz = Xr, -Yr / se
    rr = np.hypot(rx, rz)
    zr = -Yr * ce / se
    dens = ring_density(rr)
    rang = np.arctan2(rz, rx)
    b_ring_front = (rr > 1.52) & (rr < 1.88) & (rz > 0)
    spokes = np.where(b_ring_front, 0.22 * np.cos(4 * rang - TAU * t / DUR), 0.0)
    bq = rx * Lp[0] + rz * Lp[2]
    disc = bq ** 2 - (rr ** 2 - 1)
    pshadow = (bq < 0) & (disc > 0)
    Lr = dens * (0.70 + 0.30 * Lp[1] + spokes) * np.where(pshadow, 0.07, 1.0)
    ring_vis = (dens > 0.02) & ~(inside & (zr < Z))

    L = np.where(inside, Ls, 0.0)
    occ = inside.copy()
    L = np.where(ring_vis, np.maximum(Lr, 0.0) * 1.12, L)
    hint = np.where(ring_vis, np.where(Lr > 0.68, 2, 3), hint)
    occ |= ring_vis | ((rr > 1.2) & (rr < 2.4) & ~inside)
    return L, hint, occ


# ═══════════════════════════════ BLACK HOLE (Schwarzschild) ═══════════════════════
B_CX, B_CY = 782, 124
D_CAM, INC, ROLLB = 34.0, 0.13, -0.10
R_IN, R_OUT = 2.8, 11.2
SCALE = 545.0


def _orbit_table(nb=1400, bmax=15.0, h=0.004, phimax=3.2 * np.pi):
    B = np.linspace(0.02, bmax, nb)
    u0 = 1 / D_CAM
    u = np.full(nb, u0)
    du = np.sqrt(np.clip(1 / B ** 2 - u0 ** 2 + u0 ** 3, 0, None))
    steps = int(phimax / h)
    U = np.full((steps, nb), np.nan)
    DU = np.full((steps, nb), np.nan)
    alive = np.ones(nb, bool)
    fate = np.zeros(nb, np.int8)
    for i in range(steps):
        U[i, alive], DU[i, alive] = u[alive], du[alive]
        a = alive
        u_a, du_a = u[a], du[a]
        f = lambda x: 1.5 * x * x - x
        k1u, k1v = du_a, f(u_a)
        k2u, k2v = du_a + 0.5 * h * k1v, f(u_a + 0.5 * h * k1u)
        k3u, k3v = du_a + 0.5 * h * k2v, f(u_a + 0.5 * h * k2u)
        k4u, k4v = du_a + h * k3v, f(u_a + h * k3u)
        u[a] = u_a + h / 6 * (k1u + 2 * k2u + 2 * k3u + k4u)
        du[a] = du_a + h / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
        cap = alive & (u >= 1.0)
        esc_ = alive & (u < u0 * 0.6) & (du < 0)
        fate[cap], fate[esc_] = 1, 2
        alive &= ~(cap | esc_)
        if not alive.any():
            U, DU = U[: i + 1], DU[: i + 1]
            break
    fate[alive] = 1
    return B, U, DU, fate, h


def blackhole_geometry():
    B, U, DU, fate, h = _orbit_table()
    sx = (PX - B_CX) / SCALE
    sy = -(PY - B_CY) / SCALE
    c, s = np.cos(ROLLB), np.sin(ROLLB)
    sx, sy = sx * c + sy * s, -sx * s + sy * c
    n = np.array([0.0, 1.0, 0.0])
    C = D_CAM * np.array([0.0, np.sin(INC), np.cos(INC)])
    e1 = C / D_CAM
    Rv = np.array([1.0, 0, 0])
    Uv = np.array([0.0, np.cos(INC), -np.sin(INC)])
    sm = np.hypot(sx, sy) + 1e-9
    b = D_CAM * sm / np.sqrt(1 + sm ** 2)
    e2 = (sx[..., None] * Rv + sy[..., None] * Uv) / sm[..., None]
    ib = np.clip(np.rint((b - B[0]) / (B[1] - B[0])).astype(int), 0, len(B) - 1)
    a_ = e1 @ n
    c_ = e2 @ n
    phi0 = np.mod(np.arctan2(-a_, c_), np.pi)
    nsteps = U.shape[0]
    hit = np.zeros(PX.shape, bool)
    r_hit = np.full(PX.shape, R_IN)
    psi = np.zeros(PX.shape)
    g = np.ones(PX.shape)
    order = np.zeros(PX.shape, np.int8)
    for k in range(3):
        phk = phi0 + k * np.pi
        idx = np.rint(phk / h).astype(int)
        ok = (idx < nsteps) & ~hit
        idc = np.clip(idx, 0, nsteps - 1)
        uu = U[idc, ib]
        dd = DU[idc, ib]
        ok &= np.isfinite(uu) & (uu > 0)
        usafe = np.where(ok, uu, 1.0)
        r = 1.0 / usafe
        ok &= (r >= R_IN) & (r <= R_OUT)
        if not ok.any():
            continue
        cph, sph = np.cos(phk), np.sin(phk)
        P = r[..., None] * (cph[..., None] * e1 + sph[..., None] * e2)
        ps = np.arctan2(P[..., 2], P[..., 0])
        rp = -dd / (usafe ** 2)
        tang = (rp * cph)[..., None] * e1 + (rp * sph)[..., None] * e2 \
            + (r * -sph)[..., None] * e1 + (r * cph)[..., None] * e2
        kc = -tang / (np.linalg.norm(tang, axis=-1, keepdims=True) + 1e-9)
        # Left side approaches viewer (gold Doppler boost), right side recedes (violet)
        vhat = np.stack([np.sin(ps), np.zeros_like(ps), -np.cos(ps)], -1)
        beta = np.sqrt(0.5 / np.clip(r - 1, 0.3, None)).clip(0, 0.72)
        gam = 1 / np.sqrt(1 - beta ** 2)
        cth = np.sum(vhat * kc, -1)
        dop = 1 / (gam * (1 - beta * cth))
        gg = dop * np.sqrt(np.clip(1 - 1 / np.clip(r, 1.05, None), 0, 1))
        hit = hit | ok
        r_hit = np.where(ok, r, r_hit)
        psi = np.where(ok, ps, psi)
        g = np.where(ok, gg, g)
        order = np.where(ok, k, order)
    captured = (fate[ib] == 1) & ~hit
    bc = 2.598
    photon_ring = np.exp(-((b - bc) / 0.25) ** 2) * np.where(b >= bc - 0.14, 1.0, 0.0)
    return dict(hit=hit, r=r_hit, psi=psi, g=g, order=order, captured=captured,
                photon=photon_ring, b=b)


BHG = None


def blackhole(t):
    geo = BHG
    r, ps = geo["r"], geo["psi"]
    x = (r - R_IN) / (R_OUT - R_IN)
    emis = np.where(geo["hit"], (1 - x) ** 1.25 * (0.42 + 0.58 * np.sin(np.clip(x, 0, 1) * np.pi) ** 0.4), 0.0)
    # Focused Keplerian spiral in the bright inner/mid disk (r < 7.8) so outer halo stays calm
    active = (r < 7.8) & geo["hit"]
    arms = np.where(active, 0.32 * np.cos(3 * ps - 2.4 * r + TAU * (t / DUR)), 0.0)
    beam = geo["g"] ** 2.5
    I = emis * (0.72 + arms) * beam * 1.75
    I = np.where(geo["order"] >= 1, I * 1.30 + 0.14, I)
    I = np.maximum(I, geo["photon"] * 0.98)
    in_shadow = (geo["b"] < 2.42) & ~(geo["hit"] & (geo["order"] == 0))
    I = np.where(in_shadow, 0.0, I)
    L = np.clip(I, 0, 1)
    hint = np.where(geo["hit"] & (geo["g"] > 1.04) & (L > 0.28), 2, 0).astype(np.int8)
    hint = np.where(geo["hit"] & (geo["g"] < 0.93), 4, hint)
    hint = np.where(geo["photon"] > 0.50, 2, hint)
    occ = geo["hit"] | geo["captured"] | (geo["photon"] > 0.12) | (geo["b"] < 3.2)
    return L, hint, occ


# ═══════════════════════════════════ STARFIELD ═══════════════════════════════════
S_CX, S_CY, F = 480, 126, 120
rng = np.random.default_rng(7)
TRACKS = 32
_a = rng.uniform(0, TAU, TRACKS)
_d = 0.35 + 0.65 * np.sqrt(rng.uniform(0, 1, TRACKS))
TX, TY = np.cos(_a) * _d * 2.3, np.sin(_a) * _d * 0.95
TPH = rng.uniform(0, 1, TRACKS)
STAR_STEPS = [(0.80, ".", 1), (0.52, ":", 2), (0.36, "+", 3), (0.25, "*", 3), (0.16, "#", 4), (0.0, "@", 4)]
STATIC_STARS = [(int(c), int(r)) for c, r in zip(rng.integers(0, G.cols, 150), rng.integers(0, G.rows, 150))]
STATIC_CH = rng.choice(list("..........,'`+"), len(STATIC_STARS))
TWINKLE = set(rng.choice(len(STATIC_STARS), 16, replace=False).tolist())


def star_char(z):
    for zmin, ch, k in STAR_STEPS:
        if z > zmin:
            return ch, k
    return "@", 4


def starfield(t, chars, cls, blocked):
    for i, (c, r) in enumerate(STATIC_STARS):
        if blocked[r, c]:
            continue
        if i in TWINKLE:
            ph = (t / DUR + hash2(i, 3)) % 1.0
            ch = ".:+*+:."[int(ph * 7)]
            chars[r, c], cls[r, c] = ch, (3 if ch in "+*" else 2)
        else:
            chars[r, c], cls[r, c] = STATIC_CH[i], 1
    for i in range(TRACKS):
        uph = (t / DUR + TPH[i]) % 1.0
        z = 1.22 * (1 - uph) + 0.08 * uph
        for k, dz in enumerate((0.0, 0.06)):
            zz = z + dz
            if k and z > 0.30:
                break
            x = S_CX + TX[i] / zz * F
            y = S_CY + TY[i] / zz * F
            c, r = int(x // G.cw), int(y // G.ch)
            if not (0 <= c < G.cols and 0 <= r < G.rows) or blocked[r, c]:
                continue
            if k == 0:
                ch, kk = star_char(z)
            else:
                ch, kk = ("-" if abs(TX[i]) > 2.2 * abs(TY[i]) else ":"), 2
                if chars[r, c] != " ":
                    continue
            if kk >= cls[r, c]:
                chars[r, c], cls[r, c] = ch, kk


# ═══════════════════════════════════ COMPOSITION ═════════════════════════════════
HUD = (372, 26, 588, 222)


def shade_cells(L, hint, occ, thresholds):
    Lc = G.pool(L, SX, SY)
    hint_gold = G.pool((hint == 2).astype(float), SX, SY)
    hint_ring = G.pool((hint == 3).astype(float), SX, SY)
    hint_violet = G.pool((hint == 4).astype(float), SX, SY)
    occ_c = G.pool(occ.astype(float), SX, SY) > 0.3
    ch = ramp_char(Lc ** 0.85)
    k = lum_cls(Lc, thresholds)
    k = np.where((hint_gold > 0.30) & (Lc > 0.26), 4, k)
    k = np.where((hint_ring > 0.5) & (k == 4), 3, k)
    k = np.where((hint_violet > 0.45) & (k >= 3), 2, k)
    k = np.where(ch == " ", 0, k)
    return ch, k.astype(np.int8), occ_c


def build():
    global BHG
    BHG = blackhole_geometry()
    blocked0 = np.zeros((G.rows, G.cols), bool)
    c0, r0, c1, r1 = int(HUD[0] // G.cw), int(HUD[1] // G.ch), int(HUD[2] // G.cw) + 1, int(HUD[3] // G.ch) + 1
    blocked0[r0:r1, c0:c1] = True
    frames = []
    for i in range(N):
        t = i * DUR / N
        chars, cls = G.blank()
        Lp, hp, op = planet(t)
        Lb, hb, ob = blackhole(t)
        cp, kp, oc_p = shade_cells(Lp, hp, op, (0.16, 0.38, 0.68))
        cb, kb, oc_b = shade_cells(Lb, hb, ob, (0.14, 0.32, 0.60))
        blocked = blocked0 | oc_p | oc_b
        starfield(t, chars, cls, blocked)
        for cc, kk, oc in ((cp, kp, oc_p), (cb, kb, oc_b)):
            chars = np.where(oc, cc, chars)
            cls = np.where(oc, kk, cls)
        frames.append((chars, cls))
    # Lock subtle outer-halo cells that barely fluctuate to frame 0 so delta frames stay <85 KB
    c0_ref, k0_ref = frames[0]
    ramp_idx = {ch: idx for idx, ch in enumerate(" .,:;i!lI+~=*#MW&8%B@$")}
    r0_map = np.vectorize(lambda ch: ramp_idx.get(ch, -1))(c0_ref)
    for i in range(1, N):
        ci, ki = frames[i]
        ri_map = np.vectorize(lambda ch: ramp_idx.get(ch, -1))(ci)
        minor = (r0_map >= 0) & (ri_map >= 0) & (np.abs(ri_map - r0_map) <= 4) & (ki == k0_ref)
        ci[minor] = c0_ref[minor]
    layers, _ = animated_layers(G, frames, DUR, gap=6)
    return svg_doc(W, H, chrome_back() + layers + chrome_front(),
                   "Juan // Jπ Studio — 3D ASCII cosmos banner", extra_css=EXTRA_CSS), frames


# ═════════════════════════════════ HUD / TYPOGRAPHY ══════════════════════════════
EXTRA_CSS = ".t{font-weight:700;letter-spacing:6px}.s{letter-spacing:1.6px}"

MONOGRAM_ROWS = [
    "      ██╗ ███████████╗ ",
    "      ██║ ╚═██╔════██╔╝",
    "      ██║   ██║    ██║ ",
    "██╗   ██║   ██║    ██║ ",
    "╚██████╔╝   ██║    ╚██╗",
    " ╚═════╝    ╚═╝     ╚═╝",
]


def monogram(cx, top, fs=14.0, lh=16.0):
    cw = fs * 0.6
    width = max(len(r) for r in MONOGRAM_ROWS)
    x0 = cx - width * cw / 2
    out = []
    for ri, row in enumerate(MONOGRAM_ROWS):
        y = fmt(top + ri * lh)
        spans = []
        i = 0
        while i < len(row):
            if row[i] == " ":
                i += 1
                continue
            is_blk = row[i] == "█"
            j = i
            while j < len(row) and row[j] != " " and (row[j] == "█") == is_blk:
                j += 1
            fill = "url(#glint)" if is_blk else MID
            w = ' font-weight="700"' if is_blk else ""
            spans.append(f'<tspan x="{fmt(x0 + i * cw)}" fill="{fill}"{w}>{row[i:j]}</tspan>')
            i = j
        out.append(f'<text y="{y}" font-size="{fs}">{"".join(spans)}</text>')
    return "".join(out)


def chrome_back():
    return (f'<defs><linearGradient id="glint" gradientUnits="userSpaceOnUse" x1="360" y1="0" x2="460" y2="60">'
            f'<stop offset="0" stop-color="{GOLD}"/><stop offset="0.45" stop-color="{GOLD}"/>'
            f'<stop offset="0.5" stop-color="{BRIGHT}"/><stop offset="0.55" stop-color="{GOLD}"/>'
            f'<stop offset="1" stop-color="{GOLD}"/>'
            f'<animateTransform attributeName="gradientTransform" type="translate" values="-160 0;360 0;360 0" '
            f'keyTimes="0;0.55;1" dur="3.6s" repeatCount="indefinite"/></linearGradient></defs>'
            f'<rect width="{W}" height="{H}" rx="10" fill="{BG0}"/>'
            f'<rect x="0" y="252" width="{W}" height="88" fill="{BG1}"/>'
            f'<line x1="0" y1="252" x2="{W}" y2="252" stroke="{EDGE1}" stroke-width="1"/>')


def chrome_front():
    x0, y0, x1, y1 = HUD
    cx = (x0 + x1) / 2
    br = 14
    def corner(x, y, dx, dy):
        return f'<path d="M{x} {y + dy * br}V{y}H{x + dx * br}" fill="none" stroke="{GOLD}" stroke-width="1.8"/>'
    ticks = "".join(
        f'<line x1="{x0}" y1="{y}" x2="{x0 + (6 if k % 2 else 3)}" y2="{y}" stroke="{EDGE1}"/>'
        f'<line x1="{x1}" y1="{y}" x2="{x1 - (6 if k % 2 else 3)}" y2="{y}" stroke="{EDGE1}"/>'
        for k, y in enumerate(range(y0 + 28, y1 - 24, 12)))
    hud = (f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="6" fill="{BG1}" stroke="{EDGE1}"/>'
           f'<rect x="{x0 + 6}" y="{y0 + 6}" width="{x1 - x0 - 12}" height="{y1 - y0 - 12}" rx="4" fill="{BOX0}" stroke="{EDGE0}"/>'
           + corner(x0, y0, 1, 1) + corner(x1, y0, -1, 1) + corner(x0, y1, 1, -1) + corner(x1, y1, -1, -1) + ticks +
           f'<text x="{cx}" y="{y0 + 23}" text-anchor="middle" font-size="9" class="s" fill="{MID}">[ Jπ :: CORE.SYS ]</text>'
           f'<line x1="{x0 + 20}" y1="{y0 + 32}" x2="{x1 - 20}" y2="{y0 + 32}" stroke="{EDGE1}" stroke-dasharray="2 3"/>'
           + monogram(cx, y0 + 60) +
           f'<line x1="{x0 + 20}" y1="{y1 - 36}" x2="{x1 - 20}" y2="{y1 - 36}" stroke="{EDGE1}" stroke-dasharray="2 3"/>'
           f'<text x="{cx}" y="{y1 - 19}" text-anchor="middle" font-size="8.5" class="s" fill="{BRIGHT}">'
           f'ASCII·3D ENGINE <tspan fill="{GOLD}">●</tspan> ONLINE'
           f'<animate attributeName="opacity" values="1;0.55;1" dur="2.2s" repeatCount="indefinite"/></text>')
    labels = (f'<text x="20" y="18" font-size="8.5" class="s" fill="{DARK}">OBJ-01 // RINGED GAS GIANT · CASSINI + VORTEX</text>'
              f'<text x="940" y="18" text-anchor="end" font-size="8.5" class="s" fill="{DARK}">OBJ-02 // GARGANTUA BH · GRAVITATIONAL LENS</text>')
    band = (f'<line x1="290" y1="262" x2="670" y2="262" stroke="{EDGE1}" stroke-width="1"/>'
            f'<text x="{W / 2}" y="286" text-anchor="middle" font-size="24" class="t" fill="{GOLD}">'
            f'JUAN  <tspan fill="{MID}">//</tspan>  Jπ STUDIO</text>'
            f'<text x="{W / 2}" y="307" text-anchor="middle" font-size="10.2" class="s" fill="{BRIGHT}">'
            f'FÍSICA &amp; MATEMÁTICA (UNLP) <tspan fill="{GOLD}">•</tspan> DESARROLLO WEB &amp; 3D (Jπ STUDIO) '
            f'<tspan fill="{GOLD}">•</tspan> CIENCIA DE DATOS (UNLP)</text>'
            f'<text x="{W / 2}" y="326" text-anchor="middle" font-size="9.5" class="s" fill="{MID}">'
            f'LA PLATA, ARGENTINA <tspan fill="{GOLD}">•</tspan> <tspan fill="{GOLD}" font-weight="700">SHOWROOM-JPI.PAGES.DEV</tspan></text>')
    frame = f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="10" fill="none" stroke="{EDGE1}" stroke-width="1.5"/>'
    return hud + labels + band + frame
