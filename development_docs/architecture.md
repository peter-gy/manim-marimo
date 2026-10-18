# Architecture

manim-marimo is one marimo-studio view provider, registered under the
`marimo_studio.view_provider` entry point as `manim-marimo/manim`. Studio
discovers it in the marimo server's environment and calls it through the public
`marimo_studio.view_providers` SDK. Every Studio import comes from that
module, which `check_provider` verifies.

## Modules

| Module                         | Owns                                                                  |
| ------------------------------ | --------------------------------------------------------------------- |
| `manim_marimo/__init__.py`     | The scene-facing API: `value`, `output`, `cell`                       |
| `manim_marimo/_reads.py`       | `SceneReads` and the context variable that binds reads during a render |
| `manim_marimo/_provider.py`    | `ManimProvider`: starters, inspection, build, render                  |
| `manim_marimo/_render.py`      | `SceneJob` and `run_scene`, the provider side of the worker protocol  |
| `manim_marimo/_worker.py`      | The worker process that imports a scene and drives ManimGL            |
| `manim_marimo/_lineage.py`     | Traces shapes to the reads they show and records their boxes per frame |
| `manim_marimo/starters/default` | Files of the `manim-marimo/manim:default` starter                     |

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
   `.manim-marimo/video.json` with the resolution and frame rate of the
   selected quality. It then runs every declared scene once in check mode, so a
   scene that fails with its defaults fails the build and Studio keeps the last
   published view. It returns `output_sizes` for each `output()` call with a
   literal `height`, converted from scene units to points at the scale of
   ManimGL's `Text`, so Studio draws those figures at the size they appear.
3. `render()` writes the request's values as `.manim-marimo/reads/values.json`
   and each output and cell image beneath `.manim-marimo/reads/` in its private
   template copy, then runs the scene in render mode. It returns the shapes
   the worker traced as `RenderRegion` records of the movie and the poster.
4. Studio publishes `animation.mp4`, `poster.png`, and `metadata.json`, and
   the page's render host receives them as a `marimoRender` record. Studio
   admits each region that names a read of the render, and Preview makes it a
   Lens target.

## Worker protocol

`run_scene()` writes a `SceneJob` as `job.json` in a work directory and starts
`manim-marimo-worker job.json` through `request.runner`. The
runner owns the deadline, output limits, and cancellation, so Studio can stop a
render whose inputs changed by ending the worker.

The provider and the worker can live in different environments. The server's
environment needs only the base package, which registers the provider. The
`render` extra installs ManimGL and FFmpeg with the `manim-marimo-worker`
script. Studio's `find_tool` resolves that script in the notebook's pixi
environment first, then on `PATH`, so a notebook opened with `--sandbox=pixi`
renders with the conda-forge Pango and Mesa its metadata declares. Without the
script, the provider starts `python -I -m manim_marimo._worker` with its own
interpreter. `availability()` probes `manim-marimo-worker --version`, which
prints the worker's release once ManimGL and FFmpeg import, and requires the
provider's release, because both sides share the `SceneJob` format.

The worker:

1. On Linux without a display, points glcontext and libglvnd at Mesa in its
   own interpreter's prefix, since script environments run without
   activation.
2. Writes a ManimGL config with its cache beneath the work directory, then
   imports `manimlib`. ManimGL parses `sys.argv` at import, so the worker sets
   it first.
3. Imports the scene file as a module and selects the one `Scene` subclass the
   file defines that no other class in the file extends.
4. Binds `SceneReads` while it imports and runs the scene, so module-level
   reads and `construct()` see the same values.
5. In render mode, encodes the movie, rewrites it with `+faststart` so browsers
   stream it, renames the last frame to `poster.png`, and writes
   `metadata.json`. In check mode, it skips animations and encoding.
6. Writes `report.json` with an error message and the deepest stack frame
   inside the template, so diagnostics point at the author's file and line.
7. In render mode, writes `lineage.json` with the traced shapes, which
   `render()` returns as `RenderRegion` records of the movie and the poster.

