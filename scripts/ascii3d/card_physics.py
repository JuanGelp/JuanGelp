"""
Wide Panoramic Physics Banner — `assets/card-physics.svg` [960x380].

Renders the full-detail `ascii.rest/earthrise` 200x92 scene (cratered lunar
horizon in long low sunlight, highland massifs, foreground crater & boulders,
twinkling starfield, and the rotating 3D Earth rising above the horizon) mapped
into the Jπ cosmic palette (#2e0d44, #4a1f6b, #6c389c, #a86bf0, #eee8f6, #e5b75f).
"""
from __future__ import annotations

import json
import numpy as np

from core import (BG0, BOX0, EDGE0, EDGE1, DARK, MID, BRIGHT, GOLD,
                  FONT, clean_cls, esc, fmt, frame_toggle)

W, H = 960, 380
N, DUR = 10, 1.2

PAL_MAP = {
    0: 0,
    1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4, 9: 5, 10: 5, 11: 5, 12: 6,
    13: 1, 14: 2, 15: 3, 16: 4, 17: 6,
    18: 2, 19: 2, 20: 3, 21: 3, 22: 4, 23: 4, 24: 5, 25: 5,
    26: 5, 27: 5, 28: 4,
    29: 4, 30: 4, 31: 6, 32: 6, 33: 6, 34: 6, 35: 6, 36: 4, 37: 6, 38: 6,
}

CLS_ATTR = {1: "p1", 2: "p2", 3: "a", 4: "", 5: "c", 6: "d"}


def encode_rows(chars, cls, ox, oy, cw, ch_h, mask=None, gap=14):
    rows, _ = chars.shape
    nonempty = (chars != " ") & (cls > 0)
    on = nonempty if mask is None else (nonempty & mask)
    out = []
    base = 0.82 * ch_h
    for r in range(rows):
        if not on[r].any():
            continue
        yv = fmt(oy + r * ch_h + base)
        spans = []
        for k in (1, 2, 3, 4, 5, 6):
            cs = np.nonzero(on[r] & (cls[r] == k))[0]
            if cs.size == 0:
                continue
            i = 0
            while i < cs.size:
                j = i
                while j + 1 < cs.size and cs[j + 1] - cs[j] <= gap:
                    j += 1
                c0, c1 = int(cs[i]), int(cs[j])
                txt = "".join(
                    chars[r, c] if (on[r, c] and int(cls[r, c]) == k) else " "
                    for c in range(c0, c1 + 1)
                )
                cname = CLS_ATTR[k]
                cattr = f' class="{cname}"' if cname else ""
                spans.append(f'<tspan{cattr} x="{fmt(ox + c0 * cw)}">{esc(txt)}</tspan>')
                i = j + 1
        out.append(f'<text y="{yv}">{"".join(spans)}</text>')
    return "".join(out)


def build():
    data = json.load(open("/tmp/er_frames.json"))
    raw_frames = data["frames"][:N]
    r_start, r_end = 4, 96
    cols = 200
    ox, oy = 20.0, 48.0
    cw, ch_h = 4.6, 3.35
    fs = 6.2

    frames = []
    for f in raw_frames:
        lines = f["txt"].split("\n")[r_start:r_end]
        col_arr = np.array(f["col"], dtype=np.int16).reshape(100, 200)[r_start:r_end]
        c_grid = np.array([list(line.ljust(cols)[:cols]) for line in lines], dtype="<U1")
        k_grid = np.vectorize(lambda v: PAL_MAP.get(int(v), 0))(col_arr).astype(np.int8)
        k_grid = np.where(c_grid == " ", 0, k_grid)
        k_grid = clean_cls(k_grid, c_grid)
        frames.append((c_grid, k_grid))

    c0, k0 = frames[0]
    rows = r_end - r_start
    rr, cc = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
    # Animate the sunlit rotating hemisphere of the Earth + twinkling stars
    in_earth_day = ((cc - 143) ** 2 + (rr - 28) ** 2 < 16.5 ** 2) & (cc >= 136)
    in_twinkle = (rr < 30) & (cc < 118) & (k0 >= 5)
    dyn_zone = in_earth_day | in_twinkle

    for i in range(1, N):
        ci, ki = frames[i]
        ci[~dyn_zone] = c0[~dyn_zone]
        ki[~dyn_zone] = k0[~dyn_zone]
        same_k = ((ki == k0) | ((ki <= 3) & (k0 <= 3))) & in_earth_day
        ci[same_k] = c0[same_k]
        ki[same_k] = k0[same_k]

    C = np.stack([f[0] for f in frames])
    K = np.stack([f[1] for f in frames])
    same = np.all(C == C[0], axis=0) & np.all(K == K[0], axis=0)

    static_svg = encode_rows(C[0], K[0], ox, oy, cw, ch_h, mask=same, gap=14)
    anim_parts = []
    for i in range(N):
        body = encode_rows(C[i], K[i], ox, oy, cw, ch_h, mask=~same, gap=10)
        disp = "" if i == 0 else ' display="none"'
        anim_parts.append(f"<g{disp}>{frame_toggle(i, N, DUR)}{body}</g>")

    extra_css = (
        f"text{{font-family:{FONT};white-space:pre}}"
        f".p1{{fill:{EDGE0}}}.p2{{fill:{EDGE1}}}.a{{fill:{DARK}}}.b{{fill:{MID}}}.c{{fill:{BRIGHT}}}"
        f".d{{fill:{GOLD};font-weight:700}}"
    )
    body = (
        chrome_back()
        + f'<g font-size="{fs}" fill="{MID}">{static_svg}{"".join(anim_parts)}</g>'
        + chrome_front()
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%" '
        f'role="img" aria-label="Física UNLP — Earthrise Lunar Horizon"><style>{extra_css}</style>{body}</svg>'
    )
    return svg, frames


def chrome_back():
    return (
        f'<rect width="{W}" height="{H}" rx="10" fill="{BG0}" stroke="{EDGE1}" stroke-width="1.5"/>'
        f'<rect x="12" y="10" width="{W - 24}" height="28" rx="5" fill="{BOX0}" stroke="{EDGE1}"/>'
        f'<text x="24" y="28" font-size="11" fill="{GOLD}" font-weight="700">'
        f'🪐 LICENCIATURA EN FÍSICA UNLP (2023–ACT.) // EARTHRISE · HORIZONTE LUNAR</text>'
        f'<text x="{W - 24}" y="28" text-anchor="end" font-size="10" fill="{MID}">'
        f'[LaTeX PAPERS • CLASES DE CONSULTA]</text>'
        f'<rect x="12" y="42" width="{W - 24}" height="{H - 52}" rx="6" fill="#07010e" stroke="{EDGE0}"/>'
    )


def chrome_front():
    return (
        f'<rect x="12" y="42" width="{W - 24}" height="{H - 52}" rx="6" fill="none" stroke="{EDGE1}" stroke-opacity="0.7"/>'
    )
