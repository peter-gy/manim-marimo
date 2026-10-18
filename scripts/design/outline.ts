// Outline text in a font file, so the wordmark renders without the font.
import { readFile } from "node:fs/promises";
import opentype from "opentype.js";

export interface Outline {
  // SVG path data in font units with y pointing down, shifted so the
  // outline's bounding box starts at the origin.
  d: string;
  width: number;
  height: number;
  // The baseline's distance below the top of the bounding box.
  baseline: number;
  // The font's em, in the same units.
  em: number;
}

export const loadFont = async (file: string): Promise<opentype.Font> =>
  opentype.parse((await readFile(file)).buffer as ArrayBuffer);

// The outline of `text` set in `font`, with kerning.
export const outline = (font: opentype.Font, text: string): Outline => {
  const em = font.unitsPerEm;
  const box = font.getPath(text, 0, 0, em).getBoundingBox();
  return {
    d: font.getPath(text, -box.x1, -box.y1, em).toPathData(2),
    width: box.x2 - box.x1,
    height: box.y2 - box.y1,
    baseline: -box.y1,
    em,
  };
};
