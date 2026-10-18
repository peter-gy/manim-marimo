---
title: Scenes and notebook results
description: Read notebook values, figures, and cell outputs in a Manim scene, and give every read a default.
---

# Scenes and notebook results

A scene is a Python file in the view project that defines one
`manimlib.Scene` subclass. It reads notebook results through three functions
from `marimo_manim`:

```python
from manimlib import DOWN, FadeIn, Scene, Text
from marimo_manim import output, value


class Summary(Scene):
    def construct(self):
        mean = float(value("summary.mean", default=0))
        self.play(FadeIn(Text(f"Mean {mean:.2f}")))
        chart = output("distribution_figure", height=3)
        if chart is not None:
            self.play(FadeIn(chart.to_edge(DOWN)))
        self.wait(1)
```

| Read                                         | Returns                                                                 |
| -------------------------------------------- | ----------------------------------------------------------------------- |
| `value(selector, *, default=None)`           | The value's JSON form                                                   |
| `output(selector, *, default=None, **image)` | The value as an `ImageMobject`, such as a matplotlib figure             |
| `cell(name, *, default=None, **image)`       | The output of the cell called `name` as an `ImageMobject`               |

Studio renders the scene again whenever one of these results changes in the
notebook.

## Values

`value()` returns what [marimo-export](https://marimo-team.github.io/marimo-export/reference/python/values)
produces for the notebook variable:

| Notebook value                  | Scene receives                 |
| ------------------------------- | ------------------------------ |
| NumPy array                     | Nested lists of numbers        |
| pandas or polars DataFrame      | A list of row objects          |
| `datetime.date`                 | ISO 8601 text                  |
| `mo.ui` element, such as a slider | Its current value through `name.value` |

Selectors reach into values with dots and indexes, such as `summary.mean`,
`shape.value`, or `points[0]`. Wrap a value in `np.asarray()` to animate it.

## Figures and cell outputs

`output()` reads a notebook value as an image. Studio draws a matplotlib figure
as a PNG, and the scene receives an `ImageMobject`. Keyword arguments such as
`height` pass through to `ImageMobject`. A literal `height`, such as
`output("distribution_figure", height=2.6)`, also sets the size Studio draws
the figure at, so its tick labels read at the scene's own font sizes.

`cell()` reads the rendered output of a named cell. Name a cell by its
function, `def distribution_chart():`. A cell whose last expression is a figure
arrives as that figure. A cell that shows text, a table, or a layout of several
outputs has no image form and returns `default`.

## Defaults

Every read returns its `default` when the notebook has not computed the
result, when an output or cell has no image form, and when the scene runs
outside Studio, for example with `manimgl scene.py`. A present `None` value
stays `None`.

The build runs each scene with every read at its default, skipping animation.
A scene that fails there fails the build at its own line, and Studio keeps the
last published view. Give each read a default the scene can render:

```python
circle = [[[0, 0], [np.cos(t), np.sin(t)]] for t in np.linspace(0, 2 * np.pi, 61)]
chain = np.asarray(value("chain", default=circle), dtype=float)
```

## How Studio finds the reads

Studio reads the scene's source without running it and records every literal
target. Write each target as a string literal. A computed target, such as
`value(name)`, reports `manim-read-dynamic` and always returns its default.

A scene's reads include those in project modules it imports. Shared helpers can
live beside the scenes:

```text
studio/analysis/animation/
  scene.py        from helpers import axes_for
  helpers.py      reads value("bounds")
```

A change to `bounds` renders `scene.py` again, and leaves scenes that do not
import `helpers` untouched.

## Shapes that trace to their results

Each render records which notebook result every shape shows, so a reader can
select a shape in Studio's preview and reach the cell that computed it. The
tracer follows a read through the names it is bound to and the indexes the
scene takes of it:

```python
joint = np.asarray(value("joint"), dtype=float)
for i in range(6):
    for j in range(6):
        square = Rectangle(fill_opacity=joint[i, j])  # traces to joint[i][j]

for diagonal, probability in enumerate(probabilities):
    target = bars[diagonal].copy().set_height(probability * 12)
    bars[diagonal].become(target)  # traces to probabilities[diagonal]
```

Bind each read to a name, index it with names, integers, and arithmetic, and
walk it with `enumerate()` and `zip()`, so each shape names the cell of the
table it shows.
[Traced shapes](../reference/provider.md#traced-shapes) lists what the tracer
records.

## Scenes with many shapes

A scene that moves hundreds of shapes spends its render in Python, once per
frame. The [epidemic example](../examples/epidemic.md) moves two hundred people
through a 19-second movie at 1080p and 30 frames per second, and renders it in
less time than it plays, by keeping that Python small:

- Compute every position of a frame at once with NumPy, then move each shape
  in one loop of `move_to()` calls inside a single updater.
- Change a shape's color, a ring, or a link only when its state changes, and
  update the few that are active.
- Set a `DecimalNumber` or `Integer` only when the number it shows changes.
  Each new value redraws its glyphs.

Tracing records the boxes of the moving shapes at most twelve times a second,
so a higher frame rate does not multiply its cost.

## One scene per file

The file's scene is the one `Scene` subclass it defines that no other class in
the file extends. A base class in the same file, or in an imported helper,
stays available:

```python
class Styled(Scene):
    default_camera_config = {"background_color": "#ffffff"}


class Animation(Styled):
    def construct(self): ...
```

Put a second animation in its own file and show it with its own render host.

## LaTeX

`Text` renders with system fonts. `Tex` and `MathTex` call a
[LaTeX installation](https://3b1b.github.io/manim/getting_started/installation.html)
on the machine that renders the scene.
