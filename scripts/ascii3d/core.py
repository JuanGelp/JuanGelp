"""
Jπ Studio — ASCII 3D SVG engine (core).

Optimised for GitHub Camo (<85 KB per SVG, zero <script>/<filter>/<foreignObject>):
  1. Static background layer rendered once for cells that stay constant across the loop.
  2. Per-frame delta layers containing only the cells that actually change in frame i.
  3. Contiguous same-colour runs merged across static same-colour neighbours and small
     empty gaps (saving ~33 bytes per merged tspan with identical visual output).
  4. Default fill `#a86bf0` (c-mid) on the root group so mid-tone tspans omit `class="b"`.
"""
from __future__ import annotations

import numpy as np

# ── Strict Design System Palette ─────────────────────────────────────────────
BG0, BG1 = "#0d0218", "#110320"
BOX0, BOX1 = "#160529", "#1f0830"
EDGE0, EDGE1 = "#2e0d44", "#4a1f6b"
DARK, MID, BRIGHT, GOLD = "#6c389c", "#a86bf0", "#eee8f6", "#e5b75f"

CLS = {1: "a", 2: "", 3: "c", 4: "d"}  # class 2 (MID) is inherited from parent <g>

FONT = "'JetBrains Mono','Fira Code','DejaVu Sans Mono',Consolas,'Courier New',monospace"
CSS = (
    f"text{{font-family:{FONT};white-space:pre}}"
    f".a{{fill:{DARK}}}.b{{fill:{MID}}}.c{{fill:{BRIGHT}}}"
    f".d{{fill:{GOLD};font-weight:700}}"
    f".e{{fill:{EDGE1}}}"
)

RAMP = " .,:;i!lI+~=*#MW&8%B@$"


def fmt(v: float) -> str:
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ramp_char(L, ramp: str = RAMP):
    L = np.clip(L, 0.0, 1.0)
    idx = np.rint(L * (len(ramp) - 1)).astype(int)
    return np.array(list(ramp))[idx]


def lum_cls(L, t=(0.20, 0.46, 0.74)):
    return np.where(L < t[0], 1, np.where(L < t[1], 2, np.where(L < t[2], 3, 4))).astype(np.int8)


def clean_cls(cls, chars):
    """Remove isolated 1-cell colour speckles inside a row so shading reads cleanly and compacts well."""
    out = cls.copy()
    rows, cols = cls.shape
    for r in range(rows):
        for c in range(1, cols - 1):
            if chars[r, c] != " " and out[r, c - 1] == out[r, c + 1] and out[r, c - 1] > 0:
                out[r, c] = out[r, c - 1]
    return out


