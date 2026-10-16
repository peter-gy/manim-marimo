// Compose the README hero from the captured shots and write it in every theme
// to docs/public/media/. Usage: pixi run hero-render
//
// `pixi run hero-render --at 3.2 --at 12` writes the frames at those seconds to
// shots/ as PNG files and skips the encode, for checking the layout.
//
// The hero plays the fair-dice movie, drags the notebook slider toward six,
// plays the movie Studio renders for the new value, and drags it back, so the
// animation loops. Highlights follow the scene's reads as the movie plays.
import { $ } from "bun";
import { existsSync } from "node:fs";
import { mkdir, readFile, rm } from "node:fs/promises";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright";

import { step, themes, type Manifest, type State } from "./hero.ts";

interface FrameState {
  cursor: { dx: number; dy: number; opacity: number; pressed: boolean; step: number };
  focus: Partial<Record<"chart" | "controls" | "distributions", number>>;
  mean: string;
  movie: { frame: number; next?: { frame: number; opacity: number; state: State }; state: State };
  reads: Partial<Record<"figure" | "joint" | "mean" | "probabilities", number>>;
  render: { label: string; opacity: number; progress: number };
  step: number;
}

const here = import.meta.dir;
const root = resolve(here, "../..");
const shotsDir = join(here, "shots");
const outDir = join(root, "docs/public/media");
const manifestFile = join(shotsDir, "manifest.json");
if (!existsSync(manifestFile)) {
  throw new Error("Missing shots. Capture them with pixi run hero-capture.");
}
const manifest = JSON.parse(await readFile(manifestFile, "utf8")) as Manifest;
const { fps } = manifest;
// README columns are about 880 CSS pixels wide, so 1.5x keeps the 1200 pixel
// composition sharp on high-density screens.
const scale = 1.5;
// Lossy animated WebP keeps stale pixels wherever a fade ends with changes
// below the encoder's threshold, such as the pointer fading out. Near-lossless
// frames update exactly the pixels that change.
const nearLossless = 40;
const previews = process.argv.flatMap((argument, index, all) =>
  all[index - 1] === "--at" ? [Number(argument)] : [],
);

// Seconds into the movie at which examples/studio/convolution/animation/scene.py
// reaches each read: the table and the sums fill the diagonals, the mean fades
// in, and the notebook's chart replaces the bars.
const cues = { diagonals: 0.7, mean: 4.55, chart: 5.65 };

const clamp = (value: number) => Math.min(Math.max(value, 0), 1);
const smooth = (value: number) => {
  const t = clamp(value);
  return t * t * (3 - 2 * t);
};
// 1 inside [start, end), easing in and out over `fade` seconds.
const window_ = (t: number, start: number, end: number, fade = 0.25) =>
  Math.min(smooth((t - start) / fade + 1), smooth((end - t) / fade));

