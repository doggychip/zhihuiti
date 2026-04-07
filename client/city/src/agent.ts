/** Visual agent sprite that wanders the city canvas. */

import { CHAR_W, CHAR_H, DIR_ROW, createTintedCharacter } from "./sprites";
import type { SpriteAssets } from "./sprites";

export const ROLE_COLORS: Record<string, string> = {
  researcher: "#4fc3f7",
  analyst: "#ab47bc",
  trader: "#ffa726",
  coder: "#66bb6a",
  strategist: "#ef5350",
  coordinator: "#42a5f5",
  auditor: "#78909c",
  causal_reasoner: "#ec407a",
  mutualist: "#fdd835",
  darwinian: "#f44336",
  hybrid: "#8e24aa",
  critic: "#ffeb3b",
  cold_logic: "#00bcd4",
  warm_soul: "#ff5722",
  custom: "#9e9e9e",
};

const ROLE_EMOJI: Record<string, string> = {
  researcher: "🔬",
  analyst: "📊",
  trader: "💹",
  coder: "💻",
  strategist: "♟️",
  coordinator: "🔗",
  auditor: "🔍",
  causal_reasoner: "🧠",
  mutualist: "🤝",
  darwinian: "🐺",
  hybrid: "🧬",
  critic: "🎬",
  cold_logic: "🤖",
  warm_soul: "❤️",
  custom: "⚙️",
};

export interface ThoughtBubble {
  text: string;
  alpha: number;
  createdAt: number;
}

export type Direction = "down" | "up" | "left" | "right";

/** What the agent is currently trying to do. */
export type AgentGoal =
  | { type: "wander" }
  | { type: "build"; tx: number; ty: number }
  | { type: "earn"; tx: number; ty: number }  // walk to a building to earn
  | { type: "dormant" };

/** Cache of tinted character canvases per role. */
const _tintCache = new Map<string, HTMLCanvasElement>();

export class CityAgent {
  id: string;
  role: string;
  alive: boolean;
  score: number;
  color: string;
  emoji: string;

  // economy
  budget: number;
  dormant: boolean = false;
  dormantTimer: number = 0; // seconds remaining
  goal: AgentGoal = { type: "wander" };

  // position & movement (in world-pixel coordinates)
  x: number;
  y: number;
  targetX: number;
  targetY: number;
  speed: number;

  // sprite animation
  dir: Direction = "down";
  animFrame: number = 0;
  animTimer: number = 0;
  moving: boolean = false;
  tintedSheet: HTMLCanvasElement | null = null;

  // visual state
  thought: ThoughtBubble | null = null;
  buildAnim: number = 0; // 0-1 progress of build animation (0=none)
  fitness: number = 0; // Relative role fitness (0-1)
  auraProgress: number = 0; // Visual aura pulse

  // Triple Evolution: Finance & Lineage
  debt: number = 0;
  parentIds: string[] = [];
  purging: boolean = false; // Trigger "vortex/ash" effect
  kadyState: boolean = false; // Interacting with Kady Bridge

  // Evolutionary Integrity Properties
  truthfulness: number = 1.0; // 0.0 to 1.0
  reflectionState: boolean = false;
  recentThoughts: string[] = [];

  // Hybrid behavioral state
  hybridState: "cooperative" | "competitive" = "cooperative";

  constructor(
    data: { id: string; role: string; avg_score: number; alive: number; budget: number; parentIds?: string[] },
    canvasW: number,
    canvasH: number,
  ) {
    this.id = data.id;
    this.role = data.role;
    this.alive = data.alive === 1;
    this.score = data.avg_score;
    this.budget = data.budget;
    this.parentIds = data.parentIds ?? [];
    this.color = ROLE_COLORS[data.role] ?? "#9e9e9e";
    this.emoji = ROLE_EMOJI[data.role] ?? "⚙️";

    const margin = 80;
    this.x = margin + Math.random() * (canvasW - margin * 2);
    this.y = margin + Math.random() * (canvasH - margin * 2);
    this.targetX = this.x;
    this.targetY = this.y;
    this.speed = 30 + Math.random() * 25;
    this.animFrame = Math.floor(Math.random() * 4);
  }

