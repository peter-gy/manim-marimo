---
title: Examples
description: Three marimo notebooks whose Animation views render Manim scenes from notebook results.
---

# Examples

Each example is a marimo notebook in
[`examples/`](https://github.com/peter-gy/marimo-manim/tree/main/examples) with
an Animation view beside it. Open one from a clone of the repository:

```sh
pixi run edit epidemic
pixi run edit fourier
pixi run edit convolution
```

[pixi](https://pixi.sh/) installs the repository's environment and opens the
notebook with Studio. Open the **animation** view, then change a control.

<a class="feature" href="./epidemic">
  <video class="movie" src="/media/epidemic.mp4" poster="/media/epidemic.png" muted loop playsinline autoplay></video>
  <span><strong>Simulating an epidemic</strong> Two hundred people, simulated in the notebook and traced in the movie. Pause it and point at anyone.</span>
</a>

<div class="movies">
  <a href="./fourier"><video class="movie" src="/media/fourier.mp4" poster="/media/fourier.png" muted loop playsinline></video></a>
  <a href="./convolution"><video class="movie" src="/media/convolution.mp4" poster="/media/convolution.png" muted loop playsinline></video></a>
</div>

The [epidemic](./epidemic.md) and [convolution](./convolution.md) examples
embed their zero-python exports. Step from the notebook through the scene and
the movie to the exported page, and move its slider. In the epidemic's movie,
pause and point at a person to trace them to the notebook row that simulated
them.

| Example                                 | Notebook computes                                   | Scenes show                                                  |
| --------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------ |
| [Simulating an epidemic](./epidemic.md) | Two hundred people's paths, infections, and the S/I/R shares | The city, its infection rings and links, and the stacked shares |
| [Fourier drawing](./fourier.md)         | Fourier coefficients and sampled vector chains      | Rotating vectors drawing the path, and the spectrum          |
| [Convolution of dice](./convolution.md) | A joint probability table and its diagonal sums     | Diagonals filling the sum distribution, then the notebook's chart |
