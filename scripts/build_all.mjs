import fs from "node:fs";
import path from "node:path";
import { Resvg } from "@resvg/resvg-js";
import * as erMod from "./pieces_src/earthrise.ts";
import * as lwMod from "./pieces_src/lava-wall.ts";
import * as ccMod from "./pieces_src/command-city.ts";
import * as eoMod from "./pieces_src/edge-orbit.ts";

const W = 200, H = 100, CW = 6, CH = 6;
const DOTS = " ·•●";
const COVER = [0, 0.3, 0.6, 1];
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map((v) => v / 16 - 0.47);
const clamp = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);
const smooth = (a, b, v) => {
  const k = clamp((v - a) / (b - a));
  return k * k * (3 - 2 * k);
};

const CLS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const hexRgb = (s) => [1, 3, 5].map((i) => parseInt(s.slice(i, i + 2), 16));
const colorDist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);

/**
 * Lock cells whose dot size (character) is 100% invariant across all frames
 * and whose color only jitters across an adjacent palette step (< maxSameCharDist),
 * moving them into the static base layer with zero perceptible change.
 */
function lockSubtleCells(shots, palette, maxSameCharDist = 52, maxAnyDist = 32, protectPred = null) {
  const N = shots.length;
  const rgb = palette.map(hexRgb);
  const grid = shots.map((s) => s.txt.map((row) => [...row]));

  for (let r = 0; r < H; r++) {
    for (let x = 0; x < W; x++) {
      if (protectPred && protectPred(x, r)) continue;
      const k = r * W + x;
      const ch0 = grid[0][r][x];
      const c0 = shots[0].c[k];
      let sameChar = true;
      let maxD = 0;
      for (let i = 1; i < N; i++) {
        if (grid[i][r][x] !== ch0) sameChar = false;
        const d = colorDist(rgb[c0], rgb[shots[i].c[k]]);
        if (d > maxD) maxD = d;
      }
      if ((sameChar && maxD < maxSameCharDist) || maxD < maxAnyDist) {
        for (let i = 1; i < N; i++) {
          grid[i][r][x] = ch0;
          shots[i].c[k] = c0;
        }
      }
    }
  }
  for (let i = 0; i < N; i++) {
    shots[i].txt = grid[i].map((row) => row.join(""));
  }
}

/**
 * Encode a sequence of { txt: string[], c: Uint8Array } frames into an ultra-compact,
 * 100% GitHub-compatible animated SVG using:
 * 1. Static base layer (<g>) + delta frame layers (<g class="f k...">)
 * 2. Color-grouped horizontal run merging across Bayer dither patterns (bridging same-color
 *    cells separated by <= MAX_GAP spaces, since spaces render zero ink and advance by CW)
 * 3. Single-run <text> flattening (eliminating nested <tspan> when a row has 1 run)
 * 4. Row-level dominant color class inheritance on <text> (omitting redundant class="..." on <tspan>)
 */
