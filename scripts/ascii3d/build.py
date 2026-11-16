"""Build every animated SVG into ../../assets and (optionally) render previews.

usage:  python3 scripts/ascii3d/build.py [--preview DIR] [only ...]
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ASSETS = os.path.normpath(os.path.join(HERE, "..", "..", "assets"))

TARGETS = {
    "banner": ("banner", "banner-cosmos-jpi.svg"),
    "physics": ("card_physics", "card-physics.svg"),
    "studio": ("card_studio", "card-jpi-studio.svg"),
    "cyber": ("card_cyber", "card-datascience.svg"),
}

FRAME_RE = re.compile(r'<g( display="none")?><animate attributeName="display"[^>]*/>')


def frame_variant(svg: str, k: int) -> str:
    i = -1

    def sub(m):
        nonlocal i
        i += 1
        return "<g>" if i == k else '<g display="none">'
    return FRAME_RE.sub(sub, svg)


def preview(name, svg, outdir, nframes, scale=2):
    from PIL import Image
    os.makedirs(outdir, exist_ok=True)
    if nframes <= 1:
        p = os.path.join(outdir, f"{name}.svg")
        with open(p, "w") as f:
            f.write(svg)
        png = os.path.join(outdir, f"{name}_frame0.png")
        subprocess.run(["rsvg-convert", "-z", str(scale), "-o", png, p], check=True)
        os.remove(p)
        return
    pngs = []
    for k in range(nframes):
        p = os.path.join(outdir, f"{name}_f{k:02d}.svg")
        with open(p, "w") as f:
            f.write(frame_variant(svg, k))
        png = p[:-4] + ".png"
        subprocess.run(["rsvg-convert", "-z", str(scale), "-o", png, p], check=True)
        os.remove(p)
        pngs.append(png)
    ims = [Image.open(p).convert("RGB") for p in pngs]
    ims[0].save(os.path.join(outdir, f"{name}.png"))
    ims[0].save(os.path.join(outdir, f"{name}.gif"), save_all=True, append_images=ims[1:],
                duration=60, loop=0, optimize=False)
    for p in pngs[1:]:
        os.remove(p)
    os.rename(pngs[0], os.path.join(outdir, f"{name}_frame0.png"))


def main():
    args = sys.argv[1:]
    outdir = None
    if "--preview" in args:
        i = args.index("--preview")
        outdir = args[i + 1]
        del args[i:i + 2]
    only = args or list(TARGETS)
    os.makedirs(ASSETS, exist_ok=True)
    import importlib
    for key in only:
        mod_name, fname = TARGETS[key]
        t0 = time.time()
        mod = importlib.import_module(mod_name)
        svg, frames = mod.build()
        path = os.path.join(ASSETS, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        if fname == "card-datascience.svg":
            shutil.copyfile(path, os.path.join(ASSETS, "card-cybersec.svg"))
        nodes = svg.count("<")
        print(f"{fname:26s} {len(svg.encode()) / 1024:6.1f} KB  frames={len(frames):2d}  "
              f"tags={nodes:5d}  {time.time() - t0:5.1f}s")
        if outdir:
            preview(key, svg, outdir, len(frames))

    import extras
    for name, fn in (("manifesto-jpi.svg", extras.build_manifesto),
                     ("telemetry-jpi.svg", extras.build_telemetry)):
        svg, _ = fn()
        p = os.path.join(ASSETS, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"{name:26s} {len(svg.encode()) / 1024:6.1f} KB  static")
        if outdir:
            preview(name[:-4], svg, outdir, 1)


if __name__ == "__main__":
    main()
