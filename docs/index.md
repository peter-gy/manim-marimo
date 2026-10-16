---
layout: home
title: marimo-manim
titleTemplate: false
description: Manim animations of marimo notebook results, rendered as marimo-studio views.
hero:
  name: marimo-manim
  text: Animate marimo notebooks with Manim
  tagline: >-
    The notebook computes. A Manim scene animates the result. marimo-studio
    renders the movie beside the notebook's live controls, and renders it
    again when a value changes.
  actions:
    - theme: brand
      text: Get started
      link: /guide/getting-started
    - theme: alt
      text: Examples
      link: /examples/
---

<figure class="hero-figure">
  <img class="only-light" src="/media/hero-light.webp" alt="A marimo notebook beside its Animation view. The view's Manim movie fills the diagonals of the notebook's joint probability table and places the notebook's matplotlib chart in the scene. Dragging the notebook's bias slider toward six renders the movie again for the new distribution.">
  <img class="only-dark" src="/media/hero-dark.webp" alt="">
</figure>

## Notebook results in a scene

The [convolution example](./examples/convolution.md) computes a joint
probability table and a chart in the notebook. Its scene reads both by name:

```python
import numpy as np
from marimo_manim import output, value

FAIR = np.full(6, 1 / 6)
joint = np.asarray(
    value("joint", default=np.outer(FAIR, FAIR).tolist()), dtype=float
)
chart = output("distribution_figure", height=2.6)
```

Studio finds these reads in the scene's source, captures the results from the
notebook, and renders the movie again when the bias slider moves.

## Ask a coding agent

From the pixi workspace of a notebook with marimo-manim, paste this into Claude
Code, Codex, or another terminal agent:

```text
Run `pixi run agent-plugins read marimo-studio` and
`pixi run agent-plugins read marimo-manim`, then create a notebook that
explains Fourier series and an Animation view that draws a square wave
from rotating vectors.
```

## Read on

<nav class="routes">
  <a href="./guide/getting-started"><strong>Getting started</strong><span>Install marimo-manim in a pixi workspace and add an Animation view.</span></a>
  <a href="./guide/scenes"><strong>Scenes and notebook results</strong><span>Read values with <code>value()</code>, and place figures with <code>output()</code> and <code>cell()</code>.</span></a>
  <a href="./guide/pages"><strong>Pages and players</strong><span>Play several scenes on one page beside native marimo cells.</span></a>
  <a href="./guide/agents"><strong>Author with agents</strong><span>Let a coding agent write the notebook, the scenes, and the page.</span></a>
  <a href="./guide/run-and-export"><strong>Run and export</strong><span>Serve views live, export static sites, and render on Linux servers.</span></a>
  <a href="./reference/python-api"><strong>Python API</strong><span>The contract of <code>value()</code>, <code>output()</code>, and <code>cell()</code>.</span></a>
</nav>