function encodeSvg({ shots, palette, ground, every, label, maxGap = 38 }) {
  const N = shots.length;
  const baseChar = new Array(W * H).fill(" ");
  const baseCol = new Uint8Array(W * H);

  for (let k = 0; k < W * H; k++) {
    const r = (k / W) | 0, x = k % W;
    let minStep = 3;
    const freq = new Map();
    let bestKey = "", bestCnt = 0, bestCh = " ", bestC = 0;

    for (let i = 0; i < N; i++) {
      const ch = shots[i].txt[r][x];
      const st = DOTS.indexOf(ch);
      if (st < minStep) minStep = st;
      const c = ch === " " ? 0 : shots[i].c[k];
      const key = `${ch}:${c}`;
      const cnt = (freq.get(key) || 0) + 1;
      freq.set(key, cnt);
      if (cnt > bestCnt) {
        bestCnt = cnt;
        bestKey = key;
        bestCh = ch;
        bestC = c;
      }
    }

    // If the modal state's dot step is <= every frame's dot step at cell k,
    // place the modal state in the static base layer so only frames that differ need to draw over it!
    const bestStep = DOTS.indexOf(bestCh);
    if (bestCnt === N || (bestCh !== " " && bestStep <= minStep && bestCnt >= 2)) {
      baseChar[k] = bestCh;
      baseCol[k] = bestC;
    }
  }

  const used = new Set();
  const renderLayer = (shot, isStaticLayer) => {
    let out = "";
    for (let r = 0; r < H; r++) {
      const line = shot.txt[r];
      const byColor = new Map();

      for (let x = 0; x < W; x++) {
        const k = r * W + x;
        let ch, col;
        if (isStaticLayer) {
          ch = baseChar[k];
          col = baseCol[k];
        } else {
          ch = line[x];
          col = shot.c[k];
          if (ch === baseChar[k] && (ch === " " || col === baseCol[k])) continue;
        }
        if (ch === " ") continue;
        used.add(col);
        let list = byColor.get(col);
        if (!list) {
          list = [];
          byColor.set(col, list);
        }
        list.push({ x, ch });
      }

      if (byColor.size === 0) continue;

      const yVal = (r + 0.5) * CH;
      const entries = [...byColor.entries()];

      if (entries.length === 1) {
        const [col, cells] = entries[0];
        const xs = cells.map((c) => c.x * CW).join(" ");
        const str = cells.map((c) => c.ch).join("");
        out += `<text x="${xs}" y="${yVal}" class="${CLS[col]}">${esc(str)}</text>`;
        continue;
      }

      let rowSpans = "";
      const domCol = entries[0][0];
      for (let i = 0; i < entries.length; i++) {
        const [col, cells] = entries[i];
        const xs = cells.map((c) => c.x * CW).join(" ");
        const str = cells.map((c) => c.ch).join("");
        const cAttr = col === domCol ? "" : ` class="${CLS[col]}"`;
        rowSpans += `<tspan x="${xs}"${cAttr}>${esc(str)}</tspan>`;
      }
      out += `<text y="${yVal}" class="${CLS[domCol]}">${rowSpans}</text>`;
    }
    return out;
  };

  const staticBody = `<g>${renderLayer(shots[0], true)}</g>`;
  let dynGroups = "", keys = "";
  const pct = (i) => `${+((i / N) * 100).toFixed(2)}%`;

  for (let i = 0; i < N; i++) {
    const kf =
      i === 0
        ? `0%{opacity:1}${pct(1)}{opacity:0}`
        : `0%{opacity:0}${pct(i)}{opacity:1}${pct(i + 1)}{opacity:0}`;
    keys += `@keyframes k${i}{${kf}}.k${i}{animation-name:k${i}}`;
    dynGroups += `<g class="f k${i}">${renderLayer(shots[i], false)}</g>`;
  }

  const inks = [...used]
    .sort((a, b) => a - b)
    .map((c) => `.${CLS[c]}{fill:${palette[c]}}`)
    .join("");

  const fontCss = `text{font:10px ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;dominant-baseline:central}`;
  const animCss = `.f{opacity:0;will-change:opacity;animation:${every}s step-end infinite}${keys}@media (prefers-reduced-motion:reduce){.f{animation:none}.k0{opacity:1}}`;
  const width = W * CW, height = H * CH;

  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="100%" role="img" aria-label="${esc(label)}">` +
    `<title>${esc(label)}</title>` +
    `<style>${fontCss}${inks}${animCss}</style>` +
    `<rect width="${width}" height="${height}" fill="${ground}"/>` +
    staticBody +
    dynGroups +
    `</svg>`
  );
}

function renderSingleFrameSvg(shot, palette, ground) {
  return encodeSvg({
    shots: [shot],
    palette,
    ground,
    every: 1,
    label: "frame",
  }).replace('width="100%"', 'width="1200" height="600"').replace('.f{opacity:0;', '.f{opacity:1;');
}

// 1. EARTHRISE (Physics): Full 360-degree seamless rotation of the ENTIRE Earth + clouds + twinkling stars
function buildEarthrise(N = 24, every = 3.8) {
  const T_LOOP = (2 * Math.PI) / 0.045; // 139.626s = 1 full 360-degree rotation of Earth
  const fn = erMod.default();
  const shots = [];
  for (let i = 0; i < N; i++) {
    const c = new Uint8Array(W * H);
    const t = (i / N) * T_LOOP;
    const txt = fn(t, { color: c }).split("\n");
    shots.push({ txt, c });
  }
  return {
    svg: encodeSvg({
      shots,
      palette: erMod.meta.palette,
      ground: erMod.meta.ground,
      every,
      label: "earthrise, in ascii",
    }),
    shots,
    palette: erMod.meta.palette,
    ground: erMod.meta.ground,
  };
}

// 2. LAVA WALL (Web Dev - Jπ Studio): Pure lava-wall.ts
function buildLavaWall(N = 20, every = 3.2) {
  const fn = lwMod.default();
  const shots = [];
  for (let i = 0; i < N; i++) {
    const c = new Uint8Array(W * H);
    const t = (i / N) * 30;
    const txt = fn(t, { color: c }).split("\n");
    shots.push({ txt, c });
  }
  lockSubtleCells(shots, lwMod.meta.palette, 78, 45, (x, r) => x === 180 && r === 68);
  return {
    svg: encodeSvg({
      shots,
      palette: lwMod.meta.palette,
      ground: lwMod.meta.ground,
      every,
      label: "lava wall, in ascii",
    }),
    shots,
    palette: lwMod.meta.palette,
    ground: lwMod.meta.ground,
  };
}

// 3. COMMAND CITY (Data Science): Pure command-city.ts
function buildCommandCity(N = 20, every = 3.0) {
  const fn = ccMod.default();
  const palette = [...ccMod.meta.palette];
  const shots = [];
  for (let i = 0; i < N; i++) {
    const c = new Uint8Array(W * H);
    const t = (i / N) * 5.0;
    const txt = fn(t, { color: c }).split("\n");
    shots.push({ txt, c });
  }
  lockSubtleCells(shots, palette, 58, 38);
  return {
    svg: encodeSvg({
      shots,
      palette,
      ground: ccMod.meta.ground,
      every,
      label: "command city, in ascii",
    }),
    shots,
    palette,
    ground: ccMod.meta.ground,
  };
}

// 4. HEADER BANNER: edge-orbit.ts with the medium-sized detailed golden Jπ letters in the center (halftone 3D dot-shaded, zero borders, zero extra text)
function buildHeaderEdgeOrbitJpi(N = 24, every = 3.6) {
  const fn = eoMod.default();
  const palette = [...eoMod.meta.palette];
  // Add rich golden ramp (#5a3c20 -> #e5b75f -> #ffd27c -> #fff8dc)
  palette.push("#4a3014", "#7c511d", "#b57c2a", "#d99f3c", "#e5b75f", "#f5cf76", "#ffe8a3", "#fff8dc");
  const P = palette.map((s) => [1, 3, 5].map((i) => parseInt(s.slice(i, i + 2), 16) / 255));

  const nearestGold = (r, g, b) => {
    let best = 0, bd = 1e9;
    for (let i = 0; i < P.length; i++) {
      const dr = P[i][0] - r, dg = P[i][1] - g, db = P[i][2] - b;
      const d = 0.3 * dr * dr + 0.5 * dg * dg + 0.2 * db * db;
      if (d < bd) (bd = d), (best = i);
    }
    return best;
  };

  // Sample across a full 6-second request cycle (PD = 6) so requests launch, arc across the globe, and land with expanding rings!
  const shots0 = [];
  for (let i = 0; i < N; i++) {
    const c = new Uint8Array(W * H);
    const t = (i / N) * 6.0;
    const txt = fn(t, { color: c }).split("\n");
    shots0.push({ txt: txt.map((l) => [...l]), c });
  }

  // High-resolution signed distance / coverage field for medium-sized detailed "Jπ" centered at (100, 48)
  const jpiCov = new Float32Array(W * H);
  const jpiBevel = new Float32Array(W * H);

  function jpiSdf(x, y) {
    // Letter J on the left (x around 75..96, y around 36..62)
    const dJTop = Math.max(Math.abs(x - 89.5) - 6.8, Math.abs(y - 38.0) - 1.9);
    const dJStem = Math.max(Math.abs(x - 91.5) - 2.7, Math.abs(y - 46.2) - 8.5);
    const dxJ = x - 83.5, dyJ = y - 54.2;
    const rJ = Math.hypot(dxJ, dyJ);
    const dJArc = dyJ >= -0.5 ? Math.abs(rJ - 8.0) - 2.6 : Math.hypot(dxJ + 8.0, dyJ + 0.5) - 2.7;
    const dJBulb = Math.hypot(x - 75.8, y - 53.2) - 2.9;
    const dJ = Math.min(dJTop, dJStem, dJArc, dJBulb);

    // Letter π on the right (x around 101..126, y around 44..62)
    const barY = 45.0 - 0.6 * smooth(121, 125.5, x) + 0.6 * smooth(104, 100.5, x);
    const dPiBar = Math.max(Math.abs(x - 113.2) - 12.2, Math.abs(y - barY) - 2.1);
    const legLx = 106.8 - 1.8 * Math.pow(clamp((y - 45) / 16.5), 1.6);
    const dPiLegL = Math.max(Math.abs(x - legLx) - 2.4, Math.abs(y - 53.5) - 8.3);
    const legRx = 119.2 + 1.4 * Math.pow(clamp((y - 55) / 6.5), 1.5);
    const dPiLegR = Math.max(Math.abs(x - legRx) - 2.5, Math.abs(y - 53.5) - 8.3);
    const dPiFootR = Math.hypot((x - 121.2) * 0.8, y - 60.6) - 2.2;
    const dPi = Math.min(dPiBar, dPiLegL, dPiLegR, dPiFootR);

    return Math.min(dJ, dPi);
  }

  for (let r = 0; r < H; r++) {
    for (let x = 0; x < W; x++) {
      const k = r * W + x;
      let cov = 0;
      for (const [ox, oy] of [[-0.25, -0.25], [0.25, -0.25], [-0.25, 0.25], [0.25, 0.25]]) {
        const d = jpiSdf(x + 0.5 + ox, r + 0.5 + oy);
        cov += smooth(0.45, -0.45, d);
      }
      cov /= 4;
      jpiCov[k] = cov;

      const gx = jpiSdf(x + 1.0, r + 0.5) - jpiSdf(x, r + 0.5);
      const gy = jpiSdf(x + 0.5, r + 1.0) - jpiSdf(x + 0.5, r);
      const gl = Math.hypot(gx, gy, 1e-4);
      const bevel = clamp(0.65 + 0.35 * ((-gx * 0.55 - gy * 0.83) / gl));
      jpiBevel[k] = bevel;
    }
  }

  const GOLD_C = [0.95, 0.75, 0.36]; // #e5b75f warm gold

  for (let i = 0; i < N; i++) {
    const glintAt = 68 + (i / N) * 76;
    for (let r = 32; r < 66; r++) {
      for (let x = 70; x < 130; x++) {
        const k = r * W + x;
        const c = jpiCov[k];
        if (c < 0.16) continue;

        const bev = jpiBevel[k];
        const gDist = Math.abs((x + (r - 50) * 0.55) - glintAt);
        const glint = gDist < 4.5 ? 1 - smooth(0, 4.5, gDist) : 0;

        const lum = (0.98 + 0.42 * bev + 0.48 * glint) * c;
        const cr = Math.min(1.2, GOLD_C[0] * lum + glint * 0.25);
        const cg = Math.min(1.2, GOLD_C[1] * lum + glint * 0.25);
        const cb = Math.min(1.2, GOLD_C[2] * lum + glint * 0.22);
        const floor = 0.52 * c;

        const peak = Math.max(cr, cg, cb, 1e-4);
        const level = clamp(floor + (1 - floor) * Math.pow(peak, 0.85) * 0.98);
        const step = Math.max(1, Math.min(3, Math.round(level * 3 + BAYER[(r & 3) * 4 + (x & 3)] * 0.45)));
        shots0[i].txt[r][x] = DOTS[step];
        const want = Math.min(1, (level + 0.06) / COVER[step]);
        const s = (0.3 + 0.7 * want) / peak;
        shots0[i].c[k] = nearestGold(clamp(cr * s), clamp(cg * s), clamp(cb * s));
      }
    }
  }

  const shots = shots0.map((s) => ({ txt: s.txt.map((row) => row.join("")), c: s.c }));
  lockSubtleCells(shots, palette, 54, 34);
  return {
    svg: encodeSvg({
      shots,
      palette,
      ground: eoMod.meta.ground,
      every,
      label: "Juan // Jπ Studio — Edge Orbit Header",
    }),
    shots,
    palette,
    ground: eoMod.meta.ground,
  };
}

const t0 = Date.now();
const er = buildEarthrise(24, 3.8);
const lw = buildLavaWall(20, 3.2);
const cc = buildCommandCity(20, 3.0);
const hd = buildHeaderEdgeOrbitJpi(24, 3.6);

const assetsDir = "/home/antigravity/JuanGelp/assets";
const artDir = "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/2d1176f3-daf0-4f2e-80cd-8c4ef4592fb4";

for (const [fname, prefix, data] of [
  ["card-physics.svg", "physics", er],
  ["card-jpi-studio.svg", "studio", lw],
  ["card-datascience.svg", "cyber", cc],
  ["banner-cosmos-jpi.svg", "banner", hd],
]) {
  fs.writeFileSync(path.join(assetsDir, fname), data.svg);
  fs.writeFileSync(path.join(artDir, fname), data.svg);
  const gCnt = (data.svg.match(/<g/g) || []).length;
  const tCnt = (data.svg.match(/<text/g) || []).length;
  const sCnt = (data.svg.match(/<tspan/g) || []).length;
  console.log(
    `${fname}: ${(data.svg.length / 1024).toFixed(1)} KB | DOM nodes: ${gCnt + tCnt + sCnt} (g=${gCnt}, text=${tCnt}, tspan=${sCnt})`
  );

  const f0Svg = renderSingleFrameSvg(data.shots[0], data.palette, data.ground);
  const resvg0 = new Resvg(f0Svg, { fitTo: { mode: "width", value: 1200 } });
  fs.writeFileSync(path.join(artDir, `${prefix}_frame0.png`), resvg0.render().asPng());
}
console.log("Done in", Date.now() - t0, "ms");
