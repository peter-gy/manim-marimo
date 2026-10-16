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
  image:
    src: /logo.svg
    alt: marimo-manim
  actions:
    - theme: brand
      text: Get started
      link: /guide/getting-started
    - theme: alt
      text: Examples
      link: /examples/
    - theme: alt
      text: marimo-studio
      link: https://marimo-team.github.io/marimo-studio/
features:
  - title: Animate notebook values
    details: Read arrays, tables, and widget values in a scene with value(). Studio renders the scene again when one changes.
    link: /guide/scenes
  - title: Place notebook figures
    details: output() and cell() bring matplotlib figures and cell outputs into the scene as images.
    link: /guide/scenes#figures-and-cell-outputs
  - title: Pages with several scenes
    details: Each render host on the page plays one scene, beside native marimo cells and controls.
    link: /guide/pages
  - title: Agent authoring
    details: The package ships an agent skill, so a coding agent can write the notebook, the scenes, and the page.
    link: /guide/agents
---

## A notebook value, animated

The [Fourier example](./examples/fourier.md) computes Fourier coefficients in
the notebook. Its scene draws them as rotating vectors:

<video class="movie" src="/media/fourier.mp4" poster="/media/fourier.png" autoplay muted loop playsinline></video>

```python
from marimo_manim import value

chain = np.asarray(value("chain", default=circle), dtype=float)
radii = np.asarray(value("radii", default=[1]), dtype=float)
```

Change the path or the number of frequencies in the notebook, and Studio
renders the movie again.

## Ask a coding agent

From a project where marimo-manim is installed, paste this into Claude Code,
Codex, or another terminal agent:

```text
Run `uv run agent-plugins read marimo-studio` and
`uv run agent-plugins read marimo-manim`, then create a notebook that
explains Fourier series and an Animation view that draws a square wave
from rotating vectors.
```
