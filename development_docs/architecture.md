# Architecture

marimo-manim is one marimo-studio view provider, registered under the
`marimo_studio.view_provider` entry point as `marimo-manim/manim`. Studio
discovers it in the notebook's environment and calls it through the public
`marimo_studio.view_providers` SDK. Every Studio import comes from that
module, which `check_provider` verifies.

## Modules

| Module                         | Owns                                                                  |
| ------------------------------ | --------------------------------------------------------------------- |
| `marimo_manim/__init__.py`     | The scene-facing API: `value`, `output`, `cell`                       |
| `marimo_manim/_reads.py`       | `SceneReads` and the context variable that binds reads during a render |
| `marimo_manim/_provider.py`    | `ManimProvider`: starters, inspection, build, render                  |
| `marimo_manim/_render.py`      | `SceneJob` and `run_scene`, the provider side of the worker protocol  |
| `marimo_manim/_worker.py`      | The worker process that imports a scene and drives ManimGL            |
| `marimo_manim/starters/default` | Files of the `marimo-manim/manim:default` starter                     |

## Provider lifecycle

Studio calls the provider in four steps. Each step reads the view project from
disk, and only `render()` sees notebook results.

1. `inspect()` lists Source documents and build inputs, finds page projection
   sites with `html_sites`, and declares one `Render` per
   `<marimo-output render="*.py">` host on `index.html`. It parses every Python
   file with `ast` and attributes literal `value()`, `output()`, and `cell()`
   calls to each scene through the project modules the scene imports. It never
   executes project code.
2. `build()` copies the page, styles, scripts, and `public/` into the staging
   root, and everything else into the private render template. It writes
   `.marimo-manim/video.json` with the resolution and frame rate of the
   selected quality. It then runs every declared scene once in check mode, so a
   scene that fails with its defaults fails the build and Studio keeps the last
   published view.
3. `render()` writes the request's values as `.marimo-manim/reads/values.json`
   and each output and cell image beneath `.marimo-manim/reads/` in its private
   template copy, then runs the scene in render mode.
4. Studio publishes `animation.mp4`, `poster.png`, and `metadata.json`, and
   the page's render host receives them as a `marimoRender` record.

## Worker protocol

`run_scene()` writes a `SceneJob` as `job.json` in a work directory and starts
`python -I -m marimo_manim._worker job.json` through `request.runner`. The
runner owns the deadline, output limits, and cancellation, so Studio can stop a
render whose inputs changed by ending the worker.

The worker:

1. Writes a ManimGL config with its cache beneath the work directory, then
   imports `manimlib`. ManimGL parses `sys.argv` at import, so the worker sets
   it first.
2. Imports the scene file as a module and selects the one `Scene` subclass the
   file defines that no other class in the file extends.
3. Binds `SceneReads` while it imports and runs the scene, so module-level
   reads and `construct()` see the same values.
4. In render mode, encodes the movie, rewrites it with `+faststart` so browsers
   stream it, renames the last frame to `poster.png`, and writes
   `metadata.json`. In check mode, it skips animations and encoding.
5. Writes `report.json` with an error message and the deepest stack frame
   inside the template, so diagnostics point at the author's file and line.

`run_scene()` raises `RenderFailure` from that report, and the provider turns
it into a `ProviderError` with code `manim-render-failed`.

## Files a render writes

| Path                       | Where              | Purpose                                 |
| -------------------------- | ------------------ | --------------------------------------- |
| `.marimo-manim/video.json` | Template           | Resolution and frame rate from the build |
| `.marimo-manim/reads/`     | Render template copy | Values JSON and read images            |
| `.marimo-manim/work/`      | Render template copy | Job, report, ManimGL config and cache  |
| `animation.mp4`            | Render output root | The published movie                     |
| `poster.png`               | Render output root | The last frame, shown before playback   |
| `metadata.json`            | Render output root | Duration, frame rate, and resolution    |

Build checks keep their work directories beneath `request.work_root`, so the
published template holds only project files and `video.json`.
