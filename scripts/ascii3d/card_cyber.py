"""
Wide Panoramic Data Science Banner — `assets/card-datascience.svg` (and `card-cybersec.svg`) [960x350].

Renders:
  • Left panel: Ciencia de Datos en Organizaciones UNLP (2027 - Act.) stack & tools HUD.
  • Centre panel: the full-resolution 51x28 `ascii.rest/python` dual-serpent emblem
    with diagonal `/` specular glint sweep.
  • Right panel: the 3D `ascii.rest/lorenz-attractor` chaotic trajectory looping both wings
    with a glowing golden leading head (`@`, `#`).
"""
from __future__ import annotations

import json
import numpy as np

from core import (BG0, BOX0, EDGE0, EDGE1, DARK, MID, BRIGHT, GOLD,
                  Grid, animated_layers, svg_doc)

W, H = 960, 350
N, DUR = 12, 1.2
G = Grid(154, 28, 20.0, 56.0, 6.0, 9.4, fs=9.8)

_DS = json.load(open("/tmp/ds_frames.json"))
_PY = _DS["pyFrames"]
_LZ = _DS["lzFrames"]


def render_python_emblem(frame_idx, chars, cls):
    """Place the full-resolution 51x28 `ascii.rest/python` emblem at cols 49..100."""
    f = _PY[(frame_idx + 4) % len(_PY)]
    mono_lines = f["monoTxt"].split("\n")
    col_arr = np.array(f["col"], dtype=np.int16).reshape(28, 51)
    c_off = 49
    for r in range(min(28, len(mono_lines))):
        line = mono_lines[r].ljust(51)[:51]
        for c in range(51):
            ch = line[c]
            if ch == " ":
                continue
            pal = int(col_arr[r, c])
            # In python.js dark mode (indices 9..17):
            # base ink = pal % 3 (0: top/left serpent blue, 1: bottom/right serpent gold, 2: shadow)
            # glint = (pal - 9) // 3 in {0, 1, 2}
            ink = pal % 3
            glint = max(0, (pal - 9) // 3)
            if glint >= 2 or ch == "/":
                k = 4 if ink != 1 else 3
            elif glint == 1:
                k = 3 if ink == 0 else 4
            else:
                k = 4 if ink == 1 else (2 if ink == 0 else 1)
            chars[r, c_off + c] = ch
            cls[r, c_off + c] = k


def render_lorenz_attractor(frame_idx, chars, cls):
    """Place the 3D `ascii.rest/lorenz-attractor` trajectory at cols 102..153, rows 3..25."""
    f = _LZ[frame_idx % len(_LZ)]
    lines = f["txt"].split("\n")
    r_off, c_off = 3, 101
    for r in range(min(22, len(lines))):
        line = lines[r]
        for c in range(min(52, len(line))):
            ch = line[c]
            if ch == " ":
                continue
            # Ramp in lorenz.js is " .:-=+*" and "#@" for the leading trajectory tip
            if ch in "#@":
                k = 4   # blazing golden tip (#e5b75f)
            elif ch in "+*":
                k = 3   # bright recent loop (#eee8f6)
            elif ch in "-=":
                k = 2   # mid-tone wing (#a86bf0)
            else:
                k = 1   # fading phase-space trail (#6c389c)
            chars[r_off + r, c_off + c] = ch
            cls[r_off + r, c_off + c] = k


def build():
    frames = []
    for i in range(N):
        chars, cls = G.blank()
        render_python_emblem(i, chars, cls)
        render_lorenz_attractor(i, chars, cls)
        frames.append((chars, cls))
    layers, _ = animated_layers(G, frames, DUR, gap=8)
    return svg_doc(W, H, chrome_back() + layers + chrome_front(),
                   "Ciencia de Datos en Organizaciones UNLP (2027-Act.) — Python & Lorenz Attractor"), frames


def chrome_back():
    return (
        f'<rect width="{W}" height="{H}" rx="10" fill="{BG0}" stroke="{EDGE1}" stroke-width="1.5"/>'
        f'<rect x="12" y="10" width="{W - 24}" height="28" rx="5" fill="{BOX0}" stroke="{EDGE1}"/>'
        f'<text x="24" y="28" font-size="11" fill="{GOLD}" font-weight="700">'
        f'📊 CIENCIA DE DATOS EN ORGANIZACIONES UNLP (2027–ACT.) // PYTHON &amp; SISTEMAS DINÁMICOS</text>'
        f'<text x="{W - 24}" y="28" text-anchor="end" font-size="10" fill="{MID}">'
        f'[UNLP • 2027–ACT.]</text>'
        f'<rect x="12" y="42" width="{W - 24}" height="{H - 52}" rx="6" fill="#07010e" stroke="{EDGE0}"/>'
        f'<line x1="308" y1="50" x2="308" y2="{H - 18}" stroke="{EDGE0}" stroke-dasharray="3 4"/>'
        f'<line x1="620" y1="50" x2="620" y2="{H - 18}" stroke="{EDGE0}" stroke-dasharray="3 4"/>'
    )


def chrome_front():
    left_hud = (
        f'<text x="28" y="68" font-size="10.5" fill="{GOLD}" font-weight="700">$ unlp-datasci --roadmap --tools</text>'
        f'<text x="28" y="92" font-size="10" fill="{MID}">[STACK &amp; HERRAMIENTAS DE CARRERA]</text>'
        f'<text x="28" y="112" font-size="9.8" fill="{GOLD}">├─ Python • Pandas • NumPy</text>'
        f'<text x="28" y="130" font-size="9.8" fill="{BRIGHT}">├─ SQL &amp; Bases de Datos</text>'
        f'<text x="28" y="148" font-size="9.8" fill="{BRIGHT}">├─ Jupyter / Google Colab</text>'
        f'<text x="28" y="166" font-size="9.8" fill="{BRIGHT}">├─ Estadística &amp; Probabilidad</text>'
        f'<text x="28" y="184" font-size="9.8" fill="{BRIGHT}">├─ Modelado &amp; Machine Learning</text>'
        f'<text x="28" y="202" font-size="9.8" fill="{MID}">└─ Visualización &amp; LaTeX Reports</text>'
        f'<text x="28" y="232" font-size="10" fill="{MID}">[REPOSITORIO &amp; APUNTES]</text>'
        f'<text x="28" y="252" font-size="9.5" fill="{BRIGHT}">▸ Espacio en expansión progresiva</text>'
        f'<text x="28" y="270" font-size="9.5" fill="{MID}">▸ Notebooks, datasets &amp; prácticas</text>'
        f'<rect x="28" y="290" width="266" height="28" rx="4" fill="{BOX0}" stroke="{EDGE1}"/>'
        f'<text x="38" y="308" font-size="9.5" fill="{BRIGHT}">TRACK: <tspan fill="{GOLD}" font-weight="700">● UNLP 2027 – ACT.</tspan></text>'
    )
    labels = (
        f'<text x="464" y="57" text-anchor="middle" font-size="8.8" fill="{DARK}">ASCII.REST // PYTHON EMBLEM (51×28 FULL)</text>'
        f'<text x="782" y="57" text-anchor="middle" font-size="8.8" fill="{DARK}">LORENZ ATTRACTOR // PHASE SPACE</text>'
        f'<text x="782" y="324" text-anchor="middle" font-size="9.2" fill="{MID}">σ=10 • ρ=28 • β=8/3 (RK4)</text>'
    )
    return left_hud + labels
