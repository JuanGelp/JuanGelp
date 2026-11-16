"""
Native SVG generators for:
  • `assets/manifesto-jpi.svg` (960x132): Replaces broken ```ansi blocks with a crisp vector terminal.
  • `assets/telemetry-jpi.svg` (960x196): Replaces broken external Vercel stats images with a native SVG telemetry dashboard.
"""
from __future__ import annotations

from core import BG0, BG1, BOX0, EDGE0, EDGE1, DARK, MID, BRIGHT, GOLD, FONT, svg_doc


def build_manifesto():
    W, H = 960, 132
    body = (
        f'<rect width="{W}" height="{H}" rx="10" fill="{BG0}" stroke="{EDGE1}" stroke-width="1.5"/>'
        f'<rect x="10" y="10" width="{W - 20}" height="{H - 20}" rx="6" fill="{BG1}" stroke="{EDGE0}"/>'
        f'<circle cx="26" cy="24" r="4" fill="{GOLD}"/>'
        f'<circle cx="38" cy="24" r="4" fill="{MID}"/>'
        f'<circle cx="50" cy="24" r="4" fill="{DARK}"/>'
        f'<text x="66" y="28" font-size="10.5" fill="{MID}">jpi@cosmos-node: ~/manifesto</text>'
        f'<line x1="10" y1="36" x2="{W - 10}" y2="36" stroke="{EDGE0}"/>'
        f'<text x="24" y="56" font-size="12" fill="{MID}">'
        f'┌──(<tspan fill="{GOLD}" font-weight="700">jpi@cosmos-node</tspan>)-[<tspan fill="{BRIGHT}" font-weight="700">~/manifesto</tspan>]</text>'
        f'<text x="24" y="74" font-size="12" fill="{MID}">'
        f'└─$ <tspan fill="{GOLD}" font-weight="700">cat identity_core.txt</tspan></text>'
        f'<text x="24" y="96" font-size="12" fill="{BRIGHT}">'
        f'Soy <tspan fill="{GOLD}" font-weight="700">Juan (Jπ)</tspan>. Combino la formación en '
        f'<tspan fill="{MID}" font-weight="700">Licenciatura en Física (UNLP)</tspan> y '
        f'<tspan fill="{MID}" font-weight="700">Ciencia de Datos (UNLP)</tspan></text>'
        f'<text x="24" y="114" font-size="12" fill="{BRIGHT}">'
        f'con el desarrollo web, mobile y visualización 3D/WebGL a través de mi estudio '
        f'<tspan fill="{GOLD}" font-weight="700">Jπ Studio</tspan>.'
        f' <tspan fill="{GOLD}">█<animate attributeName="opacity" values="1;0;1" dur="1.1s" repeatCount="indefinite"/></tspan></text>'
    )
    return svg_doc(W, H, body, "Juan (Jπ) // Manifiesto"), [(None, None)]


def _bar_row(x, y, label, pct_txt, pct, col):
    bw = int(220 * pct)
    return (
        f'<text x="{x}" y="{y}" font-size="10.2" fill="{BRIGHT}">{label}</text>'
        f'<rect x="{x + 195}" y="{y - 9}" width="220" height="9" rx="3" fill="{BG0}" stroke="{EDGE0}"/>'
        f'<rect x="{x + 195}" y="{y - 9}" width="{bw}" height="9" rx="3" fill="{col}"/>'
        f'<text x="{x + 455}" y="{y}" text-anchor="end" font-size="10" fill="{GOLD}" font-weight="700">{pct_txt}</text>'
    )


def build_telemetry():
    W, H = 960, 196
    left = (
        f'<rect x="10" y="10" width="458" height="{H - 20}" rx="8" fill="{BOX0}" stroke="{EDGE1}"/>'
        f'<text x="26" y="34" font-size="11.5" fill="{GOLD}" font-weight="700">'
        f'⚡ TELEMETRÍA DE PERFIL // @JuanGelp</text>'
        f'<line x1="26" y1="44" x2="452" y2="44" stroke="{EDGE0}"/>'
        f'<text x="26" y="68" font-size="10.5" fill="{MID}">▸ IDENTIDAD / MARCA:</text>'
        f'<text x="452" y="68" text-anchor="end" font-size="10.5" fill="{GOLD}" font-weight="700">Juan // Jπ Studio</text>'
        f'<text x="26" y="92" font-size="10.5" fill="{MID}">▸ FÍSICA UNLP (2023–Act.):</text>'
        f'<text x="452" y="92" text-anchor="end" font-size="10.5" fill="{BRIGHT}">Clases • LaTeX • Drive Activo</text>'
        f'<text x="26" y="116" font-size="10.5" fill="{MID}">▸ SHOWROOM Jπ STUDIO:</text>'
        f'<text x="452" y="116" text-anchor="end" font-size="10.5" fill="{GOLD}" font-weight="700">showroom-jpi.pages.dev ●</text>'
        f'<text x="26" y="140" font-size="10.5" fill="{MID}">▸ CIENCIA DE DATOS UNLP:</text>'
        f'<text x="452" y="140" text-anchor="end" font-size="10.5" fill="{BRIGHT}">2027 – Act. (En Expansión)</text>'
        f'<text x="26" y="164" font-size="10.5" fill="{MID}">▸ UBICACIÓN / CONTACTO:</text>'
        f'<text x="452" y="164" text-anchor="end" font-size="10.5" fill="{BRIGHT}">La Plata, AR • juanmgelp22@gmail.com</text>'
    )
    right = (
        f'<rect x="480" y="10" width="470" height="{H - 20}" rx="8" fill="{BOX0}" stroke="{EDGE1}"/>'
        f'<text x="496" y="34" font-size="11.5" fill="{GOLD}" font-weight="700">'
        f'📊 DISTRIBUCIÓN DE STACK &amp; ÁREAS DE TRABAJO</text>'
        f'<line x1="496" y1="44" x2="934" y2="44" stroke="{EDGE0}"/>'
        + _bar_row(496, 70, "Astro • Tailwind • TS", "96%", 0.96, GOLD)
        + _bar_row(496, 98, "Three.js / WebGL • GSAP", "92%", 0.92, MID)
        + _bar_row(496, 126, "Física • Cálculo • LaTeX", "95%", 0.95, BRIGHT)
        + _bar_row(496, 154, "Python • SQL • Data Sci", "85%", 0.85, GOLD)
        + f'<text x="496" y="175" font-size="9.2" fill="{DARK}">WORKFLOWS: Claude Code • n8n • Git / GitHub Actions • Linux</text>'
    )
    body = f'<rect width="{W}" height="{H}" rx="10" fill="{BG0}" stroke="{EDGE1}" stroke-width="1.5"/>' + left + right
    return svg_doc(W, H, body, "JuanGelp // Telemetría y Distribución de Stack"), [(None, None)]
