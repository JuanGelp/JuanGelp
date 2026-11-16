"""
Wide Panoramic Web Development Banner — `assets/card-jpi-studio.svg` [960x350].

Renders the full-resolution 50x28 `ascii.rest/html` emblem in the centre with its
carved-out '5', 4-tone shading, and diagonal `/` specular glint sweep, flanked by
the Jπ Studio architecture terminal on the left and a 3D WebGL mesh on the right.
"""
from __future__ import annotations

import json
import numpy as np

from core import (BG0, BOX0, EDGE0, EDGE1, DARK, MID, BRIGHT, GOLD,
                  Grid, animated_layers, svg_doc)

W, H = 960, 350
N, DUR = 12, 1.15
G = Grid(154, 28, 20.0, 56.0, 6.0, 9.4, fs=9.8)
TAU = 2 * np.pi

_HT = json.load(open("/tmp/ht_frames.json"))["frames"]


def render_full_html_shield(frame_idx, chars, cls):
    """Place the full-resolution 50x28 `ascii.rest/html` shield at cols 51..101."""
    f = _HT[(frame_idx + 4) % len(_HT)]
    mono_lines = f["monoTxt"].split("\n")
    col_arr = np.array(f["col"], dtype=np.int16).reshape(28, 50)
    c_off = 51
    for r in range(min(28, len(mono_lines))):
        line = mono_lines[r].ljust(50)[:50]
        for c in range(50):
            ch = line[c]
            if ch == " ":
                continue
            pal = int(col_arr[r, c])
            ink = pal % 4
            glint = max(0, (pal - 12) // 4)
            if glint >= 2 or ch == "/":
                k = 4   # blazing golden specular slash (#e5b75f)
            elif glint == 1:
                k = 3 if ink in (0, 3) else 4
            else:
                # Right half of shield & inner 5 strokes brighter than left half
                k = 2 if c < 25 else 3
                if 7 <= r <= 20 and 12 <= c <= 37:
                    k = 4 if c >= 25 else 3
            chars[r, c_off + c] = ch
            cls[r, c_off + c] = k


def _build_planes():
    planes = []
    for a in range(3):
        for s in (-1.0, 1.0):
            n = np.zeros(3); n[a] = s
            planes.append((n, 0.76, 0))
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                n = np.array([sx, sy, sz]) / np.sqrt(3.0)
                planes.append((n, 0.82, 1))
    for a in range(3):
        for s1 in (-1.0, 1.0):
            for s2 in (-1.0, 1.0):
                n = np.zeros(3)
                n[(a + 1) % 3] = s1 / np.sqrt(2.0)
                n[(a + 2) % 3] = s2 / np.sqrt(2.0)
                planes.append((n, 0.84, 2))
    return (np.array([p[0] for p in planes]),
            np.array([p[1] for p in planes]),
            np.array([p[2] for p in planes]))


N_PL, D_PL, K_PL = _build_planes()


def render_webgl_mesh(t, chars, cls):
    ang = TAU * (t / DUR) * 0.25
    tilt, roll = 0.52, 0.26
    cy_a, sy_a = np.cos(ang), np.sin(ang)
    cx_a, sx_a = np.cos(tilt), np.sin(tilt)
    cz_a, sz_a = np.cos(roll), np.sin(roll)

    x, y, z = N_PL[:, 0], N_PL[:, 1], N_PL[:, 2]
    x1, z1 = x * cy_a + z * sy_a, -x * sy_a + z * cy_a
    y2, z2 = y * cx_a - z1 * sx_a, y * sx_a + z1 * cx_a
    nx = x1 * cz_a - y2 * sz_a
    ny = x1 * sz_a + y2 * cz_a
    nz = z2
    Nr = np.stack([nx, ny, nz], axis=-1)

    Lv = np.array([-0.52, -0.46, 0.72]); Lv /= np.linalg.norm(Lv)
    cx, cy = 129.0, 13.2
    sx, sy = 16.0, 9.8
    face_chars = " :+#8@"

    for r in range(2, 25):
        for c in range(108, 151):
            px = (c - cx) / sx
            py = (r - cy) / sy
            rhs = D_PL - (nx * px + ny * py)
            if np.any((np.abs(nz) < 1e-6) & (rhs < 0)):
                continue
            front = nz > 1e-6
            back = nz < -1e-6
            z_upper = np.where(front, rhs / np.where(front, nz, 1.0), 1e9)
            z_lower = np.where(back, rhs / np.where(back, nz, -1.0), -1e9)
            z_hit = np.min(z_upper)
            z_bot = np.max(z_lower)
            if z_hit < z_bot:
                continue
            i0 = int(np.argmin(z_upper))
            P = np.array([px, py, z_hit])
            margins = D_PL - (Nr @ P)
            margins[i0] = 1e9
            edge_dist = float(np.min(margins))
            n_hit = Nr[i0]
            lam = max(0.0, float(np.dot(n_hit, Lv)))
            L = np.clip(0.14 + 0.86 * lam, 0.0, 1.0)
            is_edge = (edge_dist < 0.058) or ((z_hit - z_bot) < 0.14)
            if is_edge:
                chars[r, c] = "@" if L > 0.55 else "#"
                cls[r, c] = 4
            else:
                ch = face_chars[int(round((L ** 0.85) * (len(face_chars) - 1)))]
                kind = int(K_PL[i0])
                k = 3 if (kind == 0 and L > 0.58) or (kind == 2 and L > 0.48) else (2 if L > 0.32 else 1)
                chars[r, c] = ch
                cls[r, c] = k


def build():
    frames = []
    for i in range(N):
        t = i * DUR / N
        chars, cls = G.blank()
        render_full_html_shield(i, chars, cls)
        render_webgl_mesh(t, chars, cls)
        frames.append((chars, cls))
    c0_ref, k0_ref = frames[0]
    for i in range(1, N):
        ci, ki = frames[i]
        same_k = (ki == k0_ref) & (ki > 0) & (ki < 4) & (ci != " ") & (c0_ref != " ")
        ci[:, 106:] = np.where(same_k[:, 106:], c0_ref[:, 106:], ci[:, 106:])
    layers, _ = animated_layers(G, frames, DUR, gap=8)
    return svg_doc(W, H, chrome_back() + layers + chrome_front(),
                   "Desarrollo Web - Jπ Studio — Full HTML5 ASCII Emblem & 3D WebGL Mesh"), frames


def chrome_back():
    return (
        f'<rect width="{W}" height="{H}" rx="10" fill="{BG0}" stroke="{EDGE1}" stroke-width="1.5"/>'
        f'<rect x="12" y="10" width="{W - 24}" height="28" rx="5" fill="{BOX0}" stroke="{EDGE1}"/>'
        f'<circle cx="26" cy="24" r="4" fill="{GOLD}"/>'
        f'<circle cx="38" cy="24" r="4" fill="{MID}"/>'
        f'<text x="52" y="28" font-size="11" fill="{GOLD}" font-weight="700">'
        f'🚀 DESARROLLO WEB - Jπ STUDIO // HTML5 &amp; 3D WebGL ARCHITECTURE</text>'
        f'<text x="{W - 24}" y="28" text-anchor="end" font-size="10" fill="{MID}">'
        f'[showroom-jpi.pages.dev]</text>'
        f'<rect x="12" y="42" width="{W - 24}" height="{H - 52}" rx="6" fill="#07010e" stroke="{EDGE0}"/>'
        f'<line x1="316" y1="50" x2="316" y2="{H - 18}" stroke="{EDGE0}" stroke-dasharray="3 4"/>'
        f'<line x1="646" y1="50" x2="646" y2="{H - 18}" stroke="{EDGE0}" stroke-dasharray="3 4"/>'
    )


def chrome_front():
    left_hud = (
        f'<text x="28" y="68" font-size="10.5" fill="{GOLD}" font-weight="700">$ jpi-studio --stack --services</text>'
        f'<text x="28" y="92" font-size="10" fill="{MID}">[SERVICIOS // QUÉ OFREZCO]</text>'
        f'<text x="28" y="112" font-size="9.8" fill="{BRIGHT}">├─ Web &amp; Mobile de Autor</text>'
        f'<text x="28" y="130" font-size="9.8" fill="{BRIGHT}">├─ Experiencias 3D / WebGL</text>'
        f'<text x="28" y="148" font-size="9.8" fill="{BRIGHT}">├─ Motion Design Interactivo</text>'
        f'<text x="28" y="166" font-size="9.8" fill="{BRIGHT}">└─ Automatización IA &amp; Flujos</text>'
        f'<text x="28" y="196" font-size="10" fill="{MID}">[STACK &amp; HERRAMIENTAS]</text>'
        f'<text x="28" y="216" font-size="9.8" fill="{GOLD}">▸ Astro • Tailwind • TypeScript</text>'
        f'<text x="28" y="234" font-size="9.8" fill="{GOLD}">▸ Three.js / WebGL • Shaders</text>'
        f'<text x="28" y="252" font-size="9.8" fill="{BRIGHT}">▸ GSAP • Lenis Scroll • Rive</text>'
        f'<text x="28" y="270" font-size="9.8" fill="{MID}">▸ Claude Code • n8n Workflows</text>'
        f'<rect x="28" y="290" width="272" height="28" rx="4" fill="{BOX0}" stroke="{EDGE1}"/>'
        f'<text x="38" y="308" font-size="9.5" fill="{BRIGHT}">STATUS: <tspan fill="{GOLD}" font-weight="700">● SHOWROOM ONLINE</tspan></text>'
    )
    labels = (
        f'<text x="481" y="57" text-anchor="middle" font-size="8.8" fill="{DARK}">ASCII.REST // HTML5 EMBLEM (50×28 FULL)</text>'
        f'<text x="794" y="57" text-anchor="middle" font-size="8.8" fill="{DARK}">WebGL // 3D BEVELED MESH</text>'
        f'<text x="794" y="324" text-anchor="middle" font-size="9.2" fill="{MID}">REALTIME Z-BUFFER • 60 FPS</text>'
    )
    return left_hud + labels