const timeline = (theme: (typeof themes)[number]): FrameState[] => {
  const shots = manifest.cells[theme];
  const mean = (state: State) => shots.chart[step(state)]!.mean;
  const frames: FrameState[] = [];
  const idle = { label: "", opacity: 0, progress: 0 };
  const still = (state: State, frame: number): FrameState => ({
    cursor: { dx: 0, dy: 0, opacity: 0, pressed: false, step: step(state) },
    focus: {},
    mean: mean(state),
    movie: { frame, state },
    reads: {},
    render: idle,
    step: step(state),
  });
  const seconds = (duration: number, paint: (t: number) => FrameState) => {
    const count = Math.round(duration * fps);
    for (let index = 0; index < count; index += 1) {
      frames.push(paint(index / fps));
    }
  };

  const play = (state: State) => {
    const last = manifest.states[state].frames - 1;
    const end = (last + 1) / fps + 0.9;
    seconds(end, (t) => ({
      ...still(state, Math.min(Math.round(t * fps), last)),
      focus: {
        chart: window_(t, cues.chart, end - 0.1, 0.35),
        distributions: window_(t, cues.diagonals, cues.chart),
      },
      reads: {
        figure: window_(t, cues.chart, end - 0.1, 0.35),
        joint: window_(t, cues.diagonals, cues.mean),
        mean: window_(t, cues.mean, cues.chart),
        probabilities: window_(t, cues.diagonals, cues.mean),
      },
    }));
  };

  const drag = (from: State, to: State) => {
    const last = manifest.states[from].frames - 1;
    const start = step(from);
    const target = step(to);
    const approach = 0.55;
    const travel = 1.5;
    const leave = 0.5;
    const rendering = 1.4;
    const swap = 0.35;
    // The new movie's first frame holds briefly, so the swap completes inside
    // this segment.
    const settle = 0.2;
    const release = approach + travel;
    const label = `Rendering bias = ${manifest.states[to].bias}`;
    seconds(release + rendering + swap + settle, (t) => {
      const moved = smooth((t - approach) / travel);
      const pointer = start + (target - start) * moved;
      const entering = 1 - smooth(t / approach);
      const leaving = smooth((t - release) / leave);
      const shown = clamp((t - release - rendering) / swap);
      return {
        ...still(from, last),
        cursor: {
          dx: 34 * entering + 30 * leaving,
          dy: 30 * entering + 26 * leaving,
          opacity: Math.min(smooth(t / (approach * 0.7)), 1 - leaving),
          pressed: t >= approach - 0.05 && t < release + 0.05,
          step: pointer,
        },
        focus: { controls: window_(t, 0.3, release + leave * 0.6, 0.3) },
        mean: shown < 1 ? mean(from) : mean(to),
        movie: { frame: last, next: { frame: 0, opacity: smooth(shown), state: to }, state: from },
        render: {
          label,
          opacity: window_(t, release, release + rendering + swap * 0.5, 0.2),
          progress: smooth((t - release) / rendering),
        },
        step: Math.round(pointer),
      };
    });
  };

  seconds(0.5, () => still("fair", 0));
  play("fair");
  drag("fair", "biased");
  play("biased");
  drag("biased", "fair");
  return frames;
};

await mkdir(outDir, { recursive: true });
const browser = await chromium.launch();
try {
  // Each theme paints in its own page and encodes in its own process.
  const renderTheme = async (theme: (typeof themes)[number]) => {
    const page = await browser.newPage({ deviceScaleFactor: scale, viewport: { height: 900, width: 1200 } });
    await page.addInitScript((hero: unknown) => Object.assign(window, { hero }), { manifest, theme });
    await page.goto(pathToFileURL(join(here, "compose.html")).href);
    await page.waitForSelector("body[data-ready=true]", { timeout: 60_000 });

    const frames = timeline(theme);
    if (previews.length > 0) {
      for (const at of previews) {
        const index = Math.min(Math.round(at * fps), frames.length - 1);
        await page.evaluate((frameState: FrameState) => (window as any).show(frameState), frames[index]!);
        const file = join(shotsDir, `preview-${theme}-${at}.png`);
        await page.locator("#canvas").screenshot({ path: file });
        console.log(`wrote ${file}`);
      }
      await page.close();
      return;
    }

    // Consecutive identical frames become one longer WebP frame.
    const framesDir = join(shotsDir, `frames-${theme}`);
    await rm(framesDir, { force: true, recursive: true });
    await mkdir(framesDir);
    const encoded: { duration: number; file: string }[] = [];
    let previous = "";
    for (const state of frames) {
      const key = JSON.stringify(state);
      const duration = 1000 / fps;
      if (key === previous) {
        encoded.at(-1)!.duration += duration;
        continue;
      }
      previous = key;
      const file = join(framesDir, `${String(encoded.length).padStart(4, "0")}.png`);
      await page.evaluate((frameState: FrameState) => (window as any).show(frameState), state);
      await page.locator("#canvas").screenshot({ path: file });
      encoded.push({ duration, file });
    }
    await page.close();

    const output = join(outDir, `hero-${theme}.webp`);
    const arguments_ = encoded.flatMap(({ duration, file }) => ["-d", String(Math.round(duration)), file]);
    await $`img2webp -loop 0 -min_size -near_lossless ${nearLossless} -lossless -q 75 -m 4 ${arguments_} -o ${output}`.quiet();
    const seconds = frames.length / fps;
    console.log(`rendered ${output}: ${encoded.length} frames, ${seconds.toFixed(1)} s`);
  };
  await Promise.all(themes.map(renderTheme));
} finally {
  await browser.close();
}