class Grid:
    def __init__(self, cols, rows, ox, oy, cw, ch, fs=None):
        self.cols, self.rows = cols, rows
        self.ox, self.oy, self.cw, self.ch = ox, oy, cw, ch
        self.fs = fs if fs is not None else round(cw / 0.6, 2)
        self.base = 0.8 * ch

    def blank(self):
        return np.full((self.rows, self.cols), " ", dtype="<U1"), np.zeros((self.rows, self.cols), np.int8)

    def cx(self, col):
        return self.ox + col * self.cw

    def cy(self, row):
        return self.oy + row * self.ch + self.base

    def samples(self, sx=2, sy=2):
        xs = (np.arange(self.cols * sx) + 0.5) / sx * self.cw + self.ox
        ys = (np.arange(self.rows * sy) + 0.5) / sy * self.ch + self.oy
        return np.meshgrid(xs, ys)

    @staticmethod
    def pool(a, sx, sy, how="mean"):
        h, w = a.shape
        a = a.reshape(h // sy, sy, w // sx, sx)
        return a.mean(axis=(1, 3)) if how == "mean" else a.max(axis=(1, 3))


def encode_cells(grid: Grid, chars, cls, mask=None, gap=5):
    """Group each row into contiguous same-class runs."""
    rows, _ = chars.shape
    nonempty = (chars != " ") & (cls > 0)
    on = nonempty if mask is None else (nonempty & mask)
    out = []
    for r in range(rows):
        cs = np.nonzero(on[r])[0]
        if cs.size == 0:
            continue
        yv = fmt(grid.cy(r))
        spans = []
        i = 0
        while i < cs.size:
            k = int(cls[r, cs[i]])
            j = i
            while j + 1 < cs.size and int(cls[r, cs[j + 1]]) == k and cs[j + 1] - cs[j] <= gap + 1:
                if all((not nonempty[r, c]) or int(cls[r, c]) == k for c in range(cs[j] + 1, cs[j + 1])):
                    j += 1
                else:
                    break
            c0, c1 = int(cs[i]), int(cs[j])
            txt = "".join(
                chars[r, c] if (nonempty[r, c] and int(cls[r, c]) == k) else " "
                for c in range(c0, c1 + 1)
            )
            cattr = f' class="{CLS[k]}"' if CLS[k] else ""
            spans.append(f'<tspan{cattr} x="{fmt(grid.cx(c0))}">{esc(txt)}</tspan>')
            i = j + 1
        out.append(f'<text y="{yv}">{"".join(spans)}</text>')
    if not out:
        return ""
    return "".join(out)


def frame_toggle(i: int, n: int, dur: float) -> str:
    a, b = i / n, (i + 1) / n
    if n == 1:
        return ""
    if i == 0:
        vals, kt = "inline;none", f"0;{b:.3f}"
    elif i == n - 1:
        vals, kt = "none;inline", f"0;{a:.3f}"
    else:
        vals, kt = "none;inline;none", f"0;{a:.3f};{b:.3f}"
    return (f'<animate attributeName="display" values="{vals}" keyTimes="{kt}" '
            f'dur="{dur}s" calcMode="discrete" repeatCount="indefinite"/>')


def animated_layers(grid: Grid, frames, dur: float, gap=5):
    frames = [(c, clean_cls(k, c)) for c, k in frames]
    C = np.stack([f[0] for f in frames])
    K = np.stack([f[1] for f in frames])
    same = np.all(C == C[0], axis=0) & np.all(K == K[0], axis=0)
    static = encode_cells(grid, C[0], K[0], mask=same, gap=gap)
    n = len(frames)
    parts = []
    for i in range(n):
        body = encode_cells(grid, C[i], K[i], mask=~same, gap=gap)
        disp = "" if i == 0 else ' display="none"'
        parts.append(f"<g{disp}>{frame_toggle(i, n, dur)}{body}</g>")
    fs = fmt(grid.fs)
    return f'<g font-size="{fs}" fill="{MID}">{static}{"".join(parts)}</g>', ""


def svg_doc(w, h, body, title, extra_css=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="100%" '
        f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
        f"<style>{CSS}{extra_css}</style>{body}</svg>"
    )


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def hash2(x, y, s=0):
    x = np.asarray(x, dtype=np.int64)
    y = np.asarray(y, dtype=np.int64)
    h = (x * 374761393 + y * 668265263 + s * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFFFF) / 4294967296.0


def vnoise(x, y, period=None, s=0):
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - xi, y - yi
    u, v = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    x0, x1 = xi, xi + 1
    if period:
        x0, x1 = np.mod(x0, period), np.mod(xi + 1, period)
    a, b = hash2(x0, yi, s), hash2(x1, yi, s)
    c, d = hash2(x0, yi + 1, s), hash2(x1, yi + 1, s)
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v


def fbm(x, y, octaves=4, period=None, s=0):
    tot, norm, amp, f = 0.0, 0.0, 0.5, 1
    for o in range(octaves):
        tot = tot + amp * vnoise(x * f, y * f, period * f if period else None, s + o * 17)
        norm += amp
        amp *= 0.5
        f *= 2
    return tot / norm
