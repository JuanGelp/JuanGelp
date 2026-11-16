import fs from "node:fs";
import path from "node:path";
import { Resvg } from "@resvg/resvg-js";
import * as erMod from "./pieces_src/earthrise.ts";
import * as lwMod from "./pieces_src/lava-wall.ts";
import * as ccMod from "./pieces_src/command-city.ts";
import * as eoMod from "./pieces_src/edge-orbit.ts";

const W = 200, H = 100, CW = 10, CH = 10;
const DOTS = " ·•●";
const COVER = [0, 0.3, 0.6, 1];
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map((v) => v / 16 - 0.47);
const clamp = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);
const smooth = (a, b, v) => {
  const k = clamp((v - a) / (b - a));
  return k * k * (3 - 2 * k);
};
const mix = (a, b, k) => a + (b - a) * k;

const CLS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const hexRgb = (s) => [1, 3, 5].map((i) => parseInt(s.slice(i, i + 2), 16));
const colorDist = (rgbA, rgbB) =>
  Math.hypot(rgbA[0] - rgbB[0], rgbA[1] - rgbB[1], rgbA[2] - rgbA[2]);

/**
 * Encode a sequence of { txt: string[], c: Uint8Array } frames into a compact,
 * 100% GitHub-compatible animated SVG with static base layer + delta frame layers.
 */
function encodeSvg({ shots, palette, ground, every, label }) {
  const N = shots.length;
  const isDyn = new Uint8Array(W * H);

  for (let k = 0; k < W * H; k++) {
    const r = (k / W) | 0, x = k % W;
    const ch0 = shots[0].txt[r][x], c0 = shots[0].c[k];
    for (let i = 1; i < N; i++) {
      const chi = shots[i].txt[r][x], ci = shots[i].c[k];
      if (chi !== ch0 || (chi !== " " && ci !== c0)) {
        isDyn[k] = 1;
        break;
      }
    }
  }

  const used = new Set();
  const renderLayer = (shot, wantDyn) => {
    let out = "";
    for (let r = 0; r < H; r++) {
      let rowSpans = "", x = 0;
      const line = shot.txt[r];
      while (x < W) {
        const k = r * W + x;
        const ch = isDyn[k] === wantDyn ? line[x] : " ";
        if (ch === " ") {
          x++;
          continue;
        }
        const col = shot.c[k];
        used.add(col);
        const x0 = x;
        let run = "";
        while (x < W) {
          const kk = r * W + x;
          const cc = isDyn[kk] === wantDyn ? line[x] : " ";
          if (cc !== " " && shot.c[kk] === col) {
            run += cc;
            x++;
          } else if (
            cc === " " &&
            x + 1 < W &&
            isDyn[kk + 1] === wantDyn &&
            line[x + 1] !== " " &&
            shot.c[kk + 1] === col
          ) {
            run += " ";
            x++;
          } else if (
            cc === " " &&
            x + 2 < W &&
            (isDyn[kk + 1] === wantDyn ? line[x + 1] : " ") === " " &&
            isDyn[kk + 2] === wantDyn &&
            line[x + 2] !== " " &&
            shot.c[kk + 2] === col
          ) {
            run += "  ";
            x += 2;
          } else {
            break;
          }
        }
        rowSpans += `<tspan x="${x0 * CW}" class="${CLS[col]}">${esc(run)}</tspan>`;
      }
      if (rowSpans) out += `<text y="${(r + 0.5) * CH}">${rowSpans}</text>`;
    }
    return out;
  };

  const staticBody = `<g>${renderLayer(shots[0], 0)}</g>`;
  let dynGroups = "", keys = "";
  const pct = (i) => `${+((i / N) * 100).toFixed(2)}%`;

  for (let i = 0; i < N; i++) {
    let kf = "", state = -1;
    for (let s = 0; s <= N; s++) {
      const v = s < N ? (s === i ? 1 : 0) : 0;
      if (v !== state) {
        kf += `${pct(s)}{opacity:${v}}`;
        state = v;
      }
    }
    keys += `@keyframes k${i}{${kf}}.k${i}{animation-name:k${i}}`;
    dynGroups += `<g class="f k${i}">${renderLayer(shots[i], 1)}</g>`;
  }

  const inks = [...used]
    .sort((a, b) => a - b)
    .map((c) => `.${CLS[c]}{fill:${palette[c]}}`)
    .join("");

  const fontCss = `text{font:16.67px ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;white-space:pre;dominant-baseline:central}`;
  const animCss = `.f{opacity:0;animation:${every}s step-end infinite}${keys}@media (prefers-reduced-motion:reduce){.f{animation:none}.k0{opacity:1}}`;
  const width = W * CW, height = H * CH;

  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="100%" role="img" aria-label="${esc(label)}" xml:space="preserve">` +
    `<title>${esc(label)}</title>` +
    `<style>${fontCss}${inks}${animCss}</style>` +
    `<rect width="${width}" height="${height}" fill="${ground}"/>` +
    staticBody +
    dynGroups +
    `</svg>`
  );
}

function renderSingleFrameSvg(shot, palette, ground) {
  const width = W * CW, height = H * CH;
  const inks = palette.map((p, i) => `.${CLS[i]}{fill:${p}}`).join("");
  const fontCss = `text{font:16.67px "Liberation Mono",monospace;white-space:pre;dominant-baseline:central}`;
  let out = "";
  for (let r = 0; r < H; r++) {
    let rowSpans = "", x = 0;
    const line = shot.txt[r];
    while (x < W) {
      if (line[x] === " ") { x++; continue; }
      const col = shot.c[r * W + x];
      const x0 = x;
      let run = "";
      while (x < W && line[x] !== " " && shot.c[r * W + x] === col) {
        run += line[x];
        x++;
      }
      rowSpans += `<tspan x="${x0 * CW}" class="${CLS[col]}">${esc(run)}</tspan>`;
    }
    if (rowSpans) out += `<text y="${(r + 0.5) * CH}">${rowSpans}</text>`;
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="1200" height="600" xml:space="preserve"><style>${fontCss}${inks}</style><rect width="${width}" height="${height}" fill="${ground}"/><g>${out}</g></svg>`;
}

