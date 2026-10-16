# Testing

```sh
pixi run check                    # lint, types, and every test, as CI runs them
pixi run uv run pytest -m 'not render'
```

## Test layers

| File                     | Boundary                                                                            |
| ------------------------ | ----------------------------------------------------------------------------------- |
| `tests/test_reads.py`    | `value`, `output`, and `cell` inside and outside a render                           |
| `tests/test_provider.py` | Inspection records and diagnostics, and the installed starter through `check_provider` |
| `tests/test_worker.py`   | `run_scene` against a real ManimGL process: reads, figures, checks, failures        |

`check_provider("marimo-manim/manim")` creates the starter in a temporary
notebook, builds it, publishes the page, and renders every declared scene, as
Studio does. It is the closest test to a reader opening a new view.

## Rendering on Linux

Tests marked `render` start ManimGL and FFmpeg, so they need OpenGL. macOS
provides it to every process. On Linux, `pixi.toml` installs Mesa from
conda-forge and points glcontext at its libraries, and the worker opens an EGL
context when no `DISPLAY` is set. It also installs Pango and a compiler, because
manimpango publishes no Linux wheels and uv compiles it on first sync. CI runs
the same `pixi run check` on Ubuntu with no display server and no GPU.

To reproduce a Linux failure, run the suite inside the pixi environment on a
Linux machine or container. `pixi run env | grep GLCONTEXT` shows the
libraries glcontext loads.

## Examples

Both example notebooks are part of the contract. Build and validate them after
a change to the provider, the starter, or a scene:

```sh
pixi run examples
pixi run edit fourier
```

In the Animation view, move a control and confirm every render host passes
through `stale` back to `ready` with a new movie.
