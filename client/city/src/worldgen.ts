/**
 * World generation — proper city grid with roads, zones, and decorations.
 * Roads form a grid. Buildings go next to roads. Trees fill empty grass.
 */

import { TILE } from "./sprites";

export const TileType = {
  GRASS: 0,
  GRASS_VAR1: 1,
  GRASS_VAR2: 2,
  WATER: 3,
  PATH: 5,
} as const;
export type TileType = (typeof TileType)[keyof typeof TileType];

export type DecoType =
  | "tree_green" | "tree_pink" | "bush" | "rock" | "flower"
  | "mushroom" | "pumpkin" | "fence_h" | "fence_v" | "house" | "plant";

export interface Decoration {
  type: DecoType;
  tx: number;
  ty: number;
}

export interface WorldMap {
  cols: number;
  rows: number;
  tiles: TileType[][];
  decorations: Decoration[];
  /** All road tile coords as "tx,ty" for fast lookup. */
  roadSet: Set<string>;
  /** Grass tiles adjacent to a road — valid build sites. */
  roadAdjacentGrass: { tx: number; ty: number }[];
}

function mulberry32(a: number) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

/**
 * Generate a world sized in WORLD tiles (not screen pixels).
 * The canvas will render at 2x zoom, so we only need half the tiles.
 */
export function generateWorld(viewW: number, viewH: number): WorldMap {
  // World is sized to fill the viewport at 2x zoom
  const cols = Math.ceil(viewW / (TILE * 2)) + 2;
  const rows = Math.ceil(viewH / (TILE * 2)) + 2;
  const rand = mulberry32(42);

  // 1. Fill with grass
  const tiles: TileType[][] = [];
  for (let r = 0; r < rows; r++) {
    tiles[r] = [];
    for (let c = 0; c < cols; c++) {
      const v = rand();
      tiles[r][c] = v < 0.06 ? TileType.GRASS_VAR1
                  : v < 0.12 ? TileType.GRASS_VAR2
                  : TileType.GRASS;
    }
  }

  // 2. Water border (2 tiles)
  const W = 2;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (r < W || r >= rows - W || c < W || c >= cols - W) {
        tiles[r][c] = TileType.WATER;
      }
    }
  }

  // 3. Road grid — horizontal every 8 rows, vertical every 10 cols
  //    Roads are 2 tiles wide for a nice look.
  const roadSet = new Set<string>();
  const hRoads: number[] = [];
  const vRoads: number[] = [];

  for (let r = W + 4; r < rows - W - 2; r += 8) {
    hRoads.push(r);
    for (let c = W; c < cols - W; c++) {
      tiles[r][c] = TileType.PATH;
      tiles[r + 1][c] = TileType.PATH;
      roadSet.add(`${c},${r}`);
      roadSet.add(`${c},${r + 1}`);
    }
  }
  for (let c = W + 5; c < cols - W - 2; c += 10) {
    vRoads.push(c);
    for (let r = W; r < rows - W; r++) {
      tiles[r][c] = TileType.PATH;
      tiles[r][c + 1] = TileType.PATH;
      roadSet.add(`${c},${r}`);
      roadSet.add(`${c + 1},${r}`);
    }
  }

  // 4. Find all grass tiles adjacent to a road (build lots)
  const roadAdjacentGrass: { tx: number; ty: number }[] = [];
  const buildableSet = new Set<string>();
  for (let r = W + 1; r < rows - W - 1; r++) {
    for (let c = W + 1; c < cols - W - 1; c++) {
      if (roadSet.has(`${c},${r}`)) continue;
      const t = tiles[r][c];
      if (t !== TileType.GRASS && t !== TileType.GRASS_VAR1 && t !== TileType.GRASS_VAR2) continue;
      // Check if any neighbor is road
      const adj = [`${c-1},${r}`, `${c+1},${r}`, `${c},${r-1}`, `${c},${r+1}`];
      if (adj.some(k => roadSet.has(k))) {
        roadAdjacentGrass.push({ tx: c, ty: r });
        buildableSet.add(`${c},${r}`);
      }
    }
  }

  // 5. Decorations — pre-place worldgen houses along roads, trees on grass
  const decorations: Decoration[] = [];
  const occupied = new Set<string>();

  // Place worldgen houses at intersections and along main roads
  if (hRoads.length > 0 && vRoads.length > 0) {
    // Houses near first few intersections
    for (const hr of hRoads) {
      for (const vc of vRoads) {
        // Place house 2 tiles above the road, offset from intersection
        const spots = [
          { tx: vc + 3, ty: hr - 2 },
          { tx: vc - 2, ty: hr + 3 },
          { tx: vc + 3, ty: hr + 3 },
          { tx: vc - 2, ty: hr - 2 },
        ];
        for (const s of spots) {
          if (rand() > 0.4) continue;
          if (s.tx < W + 1 || s.ty < W + 1 || s.tx >= cols - W - 2 || s.ty >= rows - W - 2) continue;
          if (roadSet.has(`${s.tx},${s.ty}`)) continue;
          if (occupied.has(`${s.tx},${s.ty}`)) continue;
          decorations.push({ type: "house", tx: s.tx, ty: s.ty });
          // Block 3x2 area
          for (let dy = 0; dy < 2; dy++)
            for (let dx = 0; dx < 3; dx++)
              occupied.add(`${s.tx + dx},${s.ty + dy}`);
        }
      }
    }
  }

  // Trees on non-road, non-adjacent grass
  for (let r = W + 1; r < rows - W - 2; r += 3) {
    for (let c = W + 1; c < cols - W - 2; c += 3) {
      if (roadSet.has(`${c},${r}`) || buildableSet.has(`${c},${r}`)) continue;
      if (occupied.has(`${c},${r}`)) continue;
      const t = tiles[r][c];
      if (t === TileType.WATER || t === TileType.PATH) continue;

      const v = rand();
      if (v < 0.25) {
        decorations.push({ type: "tree_green", tx: c, ty: r });
        occupied.add(`${c},${r}`);
        occupied.add(`${c + 1},${r}`);
      } else if (v < 0.35) {
        decorations.push({ type: "tree_pink", tx: c, ty: r });
        occupied.add(`${c},${r}`);
        occupied.add(`${c + 1},${r}`);
      } else if (v < 0.42) {
        decorations.push({ type: "flower", tx: c, ty: r });
      } else if (v < 0.47) {
        decorations.push({ type: "rock", tx: c, ty: r });
      } else if (v < 0.50) {
        decorations.push({ type: "bush", tx: c, ty: r });
      }
    }
  }

  return { cols, rows, tiles, decorations, roadSet, roadAdjacentGrass };
}
