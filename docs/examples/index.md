---
title: Examples
description: Two marimo notebooks whose Animation views render Manim scenes from notebook results.
---

# Examples

Each example is a marimo notebook in
[`examples/`](https://github.com/peter-gy/marimo-manim/tree/main/examples) with
an Animation view beside it. Open one from a clone of the repository:

```sh
pixi run edit fourier
pixi run edit convolution
```

[pixi](https://pixi.sh/) installs the repository's environment and opens the
notebook with Studio. Open the **animation** view, then change a control.

<div class="movies">
  <a href="./fourier"><video class="movie" src="/media/fourier.mp4" poster="/media/fourier.png" muted loop playsinline></video></a>
  <a href="./convolution"><video class="movie" src="/media/convolution.mp4" poster="/media/convolution.png" muted loop playsinline></video></a>
</div>

The [convolution example](./convolution.md) embeds its zero-python export.
Step from the notebook through the scene and the movie to the exported page,
and move its slider.

| Example                                 | Notebook computes                                   | Scenes show                                                  |
| --------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------ |
| [Fourier drawing](./fourier.md)         | Fourier coefficients and sampled vector chains      | Rotating vectors drawing the path, and the spectrum          |
| [Convolution of dice](./convolution.md) | A joint probability table and its diagonal sums     | Diagonals filling the sum distribution, then the notebook's chart |
