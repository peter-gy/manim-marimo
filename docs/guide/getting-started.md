---
title: Getting started
description: Install marimo-manim, add an Animation view to a notebook, and watch it render from notebook values.
---

# Getting started

marimo-manim adds a **Manim animation** starter to
[marimo-studio](https://marimo-team.github.io/marimo-studio/). Studio builds
named views of a [marimo](https://marimo.io/) notebook, and marimo-manim's
views render [ManimGL](https://github.com/3b1b/manim) scenes from the
notebook's values.

## Install

ManimGL renders with OpenGL, draws text with Pango, and encodes video with
FFmpeg. [pixi](https://pixi.sh/), the conda package manager, installs Python,
those libraries, and marimo-manim into one environment on macOS and Linux.
Put this `pixi.toml` beside the notebook:

```toml
[workspace]
name = "analysis"
channels = ["conda-forge"]
platforms = ["linux-64", "linux-aarch64", "osx-64", "osx-arm64"]

[dependencies]
python = ">=3.10,<3.15"
manimpango = ">=0.6"

[pypi-dependencies]
marimo-manim = { git = "https://github.com/peter-gy/marimo-manim" }

[target.linux.dependencies]
mesalib = ">=25"
libegl = ">=1.7"
libgl = ">=1.7"
fonts-conda-ecosystem = "*"

[target.linux.activation.env]
GLCONTEXT_LINUX_LIBGL = "$CONDA_PREFIX/lib/libGL.so.1"
GLCONTEXT_LINUX_LIBEGL = "$CONDA_PREFIX/lib/libEGL.so.1"
__EGL_VENDOR_LIBRARY_DIRS = "$CONDA_PREFIX/share/glvnd/egl_vendor.d"
```

| Table                         | Installs                                                                 |
| ----------------------------- | ------------------------------------------------------------------------ |
| `dependencies`                | Python 3.10 to 3.14 and manimpango, ManimGL's text renderer, built against Pango |
| `pypi-dependencies`           | marimo-manim, with marimo, marimo-studio, ManimGL, and FFmpeg            |
| `target.linux.dependencies`   | [Mesa](https://mesa3d.org/)'s software OpenGL and fonts                  |
| `target.linux.activation.env` | The paths ManimGL's OpenGL loader opens Mesa from                        |

macOS provides OpenGL itself. On Linux, marimo-manim renders through Mesa's EGL
driver when no display is set, so scenes render on servers without a GPU.

## Add an Animation view

Open the notebook with Studio in the workspace's environment:

```sh
pixi run marimo edit analysis.py --no-sandbox --watch
```

Studio runs the notebook, its views, and every render in this environment.
Start it inside the workspace: Studio renders scenes in the server's own
environment, which a [pixi sandbox](https://marimo.io/blog/pixi-sandboxes)
started with `--sandbox=pixi` provides to the kernel alone.

Click **Add view**, choose **Manim animation**, and create the view. Or create
it from a terminal:

```sh
pixi run marimo-studio view create animation --target analysis.py \
  --starter marimo-manim/manim:default
```

Studio writes the view project beside the notebook:

```text
studio/analysis/animation/
  view.toml     provider = "marimo-manim/manim"
  scene.py      the Manim scene
  index.html    the page that plays the movie
  style.css
  player.js
  AGENTS.md     instructions for coding agents
```

Notebook and Preview open side by side, and Preview plays the starter's
animation.

## Animate a notebook value

Give the notebook a value to animate, such as a random walk:

```python
@app.cell
def walk(np):
    steps = np.random.default_rng(7).normal(size=(60, 2)) * 0.3
    trajectory = steps.cumsum(axis=0)
    return (trajectory,)
```

Read it in `scene.py` with `value()`:

```python
import numpy as np
from manimlib import Scene, ShowCreation, VMobject
from marimo_manim import value


class Animation(Scene):
    def construct(self):
        points = np.asarray(value("trajectory", default=[[0, 0], [1, 1]]), dtype=float)
        curve = VMobject()
        curve.set_points_as_corners(np.column_stack((points, np.zeros(len(points)))))
        self.play(ShowCreation(curve), run_time=3)
        self.wait(0.5)
```

Save the scene. Studio builds the view, renders the scene with the notebook's
`trajectory`, and Preview plays the new movie. Run the `walk` cell with another
seed, and the movie renders again.

## Next steps

- [Scenes and notebook results](./scenes.md) covers `value()`, `output()`,
  and `cell()`.
- [Pages and players](./pages.md) puts several scenes and notebook controls on
  one page.
- [Author with agents](./agents.md) lets a coding agent write the notebook and
  the scenes.
