---
title: Python API
description: The functions a Manim scene calls to read notebook results.
---

# Python API

```python
from marimo_manim import cell, output, value
```

Each function reads one notebook result while Studio renders the scene. Write
the target as a string literal: Studio finds the call in the scene's source and
records the target before it renders. Outside a render, every call returns its
`default`.

## `value(selector, /, *, default=None)`

Returns the JSON form of the notebook value `selector` names.

- `selector`: a notebook variable, optionally followed by attributes and
  indexes, such as `"spectrum"`, `"summary.mean"`, `"shape.value"`, or
  `"points[0]"`.
- `default`: returned when the notebook has not computed the value and outside
  a render.

Arrays arrive as nested lists, tables as lists of row objects, and dates as
ISO 8601 text. A present `None` returns `None`.

```python
radii = np.asarray(value("radii", default=[1]), dtype=float)
```

## `output(selector, /, *, default=None, **image)`

Returns the notebook value `selector` names as a `manimlib.ImageMobject`.

- `selector`: as for `value()`, naming a value with an image form, such as a
  matplotlib figure.
- `default`: returned when the value is absent, has no image form, and outside
  a render.
- `**image`: keyword arguments for `ImageMobject`, such as `height=3`.

```python
chart = output("distribution_figure", height=2.6)
if chart is not None:
    self.play(FadeIn(chart))
```

## `cell(name, /, *, default=None, **image)`

Returns the rendered output of the notebook cell called `name` as a
`manimlib.ImageMobject`.

- `name`: the cell's name, the function name in `def distribution_chart():`.
- `default`: returned when the cell has not run, when its output is text, a
  table, or a layout, and outside a render.
- `**image`: keyword arguments for `ImageMobject`.

The output arrives as marimo shows it, so a cell that ends with a matplotlib
figure places that figure.
