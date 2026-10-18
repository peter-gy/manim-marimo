// Export the convolution example for the documentation site into
// docs/public/exports/convolution/. Usage: pixi run docs-examples
//
//   page/       the Animation view as a zero-python static site, with one
//               prepared movie per bias value in states.yaml
//   notebook/   the notebook as static marimo HTML with its outputs
//   render/     the default state's animation.mp4, poster.png, and
//               metadata.json, copied from the page export
//   example.json  the files above, the default state's inputs, and the reads
//               of scene.py
//
// The export replaces the previous copy only after every part validates.
import { execFile } from "node:child_process";
import { copyFile, mkdir, mkdtemp, readFile, rename, rm, stat, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { promisify } from "node:util";

const run = promisify(execFile);
const docs = resolve(import.meta.dirname, "..");
const root = resolve(docs, "..");
const notebook = "examples/convolution.py";
const view = "animation";
const scene = "scene.py";
const destination = join(docs, "public/exports/convolution");

interface ExportResult {
  preflight: { ok: boolean };
  runtime: string;
  view: string;
  warnings: unknown[];
}

// Studio's prepared export records the default state and the scene's reads in
// zero-python/current. renders/index.json maps each state to the bundle of
// each render and lists each bundle's files once.
interface Current {
  prepared: { inputs: Record<string, unknown>; state_fingerprint: string };
  projections: {
    renders: Record<
      string,
      { cells: Record<string, string>; outputs: Record<string, string>; values: Record<string, string> }
    >;
  };
}

interface RenderIndex {
  schema: 2;
  bundles: Record<string, { main: string; preview: string }>;
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

await mkdir(join(docs, ".vitepress/cache"), { recursive: true });
const staging = await mkdtemp(join(docs, ".vitepress/cache/exports-"));
try {
  const page = join(staging, "page");
  console.log(`Exporting ${notebook} view ${view} with the zero-python runtime`);
  const { stdout } = await run(
    "marimo-studio",
    ["view", "export", view, "--target", notebook, "--output", page, "--runtime", "zero-python", "--json"],
    { cwd: root, env: { ...process.env, NO_COLOR: "1" }, maxBuffer: 64 * 1024 * 1024 },
  );
  const result = JSON.parse(stdout) as ExportResult;
  if (result.runtime !== "zero-python" || result.view !== view || result.preflight?.ok !== true) {
    throw new Error(`The ${view} export returned an invalid result.`);
  }
  if (result.warnings.length > 0) {
    throw new Error(`The ${view} export warned:\n${JSON.stringify(result.warnings, null, 2)}`);
  }
  const document = await readFile(join(page, "index.html"), "utf8");
  if (!document.includes('<base href="./">')) {
    throw new Error("The page export has no document-relative base.");
  }

  console.log(`Exporting ${notebook} as static HTML`);
  const notebookHtml = join(staging, "notebook/index.html");
  await mkdir(join(staging, "notebook"));
  await run("marimo", ["export", "html", notebook, "--output", notebookHtml], { cwd: root });
  if (!(await readFile(notebookHtml, "utf8")).includes("<marimo-code hidden")) {
    throw new Error("The notebook export is missing its source.");
  }

  const state = join(page, "_marimo-studio/views", view);
  const current = JSON.parse(await readFile(join(state, "zero-python/current"), "utf8")) as Current;
  const index = JSON.parse(await readFile(join(state, "renders/index.json"), "utf8")) as RenderIndex;
  if (index.schema !== 2) {
    throw new Error(`The page export has render index schema ${index.schema}, expected 2.`);
  }
  const warnings = Object.values(index.states).flatMap((renders) =>
    Object.values(renders).flatMap((render) => render.warnings),
  );
  if (warnings.length > 0) {
    throw new Error(`The page export's renders warned:\n${JSON.stringify(warnings, null, 2)}`);
  }
  const id = index.states[current.prepared.state_fingerprint]?.[scene]?.bundle;
  const render = id === undefined ? undefined : index.bundles[id];
  const reads = current.projections.renders[scene];
  if (!id || !render || !reads) {
    throw new Error(`The page export has no render of ${scene} for its default state.`);
  }
  const bundle = join(state, "renders", id);
  await mkdir(join(staging, "render"));
  for (const file of [render.main, render.preview, "metadata.json"]) {
    if (!(await isFile(join(bundle, file)))) {
      throw new Error(`The default render is missing ${file}.`);
    }
    await copyFile(join(bundle, file), join(staging, "render", file));
  }

  const example = {
    inputs: current.prepared.inputs,
    movie: JSON.parse(await readFile(join(bundle, "metadata.json"), "utf8")) as Record<string, number>,
    reads: [
      ...Object.keys(reads.values).map((name) => `value("${name}")`),
      ...Object.keys(reads.outputs).map((name) => `output("${name}")`),
      ...Object.keys(reads.cells).map((name) => `cell("${name}")`),
    ],
  };
  await writeFile(join(staging, "example.json"), `${JSON.stringify(example, null, 2)}\n`);

  await rm(destination, { force: true, recursive: true });
  await mkdir(join(destination, ".."), { recursive: true });
  await rename(staging, destination);
  console.log(`Exported to ${destination}`);
} finally {
  await rm(staging, { force: true, recursive: true });
}
