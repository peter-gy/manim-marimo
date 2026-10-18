---
title: Fourier drawing
description: Rotating vectors and a spectrum, rendered from Fourier coefficients the notebook computes.
---

# Fourier drawing

[`examples/fourier.py`](https://github.com/peter-gy/manim-marimo/blob/main/examples/fourier.py)
samples a closed path, computes its Fourier coefficients, and reconstructs the
path from a chosen number of frequency pairs. The view's page shows two scenes
beside the notebook's controls and comparison chart.

```sh
pixi run edit fourier
```

## Rotating vectors

[`scene.py`](https://github.com/peter-gy/manim-marimo/blob/main/examples/studio/fourier/animation/scene.py)
reads the vector chain the notebook samples, `chain`, with shape
`[frames, vectors + 1, 2]`, and the circle radii:

<video class="movie" src="/media/fourier.mp4" poster="/media/fourier.png" controls muted playsinline></video>

```python
circle = [[[0, 0], [np.cos(t), np.sin(t)]] for t in np.linspace(0, 2 * np.pi, 61)]
chain = np.asarray(value("chain", default=circle), dtype=float)
radii = np.asarray(value("radii", default=[1]), dtype=float)
```

The defaults describe one rotating vector, so the scene also renders before
the notebook runs and in the build's check. The construction follows
[ComplexFourierSeriesExample](https://github.com/3b1b/videos/blob/master/_2019/diffyq/part4/fourier_series_scenes.py)
from 3Blue1Brown's videos.

## Spectrum

[`spectrum.py`](https://github.com/peter-gy/manim-marimo/blob/main/examples/studio/fourier/animation/spectrum.py)
grows one bar per frequency, with the radius as its height:

<video class="movie" src="/media/spectrum.mp4" poster="/media/spectrum.png" controls muted playsinline></video>

Both scenes read `radii`, so changing the path or the frequency count renders
both movies again.

## The page

```html
<marimo-output render="scene.py" aria-label="Rotating vectors">...</marimo-output>
<marimo-cell name="controls"></marimo-cell>
<div class="pair">
  <marimo-output render="spectrum.py" aria-label="Spectrum">...</marimo-output>
  <marimo-cell name="comparison"></marimo-cell>
</div>
```

[`index.html`](https://github.com/peter-gy/manim-marimo/blob/main/examples/studio/fourier/animation/index.html)
places the notebook's `controls` and `comparison` cells, so the reader changes
the path and the frequency count beside the movies.
