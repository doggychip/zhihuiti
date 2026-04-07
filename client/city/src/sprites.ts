/** Sprite sheet loader and atlas definitions for Sprout Lands assets. */

const BASE_PATH = "/assets/sprout-lands";

/** Load an image and return a promise. */
function loadImg(path: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = path;
  });
}

/** All loaded sprite sheet images. */
export interface SpriteAssets {
  character: HTMLImageElement;
  grass: HTMLImageElement;
  water: HTMLImageElement;
  fences: HTMLImageElement;
  house: HTMLImageElement;
  biomeThings: HTMLImageElement;
  plants: HTMLImageElement;
  hills: HTMLImageElement;
  furniture: HTMLImageElement;
  paths: HTMLImageElement;
  doors: HTMLImageElement;
  roofs: HTMLImageElement;
  walls: HTMLImageElement;
}

export async function loadAllSprites(): Promise<SpriteAssets> {
  const [
    character, grass, water, fences, house, biomeThings,
    plants, hills, furniture, paths, doors, roofs, walls,
  ] = await Promise.all([
    loadImg(`${BASE_PATH}/Characters/Basic Charakter Spritesheet.png`),
    loadImg(`${BASE_PATH}/Tilesets/Grass.png`),
    loadImg(`${BASE_PATH}/Tilesets/Water.png`),
    loadImg(`${BASE_PATH}/Tilesets/Fences.png`),
    loadImg(`${BASE_PATH}/Tilesets/Wooden House.png`),
    loadImg(`${BASE_PATH}/Objects/Basic Grass Biom things 1.png`),
    loadImg(`${BASE_PATH}/Objects/Basic Plants.png`),
    loadImg(`${BASE_PATH}/Tilesets/Hills.png`),
    loadImg(`${BASE_PATH}/Objects/Basic Furniture.png`),
    loadImg(`${BASE_PATH}/Objects/Paths.png`),
    loadImg(`${BASE_PATH}/Tilesets/Doors.png`),
    loadImg(`${BASE_PATH}/Tilesets/Wooden_House_Roof_Tilset.png`),
    loadImg(`${BASE_PATH}/Tilesets/Wooden_House_Walls_Tilset.png`),
  ]);
  return {
    character, grass, water, fences, house, biomeThings,
    plants, hills, furniture, paths, doors, roofs, walls,
  };
}

/*
 * Character spritesheet layout (192x192, 48x48 per frame):
 *   Row 0 (y=0):   walk down  — 4 frames
 *   Row 1 (y=48):  walk up    — 4 frames
 *   Row 2 (y=96):  walk right — 4 frames
 *   Row 3 (y=144): walk left  — 4 frames (mirrored)
 *
 * Grass tileset (176x112, 16x16 tiles):
 *   Various grass tiles — we'll use a few for variety
 *
 * Water tileset (64x16, 16x16 tiles):
 *   4 animation frames for water
 *
 * Biome things (144x80, 16x16 tiles):
 *   Trees, flowers, rocks, mushrooms, bushes
 *
 * Fences (64x64, 16x16 tiles):
 *   Various fence segments
 */

/** Character frame size */
export const CHAR_W = 48;
export const CHAR_H = 48;

/** Direction → spritesheet row mapping */
export const DIR_ROW: Record<string, number> = {
  down: 0,
  up: 1,
  right: 2,
  left: 3,
};

/** Tile size used for the world grid */
export const TILE = 16;

/**
 * Create a tinted copy of the character spritesheet for a specific role.
 * We overlay the role color at low opacity to tint the character.
 */
export function createTintedCharacter(
  base: HTMLImageElement,
  color: string,
): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = base.width;
  c.height = base.height;
  const cx = c.getContext("2d")!;

  // Draw original
  cx.drawImage(base, 0, 0);

  // Overlay color using multiply-like blend
  cx.globalCompositeOperation = "source-atop";
  cx.fillStyle = color;
  cx.globalAlpha = 0.35;
  cx.fillRect(0, 0, c.width, c.height);

  // Restore luminance from original to keep shading
  cx.globalCompositeOperation = "destination-in";
  cx.globalAlpha = 1;
  cx.drawImage(base, 0, 0);

  return c;
}
