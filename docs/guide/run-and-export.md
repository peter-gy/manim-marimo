---
title: Run and export
description: Serve Manim views live, export them as static sites, and render on Linux servers without a display.
---

# Run and export

Manim views run in every way Studio delivers a view. Studio's
[Run or export a view](https://marimo-team.github.io/marimo-studio/guide/run-and-share)
compares the options.

## Run a live view

```sh
uvx --with manim-marimo marimo run analysis.py --sandbox=pixi
```

Each reader gets a notebook session. Studio renders a scene for the results that
reader sees, and shares movies between readers whose results match. Run mode
renders at `production` quality unless `view.toml` sets another.

## Export a static site

A `zero-python` export runs the notebook on your machine, prepares one state
for each combination of control values the view lists, and renders every
scene once per state:

```sh
uvx --with manim-marimo \
  marimo-studio view export animation --target analysis.py \
  --output dist/animation --runtime zero-python
```

Studio commands that target a notebook with `[tool.pixi]` metadata install its
pixi environment and render from it, as `--sandbox=pixi` does.

List the control values to prepare in `states.yaml` beside `view.toml`. The
[convolution example](../examples/convolution.md) prepares every value of its
slider:

```yaml
schema: marimo-export.states.v1
default_state: matrix-000000
matrix:
  bias: [0.4, 0, 0.1, 0.2, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
```

Prepare every value a control can take. A slider stepped to a value without a
prepared state keeps the previous movie. Each state renders a full movie, so
the export time grows with the number of states.

The export stores the values every state's scenes read, and the whole set holds
at most 100,000 JSON values: numbers, strings, list and object entries. The
[epidemic example](../examples/epidemic.md) keeps four states of two hundred
people's paths in budget by recording positions twice a day as flat lists, and
its scene interpolates between them. Keep large per-frame data compact the
same way, or prepare fewer states.

`view preflight` prepares and renders every state as an export does, then
discards the site. Both commands warn with `prepared-states-skip-control-values`
for each control whose values the states skip, with the count and the first
skipped values:

```sh
uvx --with manim-marimo \
  marimo-studio view preflight animation --target analysis.py
```

Serve the export from a web server that compresses JavaScript and answers byte
range requests, so the page loads quickly and the movie streams:

```sh
npx serve dist/animation
```

## Linux servers

The [Getting started metadata](./getting-started.md#install) renders on Linux
servers without a display or a GPU. Its `tool.pixi.target.linux.dependencies`
table installs [Mesa](https://mesa3d.org/)'s software OpenGL into the
notebook's pixi environment, and manim-marimo renders through Mesa's EGL driver
when no `DISPLAY` is set:

```sh
uvx --with manim-marimo marimo run analysis.py --sandbox=pixi --host 0.0.0.0
```

manim-marimo's CI renders every test scene through Mesa's EGL driver on Ubuntu. With a
`DISPLAY` set, ManimGL opens its usual X11 context instead.