  initSprite(assets: SpriteAssets) {
    if (!_tintCache.has(this.role)) {
      _tintCache.set(this.role, createTintedCharacter(assets.character, this.color));
    }
    this.tintedSheet = _tintCache.get(this.role)!;
  }

  /** Pick a random road tile to walk to. Falls back to random position. */
  pickRoadTarget(roadTiles: { tx: number; ty: number }[]) {
    if (roadTiles.length === 0) return;
    const t = roadTiles[Math.floor(Math.random() * roadTiles.length)];
    this.targetX = t.tx * 16 + 8;
    this.targetY = t.ty * 16 + 8;
  }

  /** Legacy fallback. */
  pickTarget(_w: number, _h: number) {
    // no-op — use pickRoadTarget instead
  }

  /** Move to a specific tile position (center of tile). */
  moveToTile(tx: number, ty: number) {
    this.targetX = tx * 16 + 8;
    this.targetY = ty * 16 + 8;
  }

  update(dt: number): boolean {
    // Reflection — must generate corrective intent
    if (this.reflectionState) {
      this.moving = false;
      this._fadeThought();
      return false;
    }

    // Dormant — count down, don't move
    if (this.dormant) {
      this.dormantTimer -= dt;
      if (this.dormantTimer <= 0) {
        this.dormant = false;
        this.budget = 10;
        this.goal = { type: "wander" };
      }
      this.moving = false;
      // still fade thoughts
      this._fadeThought();
      return false;
    }

    // Build animation tick
    if (this.buildAnim > 0) {
      this.buildAnim = Math.max(0, this.buildAnim - dt * 1.5); // ~0.66s
    }

    const dx = this.targetX - this.x;
    const dy = this.targetY - this.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    if (dist < 2) {
      this.moving = false;
      return true; // arrived
    }

    this.moving = true;

    if (Math.abs(dx) > Math.abs(dy)) {
      this.dir = dx > 0 ? "right" : "left";
    } else {
      this.dir = dy > 0 ? "down" : "up";
    }

    this.animTimer += dt;
    if (this.animTimer > 0.15) {
      this.animTimer -= 0.15;
      this.animFrame = (this.animFrame + 1) % 4;
    }

    const step = Math.min(this.speed * dt, dist);
    this.x += (dx / dist) * step;
    this.y += (dy / dist) * step;

    this._fadeThought();

    // Pulse / Aura update (for high fitness)
    this.auraProgress = (this.auraProgress + dt) % 2.0; // 2s cycle

    // Hybrid role logic
    if (this.role === "hybrid") {
      // Switch between cooperative and competitive based on random noise or local stats (simplified for now)
      if (Math.random() < 0.05 * dt) {
        this.hybridState = this.hybridState === "cooperative" ? "competitive" : "cooperative";
      }
    }

    return false;
  }

  private _fadeThought() {
    if (this.thought) {
      const age = (performance.now() - this.thought.createdAt) / 1000;
      if (age > 6) {
        this.thought = null;
      } else if (age > 4) {
        this.thought.alpha = 1 - (age - 4) / 2;
      }
    }
  }

  getSrcRect(): { sx: number; sy: number; sw: number; sh: number } {
    const row = DIR_ROW[this.dir] ?? 0;
    const col = this.moving ? this.animFrame : 0;
    return {
      sx: col * CHAR_W,
      sy: row * CHAR_H,
      sw: CHAR_W,
      sh: CHAR_H,
    };
  }

  showThought(text: string) {
    this.thought = { text, alpha: 1, createdAt: performance.now() };
  }

  /** Enter reflection state (Circuit Breaker). */
  enterReflection() {
    this.reflectionState = true;
    this.dormant = false; // instead of dormant
    this.moving = false;
    this.goal = { type: "dormant" };
  }

  /** Exit reflection state. */
  exitReflection() {
    this.reflectionState = false;
    this.budget = 10;
    this.goal = { type: "wander" };
  }

  /** Enter dormant state (circuit breaker). */
  goDormant() {
    this.enterReflection();
  }
}
