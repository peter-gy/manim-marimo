# manim-marimo

manim-marimo is a marimo-studio view provider that renders ManimGL scenes from
marimo notebook results. Studio owns notebooks, view projects, builds,
sessions, and delivery. This package owns scene reads, the render worker, the
`manim-marimo/manim:default` starter, and the agent skill for authoring Manim
views.

## Boundaries

- Import Studio only through `marimo_studio.view_providers`. `check_provider`
  rejects other imports.
- Keep scene execution in the worker process started through
  `request.runner`, so Studio's deadlines and cancellation stop it.
- The provider runs in the marimo server with the base package. ManimGL and
  FFmpeg belong to the `render` extra, and Studio's `find_tool` resolves the
  `manim-marimo-worker` command in the notebook's pixi environment.
- Inspection reads source with `ast` and never runs project code.
- The build publishes the page and its assets, and keeps scenes private in the
  render template.
- `pixi.toml` owns the development environment: Python 3.10 to 3.14, conda
  libraries, and PyPI packages, locked in `pixi.lock`. The docs site's
  packages come from `docs/pnpm-lock.yaml`.

## Validate

```sh
pixi run check        # lint, types, and every test
pixi run examples     # after provider, starter, or scene changes
pixi run docs-build   # after docs changes
```

Rendering behavior needs evidence from a real render: a test through
`run_scene` or `check_provider`, or an example view checked in a browser.

## Keep in step

Behavior visible to view authors is described in `docs/`, in
`src/manim_marimo/starters/default/files/AGENTS.md`, and in
`skills/manim-marimo/SKILL.md`. Change all three together.

## Guides

- [Contributor guide](development_docs/README.md)
- [Architecture](development_docs/architecture.md)
- [Testing](development_docs/testing.md)
- [Releasing](development_docs/releasing.md)
