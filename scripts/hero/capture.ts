// Capture the shots the README hero composes: the convolution movie at two
// slider values, and the notebook cells at every slider step in each theme.
// Usage: pixi run hero-capture
//
// The capture copies examples/convolution.py and its view into a scratch
// workspace inside the repository, where Studio finds marimo-manim in the
// project dependencies. It exports one movie per state through `marimo-studio view export`,
// and drives the slider in the marimo editor. render.ts composes the shots.
import { $, type Subprocess } from "bun";
import { cp, mkdir, readdir, rm, writeFile } from "node:fs/promises";
import { createServer, type AddressInfo } from "node:net";
import { join, resolve } from "node:path";
import { chromium } from "playwright";

import { cells, fps, movieWidth, states, steps, themes, type Manifest, type Shot } from "./hero.ts";

const here = import.meta.dir;
const root = resolve(here, "../..");
const shotsDir = join(here, "shots");
const timeoutMs = 300_000;
// marimo keeps a medium-width cell 510 CSS pixels wide in this viewport, with
// its floating controls clear of the cells. The hero shows cells at 87% of that.
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
const notebook = join(workspace, "convolution.py");
const view = join(workspace, "studio/convolution/animation");
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
await cp(join(root, "examples/convolution.py"), notebook);
await cp(join(root, "examples/studio/convolution/animation"), view, { recursive: true });

// The render worker encodes movies with imageio-ffmpeg's ffmpeg, so the
// capture decodes them with the same build.
const ffmpeg = (await $`python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"`.text()).trim();

const manifest: Manifest = {
  cells: { dark: {}, light: {} } as Manifest["cells"],
  fps,
  states: {} as Manifest["states"],
};

try {
  // Each export renders one state, so its only movie belongs to that slider
  // value.
  for (const [name, { bias }] of Object.entries(states)) {
    await writeFile(
      join(view, "states.yaml"),
      ["schema: marimo-export.states.v1", "default_state: matrix-000000", "matrix:", `  bias: [${bias}]`, ""].join(
        "\n",
      ),
    );
    const output = join(workspace, "exports", name);
    console.log(`rendering bias ${bias}`);
    const exported = await $`marimo-studio view export animation --target ${notebook} --output ${output} --runtime zero-python --json`
      .quiet()
      .nothrow();
    if (exported.exitCode !== 0) {
      throw new Error(`Exporting bias ${bias} failed:\n${exported.stderr.toString()}`);
    }
    const renders = join(output, "_marimo-studio/views/animation/renders");
    const bundles = (await readdir(renders, { withFileTypes: true })).filter((entry) => entry.isDirectory());
    if (bundles.length !== 1) {
      throw new Error(`Expected one render for bias ${bias}, found ${bundles.length}.`);
    }
    const bundle = join(renders, bundles[0]!.name);
    const frames = join(shotsDir, `movie-${name}`);
    await mkdir(frames);
    await $`${ffmpeg} -v error -i ${join(bundle, "animation.mp4")} -vf fps=${fps},scale=${movieWidth}:-2:flags=lanczos ${join(frames, "%04d.png")}`;
    manifest.states[name as keyof typeof states] = {
      bias,
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
      editor = Bun.spawn(["marimo", "edit", "convolution.py", "--headless", "--no-token", "--port", String(port)], {
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
      const settled = async (): Promise<void> => {
        await frame.waitForFunction(
          () =>
            document.querySelector('.marimo-cell[data-cell-name="distribution_chart"] marimo-mime-renderer') &&
            !document.querySelector('[data-status="running"], [data-status="queued"]'),
          undefined,
          { polling: 250, timeout: timeoutMs },
        );
        await frame.evaluate(() => document.fonts.ready.then(() => undefined));
        await page.waitForTimeout(600);
      };
      await settled();
      const cell = (name: string) => frame.locator(`.marimo-cell[data-cell-name="${name}"]`);
      const slider = cell(cells.controls).locator('[role="slider"]');

      const shoot = async (name: string, file: string): Promise<Shot> => {
        await page.mouse.move(0, 0);
        const box = await cell(name).boundingBox();
        if (!box) {
          throw new Error(`Cell ${name} is not visible.`);
        }
        await cell(name).screenshot({ path: join(shotsDir, file) });
        return { file, height: box.height, width: box.width };
      };

      const shots = manifest.cells[theme];
      shots.distributions = await shoot(cells.distributions, `${theme}-distributions.png`);
      shots.controls = [];
      shots.chart = [];
      const expectedSum = async (): Promise<string> =>
        (await cell(cells.chart).innerText()).match(/Expected sum: (\d+\.\d+)/)?.[1] ?? "";
      let mean = await expectedSum();
      for (let step = 0; step < steps; step += 1) {
        // One key press per step gives the kernel one change to run, and every
        // step moves the expected sum, so a new sum marks the finished run.
        const before = await slider.getAttribute("aria-valuenow");
        await slider.focus();
        await page.keyboard.press(step === 0 ? "Home" : "ArrowRight");
        await slider.blur();
        if ((await slider.getAttribute("aria-valuenow")) !== before) {
          await frame.waitForFunction(
            ([selector, previous]) =>
              !document.querySelector(selector)?.textContent?.includes(`Expected sum: ${previous}`),
            [`.marimo-cell[data-cell-name="${cells.chart}"]`, mean] as const,
            { polling: 100, timeout: timeoutMs },
          );
        }
        await settled();
        mean = await expectedSum();
        const [cellBox, thumbBox] = await Promise.all([cell(cells.controls).boundingBox(), slider.boundingBox()]);
        if (!cellBox || !thumbBox) {
          throw new Error("The slider is not visible.");
        }
        shots.controls.push({
          ...(await shoot(cells.controls, `${theme}-controls-${step}.png`)),
          thumb: {
            x: thumbBox.x + thumbBox.width / 2 - cellBox.x,
            y: thumbBox.y + thumbBox.height / 2 - cellBox.y,
          },
        });
        shots.chart.push({ ...(await shoot(cells.chart, `${theme}-chart-${step}.png`)), mean });
        console.log(`captured ${theme} step ${step}, expected sum ${mean}`);
      }
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
