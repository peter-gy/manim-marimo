// Compose the README hero from the captured shots and write it in every theme
// to docs/public/media/. Usage: pixi run hero-render
//
// `pixi run hero-render --at 3.2 --at 12` writes the frames at those seconds to
// shots/ as PNG files and skips the encode, for checking the layout.
//
// The hero plays the movie for the noise slider, clicks "degree" in the
// notebook, plays the cascade Studio renders for it, and clicks "noise" again,
// so the animation loops. Rectangles surround each read as the scene uses it.
import { $ } from "bun";
import { existsSync } from "node:fs";
import { mkdir, readFile, rm } from "node:fs/promises";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright";

import { themes, type Manifest, type State } from "./hero.ts";

type Read = "nodes" | "edges" | "backward" | "rerun" | "changed";

interface FrameState {
  choice: State;
  cursor: { dx: number; dy: number; opacity: number; pressed: boolean; target: State };
  focus: Partial<Record<"controls" | "cascade", number>>;
  movie: { frame: number; next?: { frame: number; opacity: number; state: State }; state: State };
  reads: Partial<Record<Read, number>>;
  render: { label: string; opacity: number; progress: number };
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
const nearLossless = 20;
const previews = process.argv.flatMap((argument, index, all) =>
  all[index - 1] === "--at" ? [Number(argument)] : [],
);

// Seconds into the movie at which examples/studio/dataflow/animation/scene.py
// reads each result: the cells appear, the references draw, the caption counts
// the backward ones, the cells sort, and the cascade runs.
const cues = { cells: 0.8, references: 2.4, backward: 5.4, sort: 7.2, cascade: 11.2 };

const clamp = (value: number) => Math.min(Math.max(value, 0), 1);
const smooth = (value: number) => {
  const t = clamp(value);
  return t * t * (3 - 2 * t);
};
// 1 inside [start, end), easing in and out over `fade` seconds.
const window_ = (t: number, start: number, end: number, fade = 0.25) =>
  Math.min(smooth((t - start) / fade + 1), smooth((end - t) / fade));

const timeline = (): FrameState[] => {
  const frames: FrameState[] = [];
  const idle = { label: "", opacity: 0, progress: 0 };
  const still = (state: State, frame: number): FrameState => ({
    choice: state,
    cursor: { dx: 0, dy: 0, opacity: 0, pressed: false, target: state },
    focus: {},
    movie: { frame, state },
    reads: {},
    render: idle,
  });
  const seconds = (duration: number, paint: (t: number) => FrameState) => {
    const count = Math.round(duration * fps);
    for (let index = 0; index < count; index += 1) {
      frames.push(paint(index / fps));
    }
  };

  // Plays `state` from `from` seconds into its movie, with the reads lit at
  // the moments the scene uses them.
  const play = (state: State, from = 0) => {
    const last = manifest.states[state].frames - 1;
    const end = (last + 1) / fps - from + 1;
    seconds(end, (t) => {
      const at = t + from;
      return {
        ...still(state, Math.min(Math.round(at * fps), last)),
        focus: { cascade: window_(at, cues.cascade, cues.cascade + 5, 0.35) },
        reads: {
          nodes: Math.max(window_(at, cues.cells, cues.references), window_(at, cues.sort, cues.cascade)),
          edges: window_(at, cues.references, cues.backward),
          backward: window_(at, cues.backward, cues.sort),
          changed: window_(at, cues.cascade, cues.cascade + 1.4),
          rerun: window_(at, cues.cascade + 0.6, cues.cascade + 5.5, 0.35),
        },
      };
    });
  };

  // Clicks `to` in the notebook while `from` holds its last frame, then fades
  // to the new movie at `start` seconds.
  const choose = (from: State, to: State, start = 0) => {
    const last = manifest.states[from].frames - 1;
    const approach = 0.8;
    const press = 0.18;
    const leave = 0.5;
    const rendering = 1.4;
    const swap = 0.35;
    const release = approach + press;
    seconds(release + rendering + swap + 0.2, (t) => {
      const entering = 1 - smooth(t / approach);
      const leaving = smooth((t - release) / leave);
      const shown = clamp((t - release - rendering) / swap);
      return {
        ...still(from, last),
        choice: t >= approach ? to : from,
        cursor: {
          dx: 46 * entering + 30 * leaving,
          dy: 34 * entering + 26 * leaving,
          opacity: Math.min(smooth(t / (approach * 0.7)), 1 - leaving),
          pressed: t >= approach - 0.05 && t < release,
          target: to,
        },
        focus: { controls: window_(t, 0.2, release + leave * 0.8, 0.3) },
        movie: { frame: last, next: { frame: Math.round(start * fps), opacity: smooth(shown), state: to }, state: from },
        render: {
          label: `Rendering changed = ${to}`,
          opacity: window_(t, release, release + rendering + swap * 0.5, 0.2),
          progress: smooth((t - release) / rendering),
        },
      };
    });
  };

  seconds(0.4, () => still("noise", 0));
  play("noise");
  // The movies agree until the cascade, so the second one starts there.
  const jump = cues.cascade - 0.4;
  choose("noise", "degree", jump);
  play("degree", jump);
  choose("degree", "noise");
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

    const frames = timeline();
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