// 1. EARTHRISE (Physics): Full 360-degree seamless rotation of the ENTIRE Earth + clouds + twinkling stars
function buildEarthrise(N = 24, every = 4.8) {
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
function buildLavaWall(N = 16, every = 3.2) {
  const fn = lwMod.default();
  const rgbPal = lwMod.meta.palette.map(hexRgb);
  const shots0 = [];
  for (let i = 0; i < N; i++) {
    const c = new Uint8Array(W * H);
    const t = (i / N) * 30;
    const txt = fn(t, { color: c }).split("\n");
    shots0.push({ txt: txt.map((l) => [...l]), c });
  }
  for (let r = 0; r < H; r++) {
    for (let x = 0; x < W; x++) {
      const k = r * W + x;
      const isTally = x === 180 && r === 68;
      if (isTally) continue;
      let charsSame = true;
      let maxDist = 0;
      const c0 = shots0[0].c[k];
      for (let i = 1; i < N; i++) {
        if (shots0[i].txt[r][x] !== shots0[0].txt[r][x]) charsSame = false;
        const d = colorDist(rgbPal[c0], rgbPal[shots0[i].c[k]]);
        if (d > maxDist) maxDist = d;
      }
      if ((charsSame && maxDist < 85) || (c0 <= 5 && maxDist < 75)) {
        for (let i = 1; i < N; i++) {
          shots0[i].txt[r][x] = shots0[0].txt[r][x];
          shots0[i].c[k] = c0;
        }
      }
    }
  }
  const shots = shots0.map((s) => ({ txt: s.txt.map((row) => row.join("")), c: s.c }));
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
function buildCommandCity(N = 20, every = 3.6) {
  const fn = ccMod.default();
  const palette = [...ccMod.meta.palette];
  const rgbPal = palette.map(hexRgb);

  const shots0 = [];
  for (let i = 0; i < N; i++) {
    const c = new Uint8Array(W * H);
    const t = (i / N) * 5.0;
    const txt = fn(t, { color: c }).split("\n");
    shots0.push({ txt: txt.map((l) => [...l]), c });
  }

  for (let r = 0; r < H; r++) {
    for (let x = 0; x < W; x++) {
      const k = r * W + x;
      let charsSame = true;
      let maxDist = 0;
      const c0 = shots0[0].c[k];
      for (let i = 1; i < N; i++) {
        if (shots0[i].txt[r][x] !== shots0[0].txt[r][x]) charsSame = false;
        const d = colorDist(rgbPal[c0], rgbPal[shots0[i].c[k]]);
        if (d > maxDist) maxDist = d;
      }
      if ((charsSame && maxDist < 60) || maxDist < 42) {
        for (let i = 1; i < N; i++) {
          shots0[i].txt[r][x] = shots0[0].txt[r][x];
          shots0[i].c[k] = c0;
        }
      }
    }
  }

  const shots = shots0.map((s) => ({ txt: s.txt.map((row) => row.join("")), c: s.c }));
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
function buildHeaderEdgeOrbitJpi(N = 24, every = 4.0) {
  const fn = eoMod.default();
  const palette = [...eoMod.meta.palette];
  // Add rich golden ramp (#5a3c20 -> #e5b75f -> #ffd27c -> #fff8dc)
  const g0 = palette.length;
  palette.push("#4a3014", "#7c511d", "#b57c2a", "#d99f3c", "#e5b75f", "#f5cf76", "#ffe8a3", "#fff8dc");
  const P = palette.map((s) => [1, 3, 5].map((i) => parseInt(s.slice(i, i + 2), 16) / 255));
  const rgbPal = palette.map(hexRgb);

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

  // Keep 100% of arcing orange/tangerine requests, landing rings, sun flare, and twinkling stars;
  // lock negligible sub-pixel drift on unlit sea/land where character and color barely change over 6s
  for (let r = 0; r < H; r++) {
    for (let x = 0; x < W; x++) {
      const k = r * W + x;
      let charsSame = true;
      let maxDist = 0;
      const c0 = shots0[0].c[k];
      for (let i = 1; i < N; i++) {
        if (shots0[i].txt[r][x] !== shots0[0].txt[r][x]) charsSame = false;
        const d = colorDist(rgbPal[c0], rgbPal[shots0[i].c[k]]);
        if (d > maxDist) maxDist = d;
      }
      if ((charsSame && maxDist < 58) || maxDist < 38) {
        for (let i = 1; i < N; i++) {
          shots0[i].txt[r][x] = shots0[0].txt[r][x];
          shots0[i].c[k] = c0;
        }
      }
    }
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
const er = buildEarthrise(24, 4.8);
const lw = buildLavaWall(16, 3.2);
const cc = buildCommandCity(20, 3.6);
const hd = buildHeaderEdgeOrbitJpi(20, 3.6);

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
  console.log(fname, "size:", (data.svg.length / 1024).toFixed(1), "KB");

  const f0Svg = renderSingleFrameSvg(data.shots[0], data.palette, data.ground);
  const resvg0 = new Resvg(f0Svg, { fitTo: { mode: "width", value: 1200 } });
  fs.writeFileSync(path.join(artDir, `${prefix}_frame0.png`), resvg0.render().asPng());
}
console.log("Done in", Date.now() - t0, "ms");
