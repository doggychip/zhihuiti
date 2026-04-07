/**
 * Renderer — Stardew Valley style pixel art.
 * Camera at 2x zoom. No text labels on agents. Minimal clean UI.
 */

import type { CityAgent } from "./agent";
import type { SpriteAssets } from "./sprites";
import { TILE } from "./sprites";
import type { WorldMap } from "./worldgen";
import { TileType } from "./worldgen";
import type { CityEconomy } from "./economy";
import { BUILDING_EMOJI } from "./economy";

let assets: SpriteAssets | null = null;
let world: WorldMap | null = null;
let economy: CityEconomy | null = null;

let bgCanvas: HTMLCanvasElement | null = null;
let waterFrame = 0;
let waterTimer = 0;

/** The agent currently being hovered (set from main.ts). */
export let hoveredAgent: CityAgent | null = null;
export function setHovered(a: CityAgent | null) { hoveredAgent = a; }

/** Currently selected agent (click to pin). */
export let selectedAgent: CityAgent | null = null;
export function setSelected(a: CityAgent | null) { selectedAgent = a; }

export function setAssets(a: SpriteAssets) { assets = a; }
export function setWorld(w: WorldMap) { world = w; bgCanvas = null; }
export function setEconomy(e: CityEconomy) { economy = e; }

// ── Tile source rects ──
const GRASS_TILES = [
  { sx: 16, sy: 16 }, { sx: 0, sy: 80 }, { sx: 16, sy: 80 },
  { sx: 32, sy: 80 }, { sx: 16, sy: 96 },
];
const GRASS_FLOWER = { sx: 48, sy: 80 };
const GRASS_DARK = { sx: 64, sy: 80 };
const PATH_SRC = { sx: 0, sy: 16 };

const DECO_SRC: Record<string, { img: keyof SpriteAssets; sx: number; sy: number; sw: number; sh: number }> = {
  tree_green: { img: "biomeThings", sx: 0, sy: 0, sw: 32, sh: 32 },
  tree_pink:  { img: "biomeThings", sx: 32, sy: 0, sw: 32, sh: 32 },
  bush:       { img: "biomeThings", sx: 64, sy: 48, sw: 16, sh: 16 },
  rock:       { img: "biomeThings", sx: 48, sy: 32, sw: 16, sh: 16 },
  flower:     { img: "biomeThings", sx: 96, sy: 48, sw: 16, sh: 16 },
  mushroom:   { img: "biomeThings", sx: 0, sy: 48, sw: 16, sh: 16 },
  pumpkin:    { img: "biomeThings", sx: 48, sy: 48, sw: 16, sh: 16 },
  fence_h:    { img: "fences", sx: 0, sy: 0, sw: 16, sh: 16 },
  fence_v:    { img: "fences", sx: 0, sy: 16, sw: 16, sh: 16 },
  plant:      { img: "plants", sx: 48, sy: 0, sw: 16, sh: 16 },
};

// ── Background (cached) ──

function buildBackground(): HTMLCanvasElement {
  const w = world!;
  const c = document.createElement("canvas");
  c.width = w.cols * TILE;
  c.height = w.rows * TILE;
  const cx = c.getContext("2d")!;
  cx.imageSmoothingEnabled = false;

  if (!assets) return c;

  // Tiles
  for (let r = 0; r < w.rows; r++) {
    for (let col = 0; col < w.cols; col++) {
      const px = col * TILE;
      const py = r * TILE;
      const t = w.tiles[r][col];

      if (t === TileType.WATER) continue; // drawn live

      // Always draw grass base first
      const gi = ((r * 7 + col * 13) & 0x7fff) % GRASS_TILES.length;
      const gs = GRASS_TILES[gi];
      cx.drawImage(assets.grass, gs.sx, gs.sy, 16, 16, px, py, TILE, TILE);

      if (t === TileType.PATH) {
        cx.drawImage(assets.paths, PATH_SRC.sx, PATH_SRC.sy, 16, 16, px, py, TILE, TILE);
      } else if (t === TileType.GRASS_VAR1) {
        cx.drawImage(assets.grass, GRASS_FLOWER.sx, GRASS_FLOWER.sy, 16, 16, px, py, TILE, TILE);
      } else if (t === TileType.GRASS_VAR2) {
        cx.drawImage(assets.grass, GRASS_DARK.sx, GRASS_DARK.sy, 16, 16, px, py, TILE, TILE);
      }
    }
  }

  // Static decorations
  for (const d of w.decorations) {
    if (d.type === "house") {
      cx.drawImage(assets.walls, 0, 0, 80, 48, d.tx * TILE, d.ty * TILE, 80, 48);
      cx.drawImage(assets.roofs, 0, 0, 96, 48, d.tx * TILE - 8, d.ty * TILE - 40, 96, 48);
      cx.drawImage(assets.doors, 0, 0, 16, 32, d.tx * TILE + 32, d.ty * TILE + 16, 16, 32);
      continue;
    }
    const def = DECO_SRC[d.type];
    if (!def) continue;
    cx.drawImage(assets[def.img], def.sx, def.sy, def.sw, def.sh,
      d.tx * TILE, d.ty * TILE, def.sw, def.sh);
  }

  return c;
}

