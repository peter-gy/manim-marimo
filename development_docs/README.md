# Contributor guide

marimo-manim is a marimo-studio view provider. Studio owns notebooks, view
projects, builds, sessions, and delivery. marimo-manim owns one kind of view:
it finds the notebook results Manim scenes read, renders the scenes into
movies, and ships the starter, the scene API, and the agent skill for authoring
them. Start a change from the behavior a view author or reader depends on, and
test it through the same boundary.

## Set up

[pixi](https://pixi.sh/) owns the development environment. From conda-forge it
installs Python, manimpango built against Pango, the check and docs tools, and
on Linux the Mesa OpenGL stack that renders scenes without a display. From PyPI
it installs marimo-manim in editable mode with its dependencies. `pixi.lock`
pins both.

```sh
pixi run check
```

`pixi task list` shows every task:

| Task                  | Runs                                                   |
| --------------------- | ------------------------------------------------------ |
| `check`               | `lint`, `typecheck`, and `test`, as CI does            |
| `format`              | ruff fixes and formatting                              |
| `example <name>`      | Validates and builds one example view                  |
| `examples`            | Validates and builds every example view                |
| `edit <example>`      | Opens `examples/<example>.py` in Studio, with Lens to select traced shapes |
| `build`               | Builds the wheel and sdist into `dist/`                |
| `docs-examples`       | Exports the epidemic and convolution examples the docs embed |
| `docs-dev`, `docs-build` | Serves or builds the VitePress site in `docs/`      |
| `hero`                | Captures and renders the README hero                   |

## Where things live

| Path                          | Owns                                                                   |
| ----------------------------- | ---------------------------------------------------------------------- |
| `src/marimo_manim/`           | The provider, the scene API, and the render worker                     |
| `src/marimo_manim/starters/`  | Files of the `marimo-manim/manim:default` starter                      |
| `skills/marimo-manim/`, `plugin.json` | The agent skill the wheel ships as an Agent Plugin           |
| `examples/`                   | Three notebooks with Animation views, used by docs and manual checks    |
| `docs/`                       | The VitePress documentation site                                       |
| `docs/scripts/build-examples.ts` | Exports the epidemic and convolution examples into `docs/public/exports/` with their traced shapes, which the `ManimExample` component embeds |
| `scripts/hero/`               | The bun scripts that render the README hero                            |
| `tests/`                      | Read, inspection, starter, worker, and lineage tests                   |
| `pixi.toml`, `pixi.lock`      | The development environments, one per Python version, and tasks       |
| `pyproject.toml`              | Package metadata, dependencies, and the build backend                  |

## README hero

The README opens with `docs/public/media/hero-light.webp` and
`hero-dark.webp`: the `convolution` example's notebook cells beside its
Animation view, with the bias slider dragged between two rendered movies.
`pixi run hero` regenerates both from the current notebook, scene, and Studio
in the `media` environment. [bun](https://bun.sh/) runs the scripts and
[Playwright](https://playwright.dev/) drives Chromium:

| Step              | Script        | Does                                                                     |
| ----------------- | ------------- | ------------------------------------------------------------------------ |
| `hero-capture`    | `capture.ts`  | Exports the movies for bias 0 and 0.8, and captures the marimo editor's cells at every slider step between them in both themes, into `scripts/hero/shots/` |
| `hero-render`     | `render.ts`   | Paints each frame with `compose.html` and encodes the animated WebP files |

`pixi run hero-render --at 7.5` writes the frame at 7.5 seconds in each theme
to `shots/preview-<theme>-7.5.png`, for checking the layout without an
encode. `render.ts` places the
read highlights with the scene's timings, so update its `cues` when the
convolution scene changes pace.

## Guides

- [Architecture](architecture.md): the provider lifecycle and the worker
  protocol.
- [Testing](testing.md): test layers, rendering on Linux, and example checks.
- [Releasing](releasing.md): preview wheels, tagged releases, and the docs site.

## External foundations

| Project                                                                      | Role here                                                        |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [marimo-studio](https://marimo-team.github.io/marimo-studio/)                | Hosts the provider. Its `view_providers` SDK is the only import. |
| [ManimGL](https://github.com/3b1b/manim)                                     | Builds and renders scenes                                        |
| [Agent Plugins](https://agent-plugins.org/)                                  | Packages the skill into the wheel and prints it for agents       |
| [pixi](https://pixi.sh/)                                                     | Installs and locks the development environments                  |
| [uv](https://docs.astral.sh/uv/)                                             | Builds and publishes the package                                 |
| [VitePress](https://vitepress.dev/)                                          | Builds the documentation site                                    |

## Change checklist

- Behavior visible to view authors appears in `docs/`, the starter's
  `AGENTS.md`, and `skills/marimo-manim/SKILL.md` in the same terms.
- A change to scene reads, renders, or the starter keeps both examples
  building: `pixi run examples`.
- `pixi run check` passes, and the docs build with `pixi run docs-build`.
