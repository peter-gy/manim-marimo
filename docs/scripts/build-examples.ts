// Export the examples the documentation site embeds into
// docs/public/exports/NAME/. Usage: pixi run docs-examples
//
//   page/       the Animation view as a zero-python static site, with one
//               prepared movie per state in states.yaml
//   notebook/   the notebook as static marimo HTML with its outputs
//   render/     the default state's animation.mp4, poster.png, and
//               metadata.json, copied from the page export
//   example.json  the default state's inputs, the movie's metadata, the reads
//               of scene.py, and the traced shapes of the default movie with
//               the cells and values behind their reads
//
// Each export replaces its previous copy only after every part validates.
import { execFile } from "node:child_process";
import { copyFile, mkdir, mkdtemp, readFile, rename, rm, stat, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { promisify } from "node:util";

const run = promisify(execFile);
const docs = resolve(import.meta.dirname, "..");
const root = resolve(docs, "..");
const examples = ["convolution", "epidemic"];
const view = "animation";
const scene = "scene.py";
// The reader sees a value beside the shape that shows it, so values larger than
// a tooltip, such as every person's path, stay in the page export.
const maxValueBytes = 64 * 1024;

interface ExportResult {
  preflight: { ok: boolean };
  runtime: string;
  view: string;
  warnings: unknown[];
}

// Studio's prepared export records the default state and the scene's reads in
// zero-python/current, each state's values in the export index, and the cell
// that produced each notebook variable in the view's config.
interface Current {
  prepared: { export_url: string; inputs: Record<string, unknown>; state_fingerprint: string };
  projections: {
    renders: Record<
      string,
      { cells: Record<string, string>; outputs: Record<string, string>; values: Record<string, string> }
    >;
  };
}

interface Config {
  projectionTargets: { variables: Record<string, { producerLabel?: string }> };
}

interface States {
  states: Record<string, { outputs: Record<string, { value?: unknown }> }>;
}

interface Region {
  file: string;
  rect: { x: number; y: number; width: number; height: number };
  reads: string[];
  start: number | null;
  end: number | null;
  label: string | null;
  source: { path: string; line: number } | null;
}

// renders/index.json maps each state to the bundle of each render and lists
// each bundle's files and regions once.
interface RenderIndex {
  schema: 2;
  bundles: Record<string, { main: string; preview: string; regions: Region[] }>;
  states: Record<
    string,
    Record<string, { bundle: string; warnings: { code: string; message: string }[] }>
  >;
}

const isFile = async (path: string): Promise<boolean> =>
  stat(path).then(
    (entry) => entry.isFile(),
    () => false,
  );

const json = async <T>(path: string): Promise<T> => JSON.parse(await readFile(path, "utf8")) as T;

// A read narrows a target with field and index steps, such as people[17] of
// the target people, or summary.peak of summary.
const targetOf = (read: string, targets: string[]): string | undefined =>
  targets
    .filter((target) => read === target || read.startsWith(`${target}.`) || read.startsWith(`${target}[`))
    .sort((a, b) => b.length - a.length)[0];

async function exportExample(name: string, staging: string): Promise<void> {
  const notebook = `examples/${name}.py`;
  const page = join(staging, "page");
  console.log(`Exporting ${notebook} view ${view} with the zero-python runtime`);
  const { stdout } = await run(
    "marimo-studio",
    ["view", "export", view, "--target", notebook, "--output", page, "--runtime", "zero-python", "--json"],
    { cwd: root, env: { ...process.env, NO_COLOR: "1" }, maxBuffer: 64 * 1024 * 1024 },
  );
  const result = JSON.parse(stdout) as ExportResult;
  if (result.runtime !== "zero-python" || result.view !== view || result.preflight?.ok !== true) {
    throw new Error(`The ${notebook} export returned an invalid result.`);
  }
  if (result.warnings.length > 0) {
    throw new Error(`The ${notebook} export warned:\n${JSON.stringify(result.warnings, null, 2)}`);
  }
  if (!(await readFile(join(page, "index.html"), "utf8")).includes('<base href="./">')) {
    throw new Error(`The ${notebook} page export has no document-relative base.`);
  }

  console.log(`Exporting ${notebook} as static HTML`);
  const notebookHtml = join(staging, "notebook/index.html");
  await mkdir(join(staging, "notebook"));
  await run("marimo", ["export", "html", notebook, "--output", notebookHtml], { cwd: root });
  if (!(await readFile(notebookHtml, "utf8")).includes("<marimo-code hidden")) {
    throw new Error(`The ${notebook} notebook export is missing its source.`);
  }

  const state = join(page, "_marimo-studio/views", view);
  const current = await json<Current>(join(state, "zero-python/current"));
  const config = await json<Config>(join(state, "config"));
  const states = await json<States>(join(state, "zero-python", current.prepared.export_url, "index.json"));
  const index = await json<RenderIndex>(join(state, "renders/index.json"));
  if (index.schema !== 2) {
    throw new Error(`The ${notebook} export has render index schema ${index.schema}, expected 2.`);
  }
  const warnings = Object.values(index.states).flatMap((renders) =>
    Object.values(renders).flatMap((render) => render.warnings),
  );
  if (warnings.length > 0) {
    throw new Error(`The ${notebook} export's renders warned:\n${JSON.stringify(warnings, null, 2)}`);
  }
  const fingerprint = current.prepared.state_fingerprint;
  const id = index.states[fingerprint]?.[scene]?.bundle;
  const render = id === undefined ? undefined : index.bundles[id];
  const reads = current.projections.renders[scene];
  if (!id || !render || !reads) {
    throw new Error(`The ${notebook} export has no render of ${scene} for its default state.`);
  }
  const bundle = join(state, "renders", id);
  await mkdir(join(staging, "render"));
  for (const file of [render.main, render.preview, "metadata.json"]) {
    if (!(await isFile(join(bundle, file)))) {
      throw new Error(`The ${notebook} default render is missing ${file}.`);
    }
    await copyFile(join(bundle, file), join(staging, "render", file));
  }

  const targets = [...Object.keys(reads.values), ...Object.keys(reads.outputs), ...Object.keys(reads.cells)];
  const used = new Set(
    render.regions.flatMap((region) => region.reads.map((read) => targetOf(read, targets) ?? read)),
  );
  const cells: Record<string, string> = {};
  const values: Record<string, unknown> = {};
  for (const target of used) {
    const variable = target.split(/[.[]/)[0];
    const producer = config.projectionTargets.variables[variable]?.producerLabel;
    if (producer) cells[target] = producer;
    const stored = states.states[fingerprint]?.outputs[`value:${target}`]?.value;
    if (stored !== undefined && JSON.stringify(stored).length <= maxValueBytes) values[target] = stored;
  }
  const example = {
    inputs: current.prepared.inputs,
    movie: await json<Record<string, number>>(join(bundle, "metadata.json")),
    reads: [
      ...Object.keys(reads.values).map((target) => `value("${target}")`),
      ...Object.keys(reads.outputs).map((target) => `output("${target}")`),
      ...Object.keys(reads.cells).map((target) => `cell("${target}")`),
    ],
    trace: {
      cells,
      values,
      // Regions of the movie, as [x, y, width, height, start, end, reads,
      // label, path, line], and of the poster without times.
      movie: render.regions
        .filter((region) => region.file === render.main)
        .map(({ rect, start, end, reads, label, source }) => [
          rect.x,
          rect.y,
          rect.width,
          rect.height,
          start ?? 0,
          end,
          reads,
          label,
          source?.path ?? null,
          source?.line ?? null,
        ]),
      poster: render.regions
        .filter((region) => region.file === render.preview)
        .map(({ rect, reads, label, source }) => [
          rect.x,
          rect.y,
          rect.width,
          rect.height,
          reads,
          label,
          source?.path ?? null,
          source?.line ?? null,
        ]),
    },
  };
  await writeFile(join(staging, "example.json"), `${JSON.stringify(example)}\n`);
}

await mkdir(join(docs, ".vitepress/cache"), { recursive: true });
// Studio's exports share one cache, so they run one after another.
for (const name of examples) {
  const staging = await mkdtemp(join(docs, `.vitepress/cache/exports-${name}-`));
  const destination = join(docs, "public/exports", name);
  try {
    await exportExample(name, staging);
    await rm(destination, { force: true, recursive: true });
    await mkdir(join(destination, ".."), { recursive: true });
    await rename(staging, destination);
    console.log(`Exported ${name} to ${destination}`);
  } finally {
    await rm(staging, { force: true, recursive: true });
  }
}
