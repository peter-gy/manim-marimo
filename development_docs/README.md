# Contributor guide

manim-marimo is a marimo-studio view provider. Studio owns notebooks, view
projects, builds, sessions, and delivery. manim-marimo owns one kind of view:
it finds the notebook results Manim scenes read, renders the scenes into
movies, and ships the starter, the scene API, and the agent skill for authoring
them. Start a change from the behavior a view author or reader depends on, and
test it through the same boundary.

## Set up

[pixi](https://pixi.sh/) owns the development environment. From conda-forge it
installs Python, manimpango built against Pango, the check and docs tools, and
on Linux the Mesa OpenGL stack that renders scenes without a display. From PyPI
it installs manim-marimo in editable mode with its `render` extra. `pixi.lock`
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
| `docs-examples`       | Exports every example the docs embed                   |
| `docs-dev`, `docs-build` | Serves or builds the VitePress site in `docs/`      |
| `hero`                | Captures and renders the README hero                   |
| `design`              | Generates the brand assets and the examples' fonts     |

## Where things live

| Path                          | Owns                                                                   |
| ----------------------------- | ---------------------------------------------------------------------- |
| `src/manim_marimo/`           | The provider, the scene API, and the render worker                     |
| `src/manim_marimo/starters/`  | Files of the `manim-marimo/manim:default` starter                      |
| `skills/manim-marimo/`, `plugin.json` | The agent skill the wheel ships as an Agent Plugin           |
| `examples/`                   | Four notebooks with Animation views, used by docs and manual checks     |
| `docs/`                       | The VitePress documentation site                                       |
| `docs/scripts/build-examples.ts` | Exports every example into `docs/public/exports/` with its traced shapes, which the `ManimExample` component plays and links |
| `scripts/hero/`               | The bun scripts that render the README hero                            |
| `scripts/design/`             | The bun scripts that generate the brand assets into `docs/public/`     |
| `tests/`                      | Read, inspection, starter, worker, and lineage tests                   |
| `pixi.toml`, `pixi.lock`      | The development environments, one per Python version, and tasks       |
| `pyproject.toml`              | Package metadata, dependencies, and the build backend                  |

## README hero

The README opens with `docs/public/media/hero-light.webp` and
`hero-dark.webp`: the `dataflow` example's notebook cells beside its
Animation view, as the notebook switches the slider whose cascade it shows.
`pixi run hero` regenerates both from the current notebook, scene, and Studio
in the `media` environment. [bun](https://bun.sh/) runs the scripts and
[Playwright](https://playwright.dev/) drives Chromium:

| Step              | Script        | Does                                                                     |
| ----------------- | ------------- | ------------------------------------------------------------------------ |
| `hero-capture`    | `capture.ts`  | Exports the movies for the noise and degree sliders, and captures the marimo editor's cells with each selected in both themes, into `scripts/hero/shots/` |
| `hero-render`     | `render.ts`   | Paints each frame with `compose.html` and encodes the animated WebP files |

`pixi run hero-render --at 7.5` writes the frame at 7.5 seconds in each theme
to `shots/preview-<theme>-7.5.png`, for checking the layout without an
encode. `render.ts` places the
read highlights with the scene's timings, so update its `cues` when the
dataflow scene changes pace.

## Documentation theme

`docs/.vitepress/theme/` draws the site like a Manim scene, and
`scripts/hero/compose.html` paints the README hero in the same terms:

| Element  | Contract                                                                                  |
| -------- | ----------------------------------------------------------------------------------------- |
| Page     | Dark mode takes `#11161c`, the background the worker renders scenes on. Light mode is white |
| Color    | ManimGL's palette. Notebook results are green, scenes are blue, and yellow surrounds what has focus |
| Type     | Computer Modern from the `computer-modern` package: CMU Serif for text, CMU Bright for navigation, CMU Typewriter for code |
| Surfaces | A stroke and the same color as a faint fill, with square corners                           |
| Hero     | `FourierHero.vue` draws the mark and writes the wordmark with rotating vectors, from the generated `brand.ts`, and loops |

Code blocks use the `manim-dark` and `manim-light` Shiki themes in
`docs/.vitepress/config.mts`. Recompose the README hero with
`pixi run hero-render` after changing the page colors.

## Brand

The mark is marimo's looped circle drawn by rotating vectors: the default
path of `examples/fourier.py`. `pixi run design` reads the vectors from the
notebook and writes, beside the wordmark set in CMU Serif:

| Output                                   | Holds                                                         |
| ---------------------------------------- | ------------------------------------------------------------- |
| `docs/public/brand/`                     | Marks, icons, wordmarks, and lockups as SVG and PNG, the Open Graph image, and the brand board |
| `docs/public/favicon.svg`, `apple-touch-icon.png` | The icon on the scene's plate                         |
| `docs/.vitepress/theme/brand.ts`         | The mark's vectors and the wordmark's contours, which the home page's hero draws |
| `examples/studio/*/animation/fonts/`     | CMU faces the scenes register with manimpango                 |
| `examples/studio/*/animation/assets/fonts/` | CMU faces the example pages load                           |

Change the mark in the notebook's `mark_vectors`, then run `pixi run design`.

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
  `AGENTS.md`, and `skills/manim-marimo/SKILL.md` in the same terms.
- A change to scene reads, renders, or the starter keeps both examples
  building: `pixi run examples`.
- `pixi run check` passes, and the docs build with `pixi run docs-build`.
