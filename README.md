# marimo-manim

marimo-manim brings [Manim](https://github.com/3b1b/manim) animations to
[marimo](https://marimo.io/) notebooks through
[marimo-studio](https://marimo-team.github.io/marimo-studio/). The notebook
computes the values. A Manim scene in a Studio view animates them, and Studio
renders the movie again whenever a value changes.

<p align="center">
  <img alt="Rotating vectors drawing a heart, rendered from Fourier coefficients a marimo notebook computes" src="docs/public/media/fourier.webp" width="100%">
</p>

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
```

`trajectory` is a variable in the notebook. The view's page plays the movie
beside the notebook's live controls, and `output()` and `cell()` place notebook
figures inside the scene.

## Get started

```sh
uv add "marimo-manim @ git+https://github.com/peter-gy/marimo-manim"
uv run marimo edit analysis.py
```

In Studio, click **Add view** and choose **Manim animation**.
[Getting started](https://peter-gy.github.io/marimo-manim/guide/getting-started)
walks through a first animation.

## Author with a coding agent

marimo-manim ships an agent skill beside marimo-studio's. Paste this into
Claude Code, Codex, or another terminal agent:

```text
Run `uv run agent-plugins read marimo-studio` and
`uv run agent-plugins read marimo-manim`, then create a notebook that
explains Fourier series and an Animation view that draws a square wave
from rotating vectors.
```

## Examples

- [Fourier drawing](https://peter-gy.github.io/marimo-manim/examples/fourier):
  rotating vectors and a spectrum from Fourier coefficients.
- [Convolution of dice](https://peter-gy.github.io/marimo-manim/examples/convolution):
  a joint probability table folding into the distribution of a sum, ending on
  the notebook's own chart.

```sh
pixi run edit fourier
```

## Documentation

[Guide](https://peter-gy.github.io/marimo-manim/guide/getting-started) ·
[Examples](https://peter-gy.github.io/marimo-manim/examples/) ·
[Reference](https://peter-gy.github.io/marimo-manim/reference/python-api) ·
[Contributing](CONTRIBUTING.md)

## License

[Apache License 2.0](LICENSE).
