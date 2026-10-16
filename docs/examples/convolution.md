---
title: Convolution of dice
description: A joint probability table becomes the distribution of a sum, and the scene ends on the notebook's own chart.
---

# Convolution of dice

[`examples/convolution.py`](https://github.com/peter-gy/marimo-manim/blob/main/examples/convolution.py)
computes the joint probability table of a fair die and a die biased toward six,
the distribution of their sum, and a matplotlib chart of that distribution.

```sh
pixi run edit convolution
```

<video class="movie" src="/media/convolution.mp4" poster="/media/convolution.png" controls muted playsinline></video>

## Values and a figure

[`scene.py`](https://github.com/peter-gy/marimo-manim/blob/main/examples/studio/convolution/animation/scene.py)
reads the table and the sums as values, and the chart as a figure:

```python
joint = np.asarray(value("joint", default=np.outer(FAIR, FAIR).tolist()), dtype=float)
probabilities = np.asarray(
    value("probabilities", default=np.convolve(FAIR, FAIR).tolist()), dtype=float
)
...
chart = output("distribution_figure", height=2.6)
if chart is not None:
    self.play(FadeOut(VGroup(bars, labels)), FadeIn(chart), ...)
```

The scene follows each diagonal of the table into one bar of the sum's
distribution, based on
[SumAlongDiagonal](https://github.com/3b1b/videos/blob/master/_2023/convolutions2/dice.py).
It then replaces its own bars with the notebook's `distribution_figure`, so the
reader sees that both describe the same distribution.

## Static export

The view's
[`states.yaml`](https://github.com/peter-gy/marimo-manim/blob/main/examples/studio/convolution/animation/states.yaml)
prepares every value of the bias slider. A `zero-python` export renders one
movie per value, and the exported page swaps movies as the reader moves the
slider:

```sh
pixi run marimo-studio view export animation --target examples/convolution.py \
  --output dist/convolution --runtime zero-python
```
