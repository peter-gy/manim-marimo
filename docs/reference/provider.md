---
title: View provider
description: The manim-marimo/manim provider's starter, options, project files, renders, and diagnostics.
---

# View provider

manim-marimo registers one marimo-studio
[view provider](https://marimo-team.github.io/marimo-studio/guide/view-providers)
under the key `manim-marimo/manim`, through the `marimo_studio.view_provider`
entry point. Studio discovers it in the environment of the marimo server when
Studio starts.

## Starter

| Starter ID                     | Title           | Files                                                           |
| ------------------------------ | --------------- | --------------------------------------------------------------- |
| `manim-marimo/manim:default`   | Manim animation | `scene.py`, `index.html`, `style.css`, `player.js`, `AGENTS.md` |

`index.html` takes the view's title as its heading and lists the notebook's
output cells as `<marimo-cell>` hosts beside the player.

## Options

```toml
schema = 1
provider = "manim-marimo/manim"

[options]
quality = "preview"
```

| Option    | Values                              | Default                                                     |
| --------- | ----------------------------------- | ----------------------------------------------------------- |
| `quality` | `draft`, `preview`, `production`    | `preview` in Studio Preview, `production` in run mode and export |

## Project files

| Path                         | Role                                                         |
| ---------------------------- | ------------------------------------------------------------ |
| `index.html`                 | The page. Published.                                         |
| `*.css`, `*.js`, `assets/**` | Page assets. Published.                                      |
| `*.py`                       | Scenes and helper modules. Private to the render.            |
| Other files                  | Private to the render, such as data a scene loads            |

Studio's Source panel edits the project's HTML, CSS, JavaScript, Python, JSON,
Markdown, TOML, SVG, and YAML files, such as `states.yaml`, with syntax
highlighting.

## Renders

Each `<marimo-output render="path.py">` host on `index.html` declares a render
of that scene file. A render reads the targets of every literal `value()`,
`output()`, and `cell()` call in the scene file and in the project modules it
imports. `output()` and `cell()` accept `image/png`, `image/jpeg`, and
`image/webp`.

When an `output()` call passes `height` as a number, such as
`output("chart", height=2.6)`, the build reports that height to Studio in
points, about 99 points per scene unit. Studio then draws a matplotlib figure
or a Vega-Lite chart at that height with the notebook's aspect ratio, so its
text keeps its point size in the scene: a 10 point tick label matches
`Text(font_size=10)`. Without a literal height, the figure keeps the size the
notebook gives it.

| File            | Media type         | Role                         |
| --------------- | ------------------ | ---------------------------- |
| `animation.mp4` | `video/mp4`        | Main file, downloaded        |
| `poster.png`    | `image/png`        | Preview, the last frame      |
| `metadata.json` | `application/json` | `duration`, `fps`, `width`, `height` |

Each render runs in a worker process under Studio's command deadline, started
from the command [Availability](#availability) describes. The build
runs every declared scene once with all reads at their defaults, skipping
animation and encoding.

### Traced shapes

A render traces each shape the scene's code creates to the notebook results
it shows, and returns the shapes as Studio
[render regions](https://marimo-team.github.io/marimo-studio/reference/provider-api#locate-parts-of-rendered-files).
A shape is a region of `animation.mp4` for each run of frames in which it
keeps its box and reads, and the shapes of the last frame are regions of
`poster.png`. With [Lens](../guide/agents.md#point-at-a-shape-with-lens)
installed, Studio's preview makes each region a selection target that follows
the shape as the movie plays.

| Scene code                                                      | Region reads                         |
| --------------------------------------------------------------- | ------------------------------------ |
| `joint = np.asarray(value("joint"))` then `Rectangle(fill_opacity=joint[i, j])` | `joint[2][3]` for that rectangle |
| `for index, p in enumerate(probabilities)` then `bar.become(target)` built from `p` | `probabilities[4]` once the bar animates |
| `for i, (h, c) in enumerate(zip(heights, colors))` then `Square(color=c).set_height(h)` | `heights[1]` and `colors[1]` for that square |
| An updater that moves a dot to `path[index]`                    | `path[index]` for each frame range   |
| `output("figure")`                                              | `figure`                             |
| `bar = make(heights[0])` with a helper that returns a `Square`  | `heights[0]` for that square          |
| `label = Text(names[0]).next_to(dot, UP)`                       | `names[0]` for the label, none for the dot |
| `for index in range(len(probabilities))` then a label at `index` | None                                |

Each region names the shape's variable and class, such as `bar: Rectangle`,
and the line that created it. A statement gives its reads to the shapes it
creates and to the shapes it calls methods on, such as `dot` in
`dot.animate.move_to(...)`. A shape it only passes along, as an anchor or to
an animation, keeps its own reads. A shape shows the reads of the `play()`
call that moves it while that call writes frames. A shape that shows no read,
such as a title or an axis label, has no region, and selecting it selects the
whole movie.

The tracer evaluates index expressions made of names, integers, and
arithmetic, and keeps a shorter selector, such as `chain`, when an index
depends on anything else. A name that holds part of a `value()` read must
still hold the notebook's value of that part, so a loop name reused for
another read, or an index that moved on after the loop, drops the read.

Studio keeps 4,096 regions per render. When a scene's traced shapes need more,
adjacent regions of a shape merge into one over both time spans, the regions of
large shapes first. A shape that holds still for about half a second keeps its exact
box until every moving region has merged, so a scene that pauses on a moment
gives every shape there an exact target.

Tracing watches only project code and records the boxes of shapes at most
twelve times a second: every third frame at 30 frames per second, and every
other frame at 24. A statement that changes no
shape stops being watched after its first run.

## Diagnostics

| Code                    | Severity | Raised by  | Meaning                                                     |
| ----------------------- | -------- | ---------- | ----------------------------------------------------------- |
| `manim-input-missing`   | error    | Inspection | `index.html` is missing                                     |
| `manim-scene-missing`   | error    | Inspection | A render host names a scene file that does not exist        |
| `manim-source-invalid`  | error    | Inspection | A Python file in the project does not parse                 |
| `manim-read-dynamic`    | warning  | Inspection | A read's target is not a string literal                     |
| `manim-options-invalid` | error    | Build      | `quality` is not one of the listed values                   |
| `manim-render-failed`   | error    | Build, render | The scene raised. The message names the exception, and the location points at the deepest frame in the project. |

## Availability

Scenes render with the `manim-marimo-worker` command, which the `render` extra
installs. Studio looks for it in the notebook's pixi environment first, when
the notebook declares `[tool.pixi]` metadata and runs with `--sandbox=pixi` or
a `marimo-studio` command targets it, and then on `PATH`. Without the command,
scenes render in the Python that runs Studio.

The provider reports itself available when the worker's ManimGL imports and
imageio-ffmpeg locates an FFmpeg binary. The worker and Studio's provider read
and write the same render jobs, so both install one manim-marimo release.
Otherwise the starter is unavailable with a reason that names both versions.
`marimo-studio starters --target analysis.py` shows the availability for one
notebook:

```text
available 0.0.1 manim-marimo/manim:default
  A Manim scene, a video player, and native notebook context.
  provider manim-marimo/manim
```
