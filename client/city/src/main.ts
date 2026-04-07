import { CityAgent } from "./agent";
import { fetchAgents, fetchStats } from "./api";
import { loadAllSprites, TILE, type SpriteAssets } from "./sprites";
import { generateWorld, type WorldMap } from "./worldgen";
import { render, updateHUD, setAssets, setWorld, setEconomy, setHovered, setSelected, ZOOM } from "./render";
import { startThoughtLoop } from "./think";
import { CityEconomy, preferredBuilding, BUILDING_COST } from "./economy";

const canvas = document.getElementById("city") as HTMLCanvasElement;
const ctx = canvas.getContext("2d")!;
const tooltip = document.getElementById("tooltip") as HTMLDivElement;

let W = 0;
let H = 0;
let agents: CityAgent[] = [];
// Stats just triggers HUD refresh on load
let sprites: SpriteAssets | null = null;
let worldMap: WorldMap | null = null;
const econ = new CityEconomy();
setEconomy(econ);

/** Pre-computed list of road tile pixel centers for agent pathfinding. */
let roadTiles: { tx: number; ty: number }[] = [];

/** Day counter — increments every 60s of real time. */
let dayTimer = 0;
let dayCount = 1;

function resize() {
  W = window.innerWidth;
  H = window.innerHeight;
  canvas.width = W * devicePixelRatio;
  canvas.height = H * devicePixelRatio;
  canvas.style.width = W + "px";
  canvas.style.height = H + "px";
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);

  worldMap = generateWorld(W, H);
  setWorld(worldMap);
  econ.setWorld(worldMap);

  // Build road tile list from worldMap.roadSet
  roadTiles = [];
  for (const key of worldMap.roadSet) {
    const [tx, ty] = key.split(",").map(Number);
    roadTiles.push({ tx, ty });
  }
}

window.addEventListener("resize", resize);
resize();

// ── Hover / click ──

canvas.addEventListener("mousemove", (e) => {
  // Convert screen coords to world coords (accounting for zoom)
  const wx = e.clientX / ZOOM;
  const wy = e.clientY / ZOOM;

  let closest: CityAgent | null = null;
  let closestDist = 20; // hit radius in world pixels
  for (const a of agents) {
    const d = Math.hypot(a.x - wx, a.y - wy);
    if (d < closestDist) { closestDist = d; closest = a; }
  }

  setHovered(closest);

  if (closest) {
    tooltip.style.display = "block";
    tooltip.style.left = (e.clientX + 12) + "px";
    tooltip.style.top = (e.clientY - 8) + "px";
    tooltip.innerHTML = `<b>${closest.role}</b> ${closest.emoji}<br>`
      + `ID: ${closest.id.slice(0, 8)}<br>`
      + `Budget: $${Math.round(closest.budget)}<br>`
      + `Score: ${closest.score.toFixed(2)}<br>`
      + `${closest.dormant ? "💤 Dormant" : closest.goal.type}`;
    canvas.style.cursor = "pointer";
  } else {
    tooltip.style.display = "none";
    canvas.style.cursor = "default";
  }
});

canvas.addEventListener("mouseleave", () => {
  tooltip.style.display = "none";
  setHovered(null);
});

canvas.addEventListener("click", (e) => {
  const wx = e.clientX / ZOOM;
  const wy = e.clientY / ZOOM;
  let closest: CityAgent | null = null;
  let closestDist = 20;
  for (const a of agents) {
    const d = Math.hypot(a.x - wx, a.y - wy);
    if (d < closestDist) { closestDist = d; closest = a; }
  }
  setSelected(closest);
});

// ── Agent loading ──

async function loadAgents() {
  try {
    const data = await fetchAgents();
    agents = data.map((d) => new CityAgent(d, W, H));
    // Place agents on road tiles
    for (const a of agents) {
      if (roadTiles.length > 0) {
        const rt = roadTiles[Math.floor(Math.random() * roadTiles.length)];
        a.x = rt.tx * TILE + 8;
        a.y = rt.ty * TILE + 8;
      }
      a.pickRoadTarget(roadTiles);
      if (sprites) a.initSprite(sprites);
    }
  } catch (e) {
    console.error("Failed to load agents:", e);
  }
}

