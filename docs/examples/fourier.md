---
title: Fourier drawing
description: Rotating vectors draw manim-marimo's mark and TeX's italic m from Fourier coefficients the notebook computes.
aside: false
---

# Fourier drawing

The drawing on the [home page](../index.md) is this example. Its notebook,
[`examples/fourier.py`](https://github.com/peter-gy/manim-marimo/blob/main/examples/fourier.py),
samples a closed path, computes its Fourier coefficients, and keeps the
frequencies up to a slider's value. The scene turns one vector per coefficient
and traces the tip of their chain, after 3Blue1Brown's
[*But what is a Fourier series?*](https://www.youtube.com/watch?v=r6sGWTCMz2k)

<ManimExample
  name="fourier"
  notebook="examples/fourier.py"
  scene="examples/studio/fourier/animation/scene.py"
/>

Open the notebook and its view in Studio from a clone of the repository:

```sh
pixi run edit fourier
```

## Two paths

| Path                | Sampled from                                       | Vectors that draw it |
| ------------------- | -------------------------------------------------- | -------------------- |
| manim-marimo mark   | Five rotating vectors the notebook lists           | 5                    |
| TeX's italic m      | The outline of `$m$`, from matplotlib's `TextPath` | Every one kept       |

manim-marimo's mark is marimo's looped circle drawn by rotating vectors: one
turns four times while four short ones let the loops drift. The notebook
samples it, and the Fourier transform finds exactly those five vectors again.
TeX's italic m needs many more. Move the slider to see how few frequencies
still read as an m.

## The notebook computes the coefficients

```python
all_coefficients = np.fft.fft(signal) / sample_count
frequencies = np.array([k for n in range(1, pairs.value + 1) for k in (n, -n)])
```

The scene reads `terms`, one `[frequency, real, imaginary]` row per vector with
the longest first, and `traced`, the path the chain's tip draws in one turn:

```python
terms = np.asarray(value("terms", default=[[1, 0.25, 0.0]]), dtype=float)
traced = np.asarray(value("traced", default=circle), dtype=float)
```

A second scene, `spectrum.py`, draws one stem per frequency with the vector's
length as its height. The view's page plays both movies beside the notebook's
`controls` and `comparison` cells.
