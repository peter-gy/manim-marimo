// Generate manim-marimo's brand assets. Usage: pixi run design
//
// The mark is marimo's looped circle drawn by rotating vectors, the default
// path of examples/fourier.py, which mark.py reads from the notebook. The
// wordmark is "manim-marimo" set in CMU Serif.
//
//   docs/public/brand/       marks, icons, wordmarks, and lockups as SVG and
//                            PNG, the Open Graph image, and the brand board
//   docs/public/favicon.svg  the icon on the scene's plate
//   docs/public/apple-touch-icon.png
//   docs/.vitepress/theme/brand.ts  the mark's vectors and the wordmark's
//                                   contours, which the home page's hero draws
//   examples/studio/*/animation/fonts/         CMU faces the scenes register
//   examples/studio/*/animation/assets/fonts/  CMU faces the pages load
import { $ } from "bun";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { chromium, type Page } from "playwright";
import subsetFont from "subset-font";

import { loadFont, outline, type Outline } from "./outline.ts";

const here = import.meta.dir;
const root = resolve(here, "../..");
const brand = join(root, "docs/public/brand");
const face = (name: string) => join(here, "node_modules/computer-modern/fonts", `${name}.ttf`);

export const themes = {
  dark: { page: "#11161c", ink: "#ececec", muted: "#848b94", ring: "#83c167", vector: "#ececec", pen: "#ffff00" },
  light: { page: "#ffffff", ink: "#16191d", muted: "#69717a", ring: "#4f7a3a", vector: "#16191d", pen: "#b8860b" },
} as const;
type Theme = keyof typeof themes;

// [frequency, real, imaginary] rows, the longest vector first. The path they
// draw is one unit wide.
const terms = JSON.parse(await $`python ${join(here, "mark.py")}`.quiet().text()) as [number, number, number][];
const serif = await loadFont(face("cmu-serif-500-roman"));
const wordmark = outline(serif, "manim-marimo");
// CMU Serif's OS/2 table predates the x-height field, so the "x" measures it.
const xHeight = serif.charToGlyph("x").getBoundingBox().y2;

// The pen at phase t, in SVG coordinates (y down) scaled by `unit`.
const pen = (t: number, unit: number): [number, number] => {
  let x = 0;
  let y = 0;
  for (const [k, re, im] of terms) {
    const a = 2 * Math.PI * k * t;
    x += re * Math.cos(a) - im * Math.sin(a);
    y += re * Math.sin(a) + im * Math.cos(a);
  }
  return [x * unit, -y * unit];
};

// Strokes scale with the mark: hairlines for display and lockups, and a bolder
// icon for favicons, where the loops merge into one ring. The head is
// `head` stroke widths long and `wing` of its length wide on each side.
const weights = {
  fine: { ring: 0.011, vector: 0.012, pen: 0.036, head: 5.5, wing: 0.34 },
  medium: { ring: 0.022, vector: 0.022, pen: 0.05, head: 4.6, wing: 0.38 },
  bold: { ring: 0.04, vector: 0.042, pen: 0.075, head: 3.6, wing: 0.44 },
};
type Weight = keyof typeof weights;
// The ring's bounding box in path units, so the mark centers on what it draws
// rather than on the vectors' origin.
const box = (() => {
  const points = Array.from({ length: 721 }, (_, i) => pen(i / 720, 1));
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  return { x: (Math.min(...xs) + Math.max(...xs)) / 2, y: (Math.min(...ys) + Math.max(...ys)) / 2, size: Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)) };
})();
// A standalone mark leaves this share of its side as margin on each edge.
// Lockups place the ring itself, with no margin.
const margin = 0.11;