async function loadStats() {
  try {
    await fetchStats();
    refreshHUD();
  } catch (e) {
    console.error("Failed to load stats:", e);
  }
}

function refreshHUD() {
  const alive = agents.filter(a => a.alive && !a.dormant).length;
  updateHUD(dayCount, alive, econ.buildings.length, econ);
}

// ── Economy simulation ──

let buildTimer = 3;
let earnTimer = 0;
const BUILD_INTERVAL = 4;
const EARN_INTERVAL = 2;

function economyTick(dt: number) {
  buildTimer -= dt;
  if (buildTimer <= 0) {
    buildTimer = BUILD_INTERVAL;
    runBuildPhase();
  }

  earnTimer -= dt;
  if (earnTimer <= 0) {
    earnTimer = EARN_INTERVAL;
    econ.earnTick(agents);

    for (const a of agents) {
      if (!a.dormant && a.alive && a.budget <= 0) {
        a.goDormant();
        a.showThought("💤 预算归零...");
        const s = econ.agentStats.get(a.id);
        if (s) s.timesDormant++;
        else econ.agentStats.set(a.id, { buildingsBuilt: 0, totalEarned: 0, timesDormant: 1 });
      }
    }

  // update agents with fitness info for visual effects
  for (const a of agents) {
    const roleFit = econ.roleFitness.get(a.role) ?? 0;
    // Normalize fitness (simple heuristic: 100 budget = 1.0 fitness)
    a.fitness = Math.min(1, roleFit / 100);
  }

  refreshHUD();
}

  // Day counter
  dayTimer += dt;
  if (dayTimer >= 60) { dayTimer -= 60; dayCount++; refreshHUD(); }
}

function runBuildPhase() {
  const alive = agents.filter(a => a.alive && !a.dormant);

  for (const a of alive) {
    const pref = preferredBuilding(a.role);
    const cost = BUILDING_COST[pref];

    if (a.budget >= cost) {
      const site = econ.findBuildSite(a);
      if (site) {
        a.goal = { type: "build", tx: site.tx, ty: site.ty };
        a.moveToTile(site.tx, site.ty);
        econ.submitBuildIntent(a, site.tx, site.ty, pref);
      }
    } else {
      // Go earn near a building
      if (econ.buildings.length > 0) {
        const b = econ.buildings[Math.floor(Math.random() * econ.buildings.length)];
        a.goal = { type: "earn", tx: b.tx, ty: b.ty };
        a.moveToTile(b.tx, b.ty);
      } else {
        a.goal = { type: "wander" };
        a.pickRoadTarget(roadTiles);
      }
    }
  }

  const result = econ.resolveBuildIntents(agents);

  for (const id of result.built) {
    const a = agents.find(ag => ag.id === id);
    if (a) { a.buildAnim = 1; a.goal = { type: "wander" }; }
  }
  for (const id of result.rejected) {
    const a = agents.find(ag => ag.id === id);
    if (a) {
      a.showThought("😤 被抢了！");
      a.goal = { type: "wander" };
      a.pickRoadTarget(roadTiles);
    }
  }
}

// ── Game loop ──

let lastTime = performance.now();

function frame(now: number) {
  const dt = Math.min((now - lastTime) / 1000, 0.1);
  lastTime = now;

  for (const a of agents) {
    const arrived = a.update(dt);
    if (arrived && !a.dormant) {
      if (a.goal.type === "wander") {
        a.pickRoadTarget(roadTiles);
      }
    }
  }

  economyTick(dt);
  render(ctx, W, H, agents, dt);
  requestAnimationFrame(frame);
}

// ── Bootstrap ──

async function init() {
  try {
    sprites = await loadAllSprites();
    setAssets(sprites);
  } catch (e) {
    console.error("Failed to load sprites:", e);
  }

  await Promise.all([loadAgents(), loadStats()]);

  if (sprites) {
    for (const a of agents) a.initSprite(sprites);
  }

  startThoughtLoop(() => agents, econ, 4000);
  requestAnimationFrame(frame);
  setInterval(loadStats, 30000);
}

init();
