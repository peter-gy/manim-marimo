---
layout: home
title: manim-marimo
titleTemplate: false
description: Manim animations of marimo notebook results, rendered as marimo-studio views.
hero:
  text: Animate <span class="notebook">marimo notebooks</span> with <span class="scene">Manim</span>
  tagline: >-
    The notebook computes. A Manim scene animates the result, and
    marimo-studio renders it again whenever a value changes.
  actions:
    - theme: brand
      text: Get started
      link: /guide/getting-started
    - theme: alt
      text: Examples
      link: /examples/
---

<figure class="hero-figure">
  <img class="only-light" src="/media/hero-light.webp" alt="A marimo notebook beside its Animation view. Choosing which slider moves in the notebook renders the movie again: the dataflow graph of a small notebook lights up the cells that rerun, in the order marimo runs them.">
  <img class="only-dark" src="/media/hero-dark.webp" alt="">
</figure>

## The notebook computes, the scene presents

The [dataflow example](./examples/dataflow.md) above parses a small notebook,
builds the graph of which cell reads which, sorts it topologically, and finds
the cells each slider reruns. Its scene reads those results by name and only
draws them:

```python
nodes = value("nodes")
edges = value("edges")
rerun = value("rerun")
```

Studio finds these reads in the scene's source, captures the results from the
notebook, and renders the movie again when the notebook's choice changes.

## Read on

<nav class="routes">
  <a href="./guide/getting-started"><strong>Getting started</strong><span>Declare the notebook's pixi environment and add an Animation view.</span></a>
  <a href="./guide/scenes"><strong>Scenes and notebook results</strong><span>Read values with <code>value()</code>, and place figures with <code>output()</code> and <code>cell()</code>.</span></a>
  <a href="./examples/fourier"><strong>Fourier drawing</strong><span>The drawing above: rotating vectors the notebook computes.</span></a>
  <a href="./guide/agents"><strong>Author with agents</strong><span>Let a coding agent write the notebook, the scenes, and the page.</span></a>
</nav>
