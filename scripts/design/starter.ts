// Capture the preview Studio's New view dialog shows for the Manim animation
// starter. Usage: pixi run starter-preview
//
// The capture creates a view from the starter for a small notebook in a
// scratch workspace inside the repository, where Studio finds manim-marimo in
// the project dependencies. It exports the view, shows the movie's frame at
// `at`, and writes the page at 1280 by 800 to
// src/manim_marimo/starters/default/preview.webp.
import { $ } from "bun";
import { mkdir, readdir, rm, writeFile } from "node:fs/promises";
import { extname, join, resolve } from "node:path";
import { chromium } from "playwright";

const here = import.meta.dir;
const root = resolve(here, "../..");
const workspace = join(here, "out/starter");
const exported = join(workspace, "export");
const shot = join(workspace, "preview.png");
const preview = join(root, "src/manim_marimo/starters/default/preview.webp");
// The dot is halfway along the curve.
const at = 2.5;

await rm(workspace, { force: true, recursive: true });
await mkdir(workspace, { recursive: true });
await writeFile(
  join(workspace, "analysis.py"),
  `import marimo

app = marimo.App(width="medium", app_title="Random walk")


@app.cell
def _():
    import marimo as mo
    import numpy as np

    return mo, np


@app.cell
def _(mo):
    steps = mo.ui.slider(20, 120, value=60, step=20, label="Steps", show_value=True)
    steps
    return (steps,)


@app.cell
def _(np, steps):
    trajectory = (np.random.default_rng(7).normal(size=(steps.value, 2)) * 0.3).cumsum(axis=0)
    return (trajectory,)


@app.cell
def _(mo, trajectory):
    mo.md(f"The walk ends {float((trajectory[-1] ** 2).sum() ** 0.5):.2f} units from where it started.")
    return


if __name__ == "__main__":
    app.run()
`,
);
await $`marimo-studio view create animation --target analysis.py --starter manim-marimo/manim:default`.cwd(workspace).quiet();
await $`marimo-studio view export animation --target analysis.py --output ${exported} --runtime zero-python`.cwd(workspace).quiet();

// Playwright's Chromium decodes no H.264, so the worker's ffmpeg extracts the
// frame and the page shows it as the movie's poster.
const renders = join(exported, "_marimo-studio/views/animation/renders");
const [bundle] = await readdir(renders);
const ffmpeg = (await $`python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"`.text()).trim();
await $`${ffmpeg} -v error -ss ${at} -i ${join(renders, bundle!, "animation.mp4")} -frames:v 1 ${join(exported, "frame.png")}`;

const types: Record<string, string> = { ".css": "text/css", ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".png": "image/png" };
const server = Bun.serve({
  port: 0,
  async fetch(request) {
    const path = decodeURIComponent(new URL(request.url).pathname);
    const file = Bun.file(join(exported, path.endsWith("/") ? `${path}index.html` : path));
    if (!(await file.exists())) return new Response("Not found", { status: 404 });
    return new Response(file, { headers: { "content-type": types[extname(file.name!)] ?? "application/octet-stream" } });
  },
});

const browser = await chromium.launch();
try {
  // The dialog shows the top of the preview at about 3:1, so the page lays
  // out at 1.5 times the preview's size to bring the scene into that band.
  const page = await browser.newPage({ colorScheme: "dark", deviceScaleFactor: 2 / 3, viewport: { height: 1200, width: 1920 } });
  await page.goto(server.url.href);
  await page.waitForFunction(() =>
    [...document.querySelectorAll("marimo-cell")].every((cell) => cell.getBoundingClientRect().height > 0),
  );
  await page.locator("video").evaluate(async (video: HTMLVideoElement) => {
    const frame = new Image();
    frame.src = "/frame.png";
    await frame.decode();
    video.removeAttribute("controls");
    video.poster = frame.src;
  });
  await page.screenshot({ path: shot });
} finally {
  await browser.close();
  server.stop();
}
await $`cwebp -quiet -q 88 -m 6 ${shot} -o ${preview}`;
console.log(`wrote ${preview}`);
