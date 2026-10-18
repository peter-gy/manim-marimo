# Testing

```sh
pixi run check                    # lint, types, and every test, as CI runs them
pixi run pytest -m 'not render'
pixi run --environment py310 test  # one Python version: py310 to py314
```

## Test layers

| File                     | Boundary                                                                            |
| ------------------------ | ----------------------------------------------------------------------------------- |
| `tests/test_reads.py`    | `value`, `output`, and `cell` inside and outside a render                           |
| `tests/test_provider.py` | Inspection records and diagnostics, and the installed starter through `check_provider` |
| `tests/test_worker.py`   | `run_scene` against a real ManimGL process: reads, figures, checks, failures        |
| `tests/test_lineage.py`  | Traced shapes through `provider.render`: the reads each region names, and the region budget |

`check_provider("marimo-manim/manim")` creates the starter in a temporary
notebook, builds it, publishes the page, and renders every declared scene, as
Studio does. It is the closest test to a reader opening a new view.

## Rendering on Linux

Tests marked `render` start ManimGL and FFmpeg, so they need OpenGL. macOS
provides it to every process. On Linux, `pixi.toml` installs Mesa from
conda-forge and points glcontext at its libraries. The worker turns off
pyglet's hidden window and opens an EGL context when no `DISPLAY` is set. CI
runs `pixi run test` on Ubuntu with no display server and no GPU, once for each
Python version from 3.10 to 3.14.

`manimpango` comes from conda-forge in every environment, built against the
environment's Pango. `pixi list manimpango` shows its channel.

To reproduce a Linux failure, run the suite inside the pixi environment on a
Linux machine or container. `pixi run env | grep GLCONTEXT` shows the
libraries glcontext loads.

## Examples

The example notebooks are part of the contract. Build and validate them after
a change to the provider, the starter, or a scene:

```sh
pixi run examples
pixi run edit epidemic
```

In the Animation view, move a control and confirm every render host passes
through `stale` back to `ready` with a new movie. The epidemic example is the
load test for tracing: two hundred moving shapes, rings, and links. After a
change to `_lineage.py`, run `pixi run docs-examples`, which fails when a
render warns, then pause its Movie stage in the docs and point at people
during the peak and while they move.
