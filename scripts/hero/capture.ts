// Capture the shots the README hero composes: the dataflow movie for two
// radio choices, and the notebook cells with each choice selected, in each
// theme. Usage: pixi run hero-capture
//
// The capture copies examples/dataflow.py and its view into a scratch
// workspace inside the repository, where Studio finds manim-marimo in the
// project dependencies. It exports one movie per choice through
// `marimo-studio view export`, and clicks the choices in the marimo editor.
// render.ts composes the shots.
import { $, type Subprocess } from "bun";
import { cp, mkdir, readdir, rm, writeFile } from "node:fs/promises";
import { createServer, type AddressInfo } from "node:net";
import { join, resolve } from "node:path";
import { chromium } from "playwright";

import { cells, fps, movieWidth, states, themes, type Manifest } from "./hero.ts";

const here = import.meta.dir;
const root = resolve(here, "../..");
const shotsDir = join(here, "shots");
const timeoutMs = 300_000;
// marimo keeps a medium-width cell 510 CSS pixels wide in this viewport, with
// its floating controls clear of the cells.
const editorViewport = { height: 1400, width: 700 };
const editorScale = 3;

const freePort = (): Promise<number> =>
  new Promise((resolvePort, rejectPort) => {
    const probe = createServer();
    probe.on("error", rejectPort);
    probe.listen(0, "127.0.0.1", () => {
      const { port } = probe.address() as AddressInfo;
      probe.close(() => resolvePort(port));
    });
  });

const workspace = join(shotsDir, "workspace");
const notebook = join(workspace, "dataflow.py");
const view = join(workspace, "studio/dataflow/animation");
let editor: Subprocess | undefined;
const stopEditor = async (): Promise<void> => {
  editor?.kill();
  await editor?.exited;
  editor = undefined;
};
for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.once(signal, async () => {
    await stopEditor();
    await rm(workspace, { force: true, recursive: true });
    process.exit(signal === "SIGINT" ? 130 : 143);
  });
}

await rm(shotsDir, { force: true, recursive: true });
await mkdir(workspace, { recursive: true });
await cp(join(root, "examples/dataflow.py"), notebook);
await cp(join(root, "examples/studio/dataflow/animation"), view, { recursive: true });

// The render worker encodes movies with imageio-ffmpeg's ffmpeg, so the
// capture decodes them with the same build.
const ffmpeg = (await $`python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"`.text()).trim();

const manifest: Manifest = {
  cells: { dark: {}, light: {} } as Manifest["cells"],
  fps,
  states: {} as Manifest["states"],
};