// The mark centered on (x, y), `side` across: the ring the vectors draw, the
// vector from the center to the pen as it closes the path, and the pen.
// Without a theme, the parts take their colors from a style sheet.
const markBody = (theme: Theme | null, weight: Weight, side: number, cx: number, cy: number, inset = margin) => {
  const unit = (side * (1 - 2 * inset)) / box.size;
  const x = cx - box.x * unit;
  const y = cy - box.y * unit;
  const w = weights[weight];
  const paint = (attribute: "fill" | "stroke", part: "ring" | "vector" | "pen") =>
    theme ? ` ${attribute}="${themes[theme][part]}"` : "";
  const at = ([px, py]: [number, number]) => `${(px + x).toFixed(2)} ${(py + y).toFixed(2)}`;
  const ring = Array.from({ length: 721 }, (_, i) => `${i ? "L" : "M"}${at(pen(i / 720, unit))}`).join("");
  const [px, py] = pen(0, unit);
  const reachPen = Math.hypot(px, py);
  const stop = 1 - (w.pen * unit) / reachPen;
  const tip: [number, number] = [px * stop, py * stop];
  const length = Math.hypot(...tip);
  const [ux, uy] = [tip[0] / length, tip[1] / length];
  const head = Math.min(0.3 * length, w.vector * unit * w.head);
  const base: [number, number] = [tip[0] - ux * head, tip[1] - uy * head];
  const wing = head * w.wing;
  return (
    `  <path class="ring" fill="none"${paint("stroke", "ring")} stroke-width="${(w.ring * unit).toFixed(2)}" stroke-linejoin="round" d="${ring}Z"/>\n` +
    `  <path class="vector" fill="none"${paint("stroke", "vector")} stroke-width="${(w.vector * unit).toFixed(2)}" stroke-linecap="round" d="M${at([0, 0])}L${at(base)}"/>\n` +
    `  <path class="tip"${paint("fill", "vector")} d="M${at(tip)}L${at([base[0] - uy * wing, base[1] + ux * wing])}L${at([base[0] + uy * wing, base[1] - ux * wing])}Z"/>\n` +
    `  <circle class="pen"${paint("fill", "pen")} cx="${(px + x).toFixed(2)}" cy="${(py + y).toFixed(2)}" r="${(w.pen * unit).toFixed(2)}"/>\n`
  );
};

const svg = (width: number, height: number, body: string) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width.toFixed(1)} ${height.toFixed(1)}" width="${width.toFixed(1)}" height="${height.toFixed(1)}" role="img" aria-label="manim-marimo">\n` +
  `  <title>manim-marimo</title>\n${body}</svg>\n`;

const draw = (shape: Outline, x: number, y: number, scale: number, fill: string) =>
  `  <path fill="${fill}" transform="translate(${x.toFixed(2)} ${y.toFixed(2)}) scale(${scale.toFixed(5)})" d="${shape.d}"/>\n`;

// Lockup sizes are in units of the wordmark's font size.
const size = 100;
const wordScale = size / wordmark.em;
const wordWidth = wordmark.width * wordScale;
const wordHeight = wordmark.height * wordScale;
const pad = 0.12 * size;
const square = 512;

const build: Record<string, (theme: Theme) => string> = {
  mark: (theme) => svg(square, square, markBody(theme, "fine", square, square / 2, square / 2)),
  icon: (theme) => svg(square, square, markBody(theme, "bold", square, square / 2, square / 2)),
  wordmark: (theme) => svg(wordWidth + 2 * pad, wordHeight + 2 * pad, draw(wordmark, pad, pad, wordScale, themes[theme].ink)),
  "lockup-horizontal": (theme) => {
    // The mark centers on the wordmark's x-height.
    const side = 1.04 * size;
    const gap = 0.3 * size;
    const baseline = wordmark.baseline * wordScale;
    const center = baseline - (xHeight * wordScale) / 2;
    const top = Math.min(0, center - side / 2);
    const bottom = Math.max(wordHeight, center + side / 2);
    const shift = pad - top;
    return svg(
      pad + side + gap + wordWidth + pad,
      bottom - top + 2 * pad,
      markBody(theme, "medium", side, pad + side / 2, center + shift, 0) +
        draw(wordmark, pad + side + gap, shift, wordScale, themes[theme].ink),
    );
  },
  "lockup-stacked": (theme) => {
    const side = 3 * size;
    const gap = 0.7 * size;
    const margin = 2 * pad;
    const width = Math.max(side, wordWidth) + 2 * margin;
    return svg(
      width,
      margin + side + gap + wordHeight + margin,
      markBody(theme, "medium", side, width / 2, margin + side / 2, 0) +
        draw(wordmark, (width - wordWidth) / 2, margin + side + gap, wordScale, themes[theme].ink),
    );
  },
};

// The favicon sits on the scene's plate, so it reads on light and dark tab
// strips alike.
const plated = (side: number) =>
  svg(
    side,
    side,
    `  <rect width="${side}" height="${side}" rx="${side * 0.18}" fill="${themes.dark.page}"/>\n` +
      markBody("dark", "bold", side, side / 2, side / 2),
  );
const favicon = plated(square);
const touchIcon = svg(180, 180, `  <rect width="180" height="180" fill="${themes.dark.page}"/>\n` + markBody("dark", "bold", 150, 90, 90));