function drawWater(ctx: CanvasRenderingContext2D) {
  if (!assets || !world) return;
  const sx = waterFrame * 16;
  for (let r = 0; r < world.rows; r++) {
    for (let c = 0; c < world.cols; c++) {
      if (world.tiles[r][c] === TileType.WATER) {
        ctx.drawImage(assets.water, sx, 0, 16, 16, c * TILE, r * TILE, TILE, TILE);
      }
    }
  }
}

// ── Economy buildings ──

function drawBuildings(ctx: CanvasRenderingContext2D) {
  if (!economy) return;
  for (const b of economy.buildings) {
    const px = b.tx * TILE;
    const py = b.ty * TILE;

    const age = (performance.now() - b.buildTime) / 1000;
    if (age < 0.4) {
      const s = age / 0.4;
      ctx.save();
      ctx.translate(px + 8, py + 16);
      ctx.scale(s, s);
      ctx.translate(-(px + 8), -(py + 16));
    }

    // Use sprite-based buildings: roof tiles for houses, fences for farms, etc.
    // For now, use clean emoji on a subtle tile
    ctx.font = "14px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(BUILDING_EMOJI[b.type], px + 8, py + 8);

    if (age < 0.4) ctx.restore();
  }
}

// ── Agents ──

function drawAgent(ctx: CanvasRenderingContext2D, a: CityAgent) {
  if (!a.tintedSheet) return;

  const src = a.getSrcRect();
  // Draw at 1:1 in world coords (camera zoom handles magnification)
  const dx = Math.round(a.x - src.sw / 2);
  const dy = Math.round(a.y - src.sh / 2);

  // Selected indicator: small yellow circle under feet
  if (a === selectedAgent) {
    ctx.fillStyle = "rgba(255, 220, 50, 0.5)";
    ctx.beginPath();
    ctx.ellipse(a.x, a.y + src.sh / 2 - 2, 10, 4, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  // Aura pulse for high fitness
  if (a.fitness > 0.8) {
    const pulse = Math.abs(Math.sin(a.auraProgress * Math.PI));
    const r = 10 + pulse * 6;
    const grad = ctx.createRadialGradient(a.x, a.y + 4, 2, a.x, a.y + 4, r);
    grad.addColorStop(0, "rgba(255, 255, 255, 0.6)");
    grad.addColorStop(1, "rgba(255, 255, 255, 0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(a.x, a.y + 4, r, 0, Math.PI * 2);
    ctx.fill();
  }

  // Dormant: semi-transparent
  if (a.purging) {
    // Vortex / Ash effect
    const age = (performance.now() % 1000) / 1000;
    ctx.globalAlpha = 1 - age;
    ctx.save();
    ctx.translate(a.x, a.y);
    ctx.rotate(age * Math.PI * 4);
    ctx.scale(1 - age, 1 - age);
    ctx.drawImage(a.tintedSheet, src.sx, src.sy, src.sw, src.sh, -src.sw / 2, -src.sh / 2, src.sw, src.sh);
    ctx.restore();
    ctx.globalAlpha = 1;
    return;
  }

  // Kady Bridge Icon
  if (a.kadyState) {
    ctx.font = "10px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("🌉", a.x, a.y - src.sh / 2 - 12);
  }

  if (a.dormant) ctx.globalAlpha = 0.35;
  else if (!a.alive) ctx.globalAlpha = 0.4;

  ctx.drawImage(a.tintedSheet, src.sx, src.sy, src.sw, src.sh, dx, dy, src.sw, src.sh);
  ctx.globalAlpha = 1;

  // Dormant zzz (small)
  if (a.dormant) {
    ctx.font = "8px sans-serif";
    ctx.textAlign = "center";
    const bob = Math.sin(performance.now() / 400) * 3;
    ctx.fillText("💤", a.x + 10, a.y - src.sh / 2 - bob);
  }

  // Build hammer (small, brief)
  if (a.buildAnim > 0.3) {
    ctx.font = "10px sans-serif";
    ctx.textAlign = "center";
    ctx.globalAlpha = Math.min(1, a.buildAnim);
    ctx.fillText("🔨", a.x + 12, a.y - src.sh / 2 - 4);
    ctx.globalAlpha = 1;
  }
}

// ── Thought bubble (small, one at a time) ──

function drawThoughts(ctx: CanvasRenderingContext2D, agents: CityAgent[]) {
  // Only show the single most recent thought
  let best: CityAgent | null = null;
  let bestTime = 0;
  for (const a of agents) {
    if (a.thought && a.thought.alpha > 0 && a.thought.createdAt > bestTime) {
      best = a;
      bestTime = a.thought.createdAt;
    }
  }
  if (!best?.thought) return;

  const a = best;
  const t = a.thought!;
  const maxW = 140;
  const pad = 5;
  const lh = 11;

  ctx.save();
  ctx.globalAlpha = t.alpha;
  ctx.font = "8px 'SF Mono', monospace";
  ctx.textAlign = "left";

  // Word wrap
  const words = t.text.split(" ");
  const lines: string[] = [];
  let cur = "";
  for (const w of words) {
    const test = cur ? cur + " " + w : w;
    if (ctx.measureText(test).width > maxW - pad * 2) {
      if (cur) lines.push(cur);
      cur = w;
    } else cur = test;
  }
  if (cur) lines.push(cur);
  if (lines.length > 3) lines.length = 3; // cap at 3 lines

  const bw = maxW;
  const bh = lines.length * lh + pad * 2;
  const bx = Math.round(a.x - bw / 2);
  const by = Math.round(a.y - 48 / 2 - 8 - bh);

  // Bubble
  ctx.fillStyle = "rgba(255,248,228,0.93)";
  ctx.strokeStyle = "rgba(139,119,80,0.5)";
  ctx.lineWidth = 0.5;
  roundRect(ctx, bx, by, bw, bh, 4);
  ctx.fill();
  ctx.stroke();

  // Pointer
  ctx.beginPath();
  ctx.moveTo(a.x - 3, by + bh);
  ctx.lineTo(a.x, by + bh + 4);
  ctx.lineTo(a.x + 3, by + bh);
  ctx.fillStyle = "rgba(255,248,228,0.93)";
  ctx.fill();

  // Text
  ctx.fillStyle = "#3b2f1e";
  for (let i = 0; i < lines.length; i++) {
    ctx.fillText(lines[i], bx + pad, by + pad + 8 + i * lh);
  }
  ctx.restore();
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

// ── Main render ──

export const ZOOM = 2;

export function render(
  ctx: CanvasRenderingContext2D,
  viewW: number,
  viewH: number,
  agents: CityAgent[],
  dt: number,
) {
  ctx.imageSmoothingEnabled = false;

  waterTimer += dt;
  if (waterTimer > 0.5) { waterTimer -= 0.5; waterFrame = (waterFrame + 1) % 4; }

  // Apply camera zoom
  ctx.save();
  ctx.scale(ZOOM, ZOOM);

  // World-space dimensions
  const ww = world ? world.cols * TILE : viewW;
  const wh = world ? world.rows * TILE : viewH;

  // Green base
  ctx.fillStyle = "#5a8f29";
  ctx.fillRect(0, 0, ww, wh);

  // Water (animated)
  drawWater(ctx);

  // Static background (cached)
  if (!bgCanvas && assets && world) bgCanvas = buildBackground();
  if (bgCanvas) ctx.drawImage(bgCanvas, 0, 0);

  // Economy buildings
  drawBuildings(ctx);

  // Agents sorted by Y
  const sorted = [...agents].sort((a, b) => a.y - b.y);
  for (const a of sorted) drawAgent(ctx, a);

  // One thought bubble
  drawThoughts(ctx, agents);

  ctx.restore(); // undo zoom
}

// ── HUD (DOM, styled in HTML) ──

export function updateHUD(dayCount: number, agentCount: number, buildingCount: number, econ: CityEconomy | null) {
  const hud = document.getElementById("hud");
  if (!hud) return;

  let html = `<div class="hud-title">🌿 Zhihuiti City</div>`;
  html += `<div class="hud-row"><span class="hud-label">Day</span><span class="hud-val">${dayCount}</span></div>`;
  html += `<div class="hud-row"><span class="hud-label">Agents</span><span class="hud-val">${agentCount}</span></div>`;
  html += `<div class="hud-row"><span class="hud-label">Buildings</span><span class="hud-val">${buildingCount}</span></div>`;

  if (econ) {
    const lb = econ.getLeaderboard().slice(0, 3);
    if (lb.length > 0) {
      html += `<div class="hud-divider"></div>`;
      html += `<div class="hud-subtitle">Top Builders</div>`;
      const medals = ["🥇", "🥈", "🥉"];
      for (let i = 0; i < lb.length; i++) {
        html += `<div class="hud-row"><span class="hud-label">${medals[i]} ${lb[i].id.slice(0, 6)}</span>`
              + `<span class="hud-val">${lb[i].stats.buildingsBuilt} built</span></div>`;
      }
    }
  }

  // Triple Evolution HUD
  if (econ && econ.funds.length > 0) {
    html += `<div class="hud-divider"></div>`;
    html += `<div class="hud-subtitle">Community Funds</div>`;
    for (const f of econ.funds.slice(0, 2)) {
      const progress = Math.round((f.current / f.goal) * 100);
      html += `<div class="hud-row"><span class="hud-label">Park @ ${f.tx},${f.ty}</span><span class="hud-val">${progress}%</span></div>`;
    }
  }

  hud.innerHTML = html;
}
