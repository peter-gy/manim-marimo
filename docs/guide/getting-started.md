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

Add marimo-manim to the environment that runs the notebook. It brings
marimo-studio and ManimGL with it:

```sh
uv add "marimo-manim @ git+https://github.com/peter-gy/marimo-manim"
```

[uv](https://docs.astral.sh/uv/) is the Python package manager these pages use.
Rendering needs an [OpenGL](https://www.opengl.org/) context, which macOS
provides. On a Linux server, run Studio under `xvfb-run -a` as
[Run and export](./run-and-export.md#linux-servers) describes. The video
encoder comes from [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg).

## Add an Animation view

Open the notebook with Studio:

```sh
uv run marimo edit analysis.py --watch
```

Click **Add view**, choose **Manim animation**, and create the view. Or create
it from a terminal:

```sh
uv run marimo-studio view create animation --target analysis.py \
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
