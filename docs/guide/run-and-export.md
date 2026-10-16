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
uv run marimo run analysis.py
```

Each reader gets a notebook session. Studio renders a scene for the results that
reader sees, and shares movies between readers whose results match. Run mode
renders at `production` quality unless `view.toml` sets another.

## Export a static site

A `zero-python` export runs the notebook on your machine, prepares one state
for each combination of control values the view lists, and renders every
scene once per state:

```sh
uv run marimo-studio view export animation --target analysis.py \
  --output dist/animation --runtime zero-python
```

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

Serve the export from a web server that compresses JavaScript and answers byte
range requests, so the page loads quickly and the movie streams:

```sh
npx serve dist/animation
```

## Linux servers

ManimGL needs OpenGL, and its text library, manimpango, compiles against
[Pango](https://pango.gnome.org/) on Linux. [pixi](https://pixi.sh/), the
conda package manager, installs both from conda-forge into the workspace that
runs Studio:

```toml
[target.linux.dependencies]
mesalib = ">=25"
libegl = ">=1.7"
libgl = ">=1.7"
pango = ">=1.56"
cairo = ">=1.18"
pkg-config = ">=0.29"
glib = ">=2.84"
zlib = ">=1.3"
expat = ">=2.6"
xorg-xorgproto = ">=2024.1"
c-compiler = ">=1.9"
fonts-conda-ecosystem = "*"

[target.linux.activation.env]
GLCONTEXT_LINUX_LIBGL = "$CONDA_PREFIX/lib/libGL.so.1"
GLCONTEXT_LINUX_LIBEGL = "$CONDA_PREFIX/lib/libEGL.so.1"
__EGL_VENDOR_LIBRARY_DIRS = "$CONDA_PREFIX/share/glvnd/egl_vendor.d"
CC = "$CONDA_PREFIX/bin/gcc"
LDFLAGS = "-L$CONDA_PREFIX/lib -Wl,-rpath,$CONDA_PREFIX/lib"
```

On a machine without a display, marimo-manim renders through
[Mesa](https://mesa3d.org/)'s software EGL driver, which needs no window system
and no GPU. Install the Python environment and start Studio through
`pixi run`, so the build and the renders use these libraries:

```sh
pixi run uv run marimo run analysis.py --host 0.0.0.0
```

marimo-manim's own CI renders every test scene this way, from the same tables
in its [`pixi.toml`](https://github.com/peter-gy/marimo-manim/blob/main/pixi.toml).
With a `DISPLAY` set, ManimGL opens its usual X11 context instead.
