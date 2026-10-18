---
name: marimo-manim
description: >-
  Author Manim animation views of a marimo notebook with marimo-studio. Use
  when a view should animate notebook values, place notebook figures in a
  scene, or add, debug, render, or export a marimo-manim scene.
---

# Author Manim views

marimo-manim is a marimo-studio view provider. The notebook computes values
and figures. A view project holds Manim scenes that read them and a page that
plays each rendered movie beside native notebook cells. Studio renders a scene
again whenever a result it reads changes.

Read the marimo-studio skill first. It owns connecting to the notebook,
creating and editing views, building, and browser verification:

```console
pixi run agent-plugins read marimo-studio
```

This skill adds what is specific to Manim views.

## Create the view

A [pixi](https://pixi.sh/) workspace beside the notebook provides marimo-manim
with the libraries ManimGL renders with: `manimpango` from conda-forge, and on
Linux Mesa's OpenGL. Start Studio in that environment, so the notebook, the
provider, and every render share it:

```console
pixi run marimo edit notebook.py --no-sandbox --watch
```

Create the view from the provider's starter:

```python
view = await workspace.create_view("animation", starter="marimo-manim/manim:default")
await view.build()
```

The project contains `scene.py`, `index.html`, `style.css`, `player.js`, and
`AGENTS.md`. Read `AGENTS.md` before editing.

## Keep computation in the notebook

Compute every number the animation shows in notebook cells and assign it to a
named variable: point arrays, coefficients, probabilities, labels, and summary
statistics. A scene choreographs those values. It does not recompute the
analysis. Add a notebook variable when the scene needs a new shape of data,
such as a `[frames, points, 2]` array of positions.

## Read notebook results in a scene

```python
import numpy as np
from manimlib import FadeIn, Scene, ShowCreation, VMobject
from marimo_manim import output, value


class Animation(Scene):
    def construct(self):
        points = np.asarray(value("trajectory", default=[[0, 0], [1, 1]]), dtype=float)
        curve = VMobject()
        curve.set_points_as_corners(np.column_stack((points, np.zeros(len(points)))))
        self.play(ShowCreation(curve), run_time=3)
        chart = output("trajectory_figure", height=3)
        if chart is not None:
            self.play(FadeIn(chart.to_corner()))
        self.wait(0.5)
```

| Read                                         | Returns                                                     |
| -------------------------------------------- | ----------------------------------------------------------- |
| `value(selector, *, default=None)`           | The JSON form: arrays as nested lists, tables as row lists  |
| `output(selector, *, default=None, **image)` | A notebook value, such as a matplotlib figure, as an image  |
| `cell(name, *, default=None, **image)`       | A named cell's output as an image, when marimo shows one    |

Rules that inspection and the build enforce:

- Write every target as a string literal. A computed target reports
  `manim-read-dynamic` and always returns its default.
- Give every read a default the scene can render. The build runs each scene
  with every read at its default, and a failure there fails the build at the
  scene's line.
- A scene file defines exactly one `manimlib.Scene` subclass. Helper modules in
  the project can hold base classes and shared mobjects, and their reads count
  toward the scenes that import them.
- Use `Text` for labels. `Tex` and `MathTex` need a LaTeX installation on the
  machine that renders.
- Place figures with a literal height, such as `output("chart", height=2.6)`.
  Studio draws the figure at that height, so its text reads at the scene's own
  font sizes.

## Shapes trace to notebook results

Each render records which read every shape shows, and Studio's preview makes
the shapes Lens targets. Keep the trace precise: bind each read to a name,
index it with names, integers, and arithmetic, such as `joint[i, j]`, and walk
it with `enumerate()` and `zip()`. A Lens selection on a shape names its
variable and class, such as `bar: Rectangle`, the read it shows, such as
`probabilities[4]`, and the scene line that created it. Change the
choreography at that line, or the notebook cell behind the read when the
number itself is wrong.

## Show scenes on the page

Each `<marimo-output render="scene.py">` host on `index.html` renders that
scene file. Add a scene file and a host to show a second animation. The markup
inside the host is the player that `player.js` fills from the host's
`marimoRender` record. Keep controls and supporting outputs in
`<marimo-cell name="...">` hosts beside the movie.

Set `quality` in `view.toml` to `draft` while iterating on choreography.
Remove it to use `preview` in Studio Preview and `production` for run mode and
export.

## Verify

Build, then check every render host in the preview:

```python
build = await view.build()
inspection = await view.inspect()
print(build.revision, inspection.freshness, inspection.diagnostics)
print(await view.preview_url(runtime="server"))
```

In the browser, wait for each `marimo-output[render]` to reach
`data-state="ready"`. Its `marimoRender.absent` lists the reads that rendered
at their defaults, which usually means a misspelled selector or a figure
without an image form. Seek the video to its last frame and look at it: a
render that succeeds can still overlap labels or place a figure off screen.
Change a notebook control and confirm the host passes through `stale` and
shows a new movie.

For a static export, list every value each control can send in `states.yaml`
beside `view.toml`. `marimo-studio view preflight animation` warns with
`prepared-states-skip-control-values` for each control whose values the states
skip.

| Symptom                                        | Cause and repair                                                         |
| ---------------------------------------------- | ------------------------------------------------------------------------ |
| Build fails at a scene line                    | The scene fails with defaults. Give the read a renderable default.       |
| `manim-scene-missing` at a host in `index.html` | The host names a scene file that does not exist.                         |
| `Found none` or `Found A, B` in a render error | The file defines no Scene subclass, or two unrelated ones.               |
| Host stays `stale` for a long time             | The scene renders slowly. Use `quality = "draft"` or shorten `run_time`. |
| OpenGL errors on Linux                         | Add Mesa to the pixi workspace and start Studio through `pixi run`.      |
