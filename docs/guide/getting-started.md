---
title: Getting started
description: Install manim-marimo, add an Animation view to a notebook, and watch it render from notebook values.
---

# Getting started

manim-marimo adds a **Manim animation** starter to
[marimo-studio](https://marimo-team.github.io/marimo-studio/). Studio builds
named views of a [marimo](https://marimo.io/) notebook, and manim-marimo's
views render [ManimGL](https://github.com/3b1b/manim) scenes from the
notebook's values.

## Install

ManimGL renders with OpenGL, draws text with Pango, and encodes video with
FFmpeg. manim-marimo renders scenes in the notebook's
[pixi](https://pixi.sh/) environment, where conda-forge provides those
libraries on macOS and Linux. Declare the environment in the notebook's script
metadata, the `# /// script` block at the top of `analysis.py`:

```python
# /// script
# requires-python = ">=3.10,<3.15"
# dependencies = [
#     "manim-marimo[render]",
# ]
#
# [tool.pixi.workspace]
# channels = ["conda-forge"]
# platforms = ["linux-64", "linux-aarch64", "osx-64", "osx-arm64"]
#
# [tool.pixi.dependencies]
# manimpango = ">=0.6"
#
# [tool.pixi.target.linux.dependencies]
# mesalib = ">=25"
# libegl = ">=1.7"
# libgl = ">=1.7"
# fonts-conda-ecosystem = "*"
# ///
```

| Table                                 | Installs                                                                     |
| ------------------------------------- | ---------------------------------------------------------------------------- |
| `dependencies`                        | manim-marimo, and through its `render` extra ManimGL and FFmpeg              |
| `tool.pixi.workspace`                 | conda-forge as the channel, and the platforms pixi solves for                |
| `tool.pixi.dependencies`              | manimpango, ManimGL's text renderer, built against Pango                     |
| `tool.pixi.target.linux.dependencies` | [Mesa](https://mesa3d.org/)'s software OpenGL and fonts                      |

macOS provides OpenGL itself. On Linux, manim-marimo renders through Mesa's EGL
driver when no display is set, so scenes render on servers without a GPU.

## Add an Animation view

Open the notebook in a [pixi sandbox](https://marimo.io/blog/pixi-sandboxes),
with Studio and manim-marimo in the marimo server:

```sh
uvx --with manim-marimo marimo edit analysis.py --sandbox=pixi --watch
```

[uv](https://docs.astral.sh/uv/)'s `uvx` runs marimo with manim-marimo and
Studio, and needs `pixi` on `PATH`. `--sandbox=pixi` installs the notebook's
environment and runs its kernel there. Studio runs the commands views need from
the same environment first, so every scene renders with the ManimGL, Pango, and
Mesa the metadata declares. The first start downloads Python and those
libraries.

Click **Add view**, choose **Manim animation**, and create the view. Or create
it from a terminal:

```sh
uvx --with manim-marimo \
  marimo-studio view create animation --target analysis.py \
  --starter manim-marimo/manim:default
```

Studio writes the view project beside the notebook:

```text
studio/analysis/animation/
  view.toml     provider = "manim-marimo/manim"
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
from manim_marimo import value


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
