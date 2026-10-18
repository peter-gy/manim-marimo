---
layout: home
title: manim-marimo
titleTemplate: false
description: Manim animations of marimo notebook results, rendered as marimo-studio views.
hero:
  name: manim-marimo
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

## Two hundred people, traced

The [epidemic example](./examples/epidemic.md) simulates a city of two hundred
people in the notebook, after 3Blue1Brown's *Simulating an epidemic*. The scene
plays the infection spreading person to person. Pause the movie and point at
anyone: it names the row of the notebook's `people` table behind that dot, the
cell that computed it, and the line of `scene.py` that drew it.

<div class="wide">
<ManimExample
  name="epidemic"
  notebook="examples/epidemic.py"
  scene="examples/studio/epidemic/animation/scene.py"
  stage="movie"
>

<<< ../examples/studio/epidemic/animation/scene.py{python:line-numbers}

</ManimExample>
</div>

## Notebook results in a scene

The [convolution example](./examples/convolution.md) computes a joint
probability table and a chart in the notebook. Its scene reads both by name:

```python
import numpy as np
from manim_marimo import output, value

FAIR = np.full(6, 1 / 6)
joint = np.asarray(
    value("joint", default=np.outer(FAIR, FAIR).tolist()), dtype=float
)
chart = output("distribution_figure", height=2.6)
```

Studio finds these reads in the scene's source, captures the results from the
notebook, and renders the movie again when the bias slider moves. The
[example page](./examples/convolution.md) embeds the notebook, the scene, the
movie, and the exported page.

## Ask a coding agent

Paste this into Claude Code, Codex, or another terminal agent, from the folder
of the notebook:

```text
Read the marimo-studio and manim-marimo skills with
`uvx --with "manim-marimo @ git+https://github.com/peter-gy/manim-marimo" agent-plugins read <name>`,
then create a notebook that explains Fourier series and an Animation view
that draws a square wave from rotating vectors.
```

## Read on

<nav class="routes">
  <a href="./guide/getting-started"><strong>Getting started</strong><span>Declare the notebook's pixi environment and add an Animation view.</span></a>
  <a href="./guide/scenes"><strong>Scenes and notebook results</strong><span>Read values with <code>value()</code>, and place figures with <code>output()</code> and <code>cell()</code>.</span></a>
  <a href="./guide/pages"><strong>Pages and players</strong><span>Play several scenes on one page beside native marimo cells.</span></a>
  <a href="./guide/agents"><strong>Author with agents</strong><span>Let a coding agent write the notebook, the scenes, and the page.</span></a>
  <a href="./guide/run-and-export"><strong>Run and export</strong><span>Serve views live, export static sites, and render on Linux servers.</span></a>
  <a href="./reference/python-api"><strong>Python API</strong><span>The contract of <code>value()</code>, <code>output()</code>, and <code>cell()</code>.</span></a>
</nav>