try {
  // Each export renders one state, so its only movie belongs to that choice.
  for (const state of states) {
    await writeFile(
      join(view, "states.yaml"),
      ["schema: marimo-export.states.v1", "default_state: matrix-000000", "matrix:", `  changed: ["${state}"]`, ""].join(
        "\n",
      ),
    );
    const output = join(workspace, "exports", state);
    console.log(`rendering ${state}`);
    const exported = await $`marimo-studio view export animation --target ${notebook} --output ${output} --runtime zero-python --json`
      .quiet()
      .nothrow();
    if (exported.exitCode !== 0) {
      throw new Error(`Exporting ${state} failed:\n${exported.stderr.toString()}`);
    }
    const renders = join(output, "_marimo-studio/views/animation/renders");
    const bundles = (await readdir(renders, { withFileTypes: true })).filter((entry) => entry.isDirectory());
    if (bundles.length !== 1) {
      throw new Error(`Expected one render for ${state}, found ${bundles.length}.`);
    }
    const bundle = join(renders, bundles[0]!.name);
    const frames = join(shotsDir, `movie-${state}`);
    await mkdir(frames);
    await $`${ffmpeg} -v error -i ${join(bundle, "animation.mp4")} -vf fps=${fps},scale=${movieWidth}:-2:flags=lanczos ${join(frames, "%04d.png")}`;
    manifest.states[state] = {
      frames: (await readdir(frames)).length,
      movie: await Bun.file(join(bundle, "metadata.json")).json(),
    };
  }

  const browser = await chromium.launch();
  try {
    for (const theme of themes) {
      // marimo reads .marimo.toml from the working directory first, so the
      // editor ignores the user's own settings.
      await writeFile(
        join(workspace, ".marimo.toml"),
        [
          "[display]",
          `theme = "${theme}"`,
          "code_editor_font_size = 14",
          'cell_output = "below"',
          "",
          "[runtime]",
          "auto_instantiate = true",
          "",
          "[completion]",
          "activate_on_typing = false",
          "copilot = false",
          "",
        ].join("\n"),
      );
      const port = await freePort();
      editor = Bun.spawn(["marimo", "edit", "dataflow.py", "--headless", "--no-token", "--port", String(port)], {
        cwd: workspace,
        stderr: Bun.file(join(shotsDir, `marimo-${theme}.log`)),
        stdout: "ignore",
      });
      const url = `http://127.0.0.1:${port}/`;
      const deadline = Date.now() + timeoutMs;
      while (!(await fetch(url).then((response) => response.ok, () => false))) {
        if (Date.now() > deadline || editor.exitCode !== null) {
          throw new Error(`The marimo editor did not answer at ${url}. See shots/marimo-${theme}.log.`);
        }
        await Bun.sleep(500);
      }

      const context = await browser.newContext({
        colorScheme: theme,
        deviceScaleFactor: editorScale,
        reducedMotion: "reduce",
        viewport: editorViewport,
      });
      const page = await context.newPage();
      await page.goto(url, { timeout: timeoutMs });
      // Studio hosts the marimo editor in a frame beside its views. The frame
      // opens on its own, so the notebook gets the whole viewport.
      let editorUrl: string | undefined;
      while (!(editorUrl = page.frames().find((frame) => frame.url().includes("/_marimo-studio/editor/"))?.url())) {
        if (Date.now() > deadline) {
          throw new Error("Studio did not open the marimo editor frame.");
        }
        await page.waitForTimeout(250);
      }
      await page.goto(editorUrl, { timeout: timeoutMs });
      const frame = page.mainFrame();
      const cell = (name: string) => frame.locator(`.marimo-cell[data-cell-name="${name}"]`);
      // A summary naming the choice marks the finished run.
      const settled = async (state: string): Promise<void> => {
        await frame.waitForFunction(
          ([selector, choice]) =>
            document.querySelector(selector)?.textContent?.includes(`Moving ${choice}`) &&
            !document.querySelector('[data-status="running"], [data-status="queued"]'),
          [`.marimo-cell[data-cell-name="${cells.summary}"]`, state] as const,
          { polling: 250, timeout: timeoutMs },
        );
        await frame.evaluate(() => document.fonts.ready.then(() => undefined));
        await page.waitForTimeout(600);
      };
      // The hero shows a cell's output, or the code of a cell without one,
      // without marimo's cell chrome.
      const part = (name: string) =>
        name === cells.cascade ? cell(name).locator(".cm-editor").first() : cell(name).locator(".output-area").first();
      const shoot = async (name: string, file: string) => {
        await page.mouse.move(0, 0);
        const box = await part(name).boundingBox();
        if (!box) {
          throw new Error(`Cell ${name} is not visible.`);
        }
        await part(name).screenshot({ path: join(shotsDir, file) });
        return { file, height: box.height, width: box.width };
      };

      const shots = { controls: {}, choices: {}, summary: {} } as Manifest["cells"][typeof theme];
      await settled(states[0]);
      shots.cascade = await shoot(cells.cascade, `${theme}-cascade.png`);
      const box = await part(cells.controls).boundingBox();
      for (const state of states) {
        const choice = cell(cells.controls).getByRole("radio", { name: state, exact: true });
        await choice.check();
        await settled(state);
        const at = await choice.boundingBox();
        if (!box || !at) {
          throw new Error(`The ${state} choice is not visible.`);
        }
        shots.choices[state] = { x: at.x + at.width / 2 - box.x, y: at.y + at.height / 2 - box.y };
        shots.controls[state] = await shoot(cells.controls, `${theme}-controls-${state}.png`);
        shots.summary[state] = await shoot(cells.summary, `${theme}-summary-${state}.png`);
        console.log(`captured ${theme} ${state}`);
      }
      manifest.cells[theme] = shots;
      await context.close();
      await stopEditor();
    }
  } finally {
    await browser.close();
  }
  await writeFile(join(shotsDir, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
} finally {
  await stopEditor();
  await rm(workspace, { force: true, recursive: true });
}