await mkdir(brand, { recursive: true });
const assets: { file: string; width: number }[] = [];
for (const [name, make] of Object.entries(build)) {
  for (const theme of Object.keys(themes) as Theme[]) {
    const file = `manim-marimo-${name}-${theme}.svg`;
    await writeFile(join(brand, file), make(theme));
    assets.push({ file, width: name === "lockup-horizontal" || name === "wordmark" ? 1280 : name === "lockup-stacked" ? 960 : 512 });
  }
}
await writeFile(join(root, "docs/public/favicon.svg"), favicon);
// The hero draws the mark, then writes the wordmark one closed contour at a
// time, in reading order.
// opentype.js starts each contour with a moveto and leaves it implicitly closed.
const contours = wordmark.d.split(/(?=M)/).map((contour) => `${contour.trim()}Z`);
await writeFile(
  join(root, "docs/.vitepress/theme/brand.ts"),
  `// Generated by scripts/design/brand.ts. The mark's rotating vectors come from\n` +
    `// examples/fourier.py as [frequency, real, imaginary] rows, longest first,\n` +
    `// and draw a path one unit wide. The wordmark is "manim-marimo" set in CMU\n` +
    `// Serif, as SVG path data in font units with y pointing down, one closed\n` +
    `// contour per entry in reading order.\n` +
    `export const mark: [number, number, number][] = ${JSON.stringify(terms.map((row) => row.map((v) => Number(v.toFixed(6)))))};\n\n` +
    `export const wordmark = ${JSON.stringify({ width: Math.round(wordmark.width), height: Math.round(wordmark.height), contours }, null, 2)};\n`,
);

// Rasterize each SVG at a fixed width with a transparent background, then
// compose the Open Graph image and the brand board from the same assets.
const browser = await chromium.launch();
const raster = async (page: Page, markup: string, width: number, out: string) => {
  await page.setContent(`<body style="margin:0">${markup.replace(/width="[\d.]+" height="[\d.]+"/, `width="${width}"`)}</body>`);
  await page.locator("svg").screenshot({ path: out, omitBackground: true });
};
const page = await browser.newPage({ deviceScaleFactor: 1 });
for (const asset of assets) {
  await raster(page, await readFile(join(brand, asset.file), "utf8"), asset.width, join(brand, asset.file.replace(/\.svg$/, ".png")));
}
await raster(page, touchIcon, 180, join(root, "docs/public/apple-touch-icon.png"));
await page.close();

const data = { terms, themes, wordmark, xHeight };
const compose = async (template: string, out: string, viewport: { width: number; height: number }, full = false) => {
  const view = await browser.newPage({ colorScheme: "dark", deviceScaleFactor: 2, viewport });
  await view.addInitScript((value: unknown) => Object.assign(window, { brand: value }), data);
  await view.goto(pathToFileURL(join(here, template)).href);
  await view.waitForSelector("body[data-ready=true]");
  await view.screenshot({ path: out, fullPage: full });
  await view.close();
};
await compose("og.html", join(brand, "manim-marimo-og.png"), { width: 1200, height: 630 });
await compose("board.html", join(brand, "manim-marimo-brand-board.png"), { width: 1440, height: 900 }, true);
await browser.close();

// The examples' scenes register TrueType faces, and their pages load WOFF2
// faces from assets/. Both keep Latin, punctuation, Greek, arrows, and math
// operators, and the copyright and license names the OFL requires.
const ranges = [
  [0x20, 0x7e],
  [0xa0, 0x17f],
  [0x2c6, 0x2dd],
  [0x391, 0x3c9],
  [0x2000, 0x206f],
  [0x2190, 0x21ff],
  [0x2200, 0x22ff],
];
const text = ranges.flatMap(([a, b]) => Array.from({ length: b! - a! + 1 }, (_, i) => String.fromCodePoint(a! + i))).join("");
const subset = (file: string, format: "truetype" | "woff2") =>
  readFile(face(file)).then((source) =>
    subsetFont(source, text, { targetFormat: format, preserveNameIds: [0, 1, 2, 3, 4, 5, 6, 13, 14] }),
  );
const license = await readFile(join(here, "node_modules/computer-modern/OFL.txt"));
const scenes: Record<string, string[]> = {
  convolution: ["cmu-serif-500-roman"],
  dataflow: ["cmu-serif-500-roman", "cmu-typewriter-text-500-roman"],
  epidemic: ["cmu-serif-500-roman"],
  fourier: ["cmu-serif-500-roman"],
};
const pages = ["cmu-serif-500-roman", "cmu-serif-500-italic", "cmu-typewriter-text-500-roman"];
for (const [example, faces] of Object.entries(scenes)) {
  const view = join(root, "examples/studio", example, "animation");
  for (const [directory, files, format] of [
    [join(view, "fonts"), faces, "truetype"],
    [join(view, "assets/fonts"), pages, "woff2"],
  ] as const) {
    await mkdir(directory, { recursive: true });
    await writeFile(join(directory, "OFL.txt"), license);
    for (const file of files) {
      await writeFile(join(directory, `${file}.${format === "truetype" ? "ttf" : "woff2"}`), await subset(file, format));
    }
  }
}
console.log(`wrote ${assets.length * 2 + 3} brand files and the fonts of ${Object.keys(scenes).length} examples`);