`SceneLineage` traces in two halves. A static pass over each project file
binds local names to the reads they hold, such as `joint` for
`np.asarray(value("joint"))` and `probabilities[index]` for the item of
`enumerate(probabilities)`. Tuple assignments and `zip()` pair their items, so
`for i, (h, c) in enumerate(zip(heights, colors))` binds `h` to `heights[i]`
alone. A size such as `len(probabilities)` or a `range()` holds no read, so
shapes it places stay untraced. Indexing a read selects a part of it, so the
reads that computed the index stay out, while indexing a constant, as in
`PALETTE[status]`, passes the index's reads on. Lambdas and function
parameters hide the outer names they share. Each bound read remembers the
statement that bound its name.

Each statement compiles once into a `_Plan`: its reads, the names it assigns,
the shapes it calls methods on, the shapes it copies, and the names with
several binding statements that it binds. Methods that return another object
or only read, such as `copy()`, `get_center()`, or `c2p()`, and methods that
place shapes, such as `add()` and `arrange()`, leave their shape's reads alone.

While the scene runs, a line tracer watches only project code, through
`sys.monitoring` on Python 3.12 and newer and `sys.settrace` before. A
statement's first line event starts it, and its later lines continue it. On
that event the tracer reads the frame's locals once and evaluates the plan's
reads:

- A read through a name that several statements bind counts only when the
  statement that last ran for that name bound it. An updater or comprehension
  checks the frame that encloses it, and once that frame returns, the bindings
  it ended with.
- A read through a name that holds a part of a `value()` read counts only when
  the name still holds the notebook's value of that part, which the worker
  passes in. A loop name reused for another read, or an index that moved on,
  drops the read.
- A read through a name that holds a shape is that shape's own lineage.

The shapes a statement calls methods on exist before it runs, so the tracer
gives each one the reads of its own calls on that event, before any frame a
`play()` call writes, and those reads replace the reads of changes in earlier
frames. A `run_time` or another argument outside the shape's calls stays off
it.
An assignment waits for the next event in its frame, then names the shapes it
bound and gives a shape created during the statement, such as one a helper
builds in `bar = make(heights[0])`, the statement's reads. A copy takes the
reads of the shape it copies. A wrapped `Mobject.__init__` gives each new shape
the reads of the statement that created it.

A line that never changes a shape stops reporting itself: a statement whose
calls on shapes read nothing and that assigns nothing, or an assignment that
bound no shape in sixteen runs. A loop header keeps reporting while its body
holds a statement that can change a shape, because each pass starts there. A
one-line compound statement, such as `if test: shape.set_fill(p)`, maps its
line to its header, so its body changes no shape. A call in a branch of a
conditional expression changes no shape either. A debugger or coverage tool that owns `sys.settrace` keeps it,
and that run records where each shape was created.

The wrapped `emit_frame()` records boxes every `ceil(fps / 12)` frames, at most
twelve times a second, and each run lasts until the next recorded frame. It
records the box of every shape in the scene that shows a read, relative to the
camera frame, except the parts a line creates with a shape that shows reads of
its own, because Studio drops a region without reads. After the scene runs,
the worker records the shapes of its final state for the poster. A frame from a
camera turned out of the scene's plane records no boxes. A tracing error,
including one in the creation hook, stops the tracer and leaves the render
unchanged.

Studio keeps 4,096 regions per render, and a static export's page loads every
state's regions, so `records()` keeps a render's lineage under 4,000 regions
and 1 MB. A shape that moves on every frame has a run per recorded frame, so
while the records exceed either bound, each shape's adjacent runs merge pairwise
into one run with the union of their boxes and reads. The movie keeps a target
for every shape on every frame, with coarser boxes. When merging cannot fit the
bounds, the longest runs stay.

`run_scene()` raises `RenderFailure` from that report, and the provider turns
it into a `ProviderError` with code `manim-render-failed`.

## Files a render writes

| Path                       | Where              | Purpose                                 |
| -------------------------- | ------------------ | --------------------------------------- |
| `.manim-marimo/video.json` | Template           | Resolution and frame rate from the build |
| `.manim-marimo/reads/`     | Render template copy | Values JSON and read images            |
| `.manim-marimo/work/`      | Render template copy | Job, report, ManimGL config and cache  |
| `animation.mp4`            | Render output root | The published movie                     |
| `poster.png`               | Render output root | The last frame, shown before playback   |
| `metadata.json`            | Render output root | Duration, frame rate, and resolution    |
| `.manim-marimo/work/lineage.json` | Render template copy | Traced shapes by frame range and on the last frame |

Build checks keep their work directories beneath `request.work_root`, so the
published template holds only project files and `video.json`.
