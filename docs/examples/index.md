---
title: Examples
description: Four marimo notebooks whose Animation views render Manim scenes from notebook results.
---

# Examples

Each example is a marimo notebook in
[`examples/`](https://github.com/peter-gy/manim-marimo/tree/main/examples) with
an Animation view beside it. The notebook computes every result, and the
view's scene only presents them. Open one from a clone of the repository:

```sh
pixi run edit dataflow
```

[pixi](https://pixi.sh/) installs the repository's environment and opens the
notebook with Studio. Open the **animation** view, then change a control.

<div class="gallery">
  <a href="./dataflow">
    <img src="/exports/dataflow/render/poster.png" alt="" loading="lazy">
    <strong>A notebook is a dataflow graph</strong>
    <span>The notebook sorts a small notebook's cells and finds what each slider reruns.</span>
  </a>
  <a href="./fourier">
    <img src="/exports/fourier/render/poster.png" alt="" loading="lazy">
    <strong>Fourier drawing</strong>
    <span>Rotating vectors draw manim-marimo's mark from coefficients the notebook computes.</span>
  </a>
  <a href="./convolution">
    <img src="/exports/convolution/render/poster.png" alt="" loading="lazy">
    <strong>Convolution of dice</strong>
    <span>A joint probability table fills the distribution of the sum, diagonal by diagonal.</span>
  </a>
  <a href="./epidemic">
    <img src="/exports/epidemic/render/poster.png" alt="" loading="lazy">
    <strong>Simulating an epidemic</strong>
    <span>Two hundred simulated people, each traced to the notebook row behind them.</span>
  </a>
</div>

Each example page embeds its zero-python export. Step from the notebook
through the scene and the movie to the exported page, and change its control.
