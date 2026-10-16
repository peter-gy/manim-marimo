# marimo-manim

marimo-manim is a marimo-studio view provider that renders ManimGL scenes from
marimo notebook results. Studio owns notebooks, view projects, builds,
sessions, and delivery. This package owns scene reads, the render worker, the
`marimo-manim/manim:default` starter, and the agent skill for authoring Manim
views.

## Boundaries

- Import Studio only through `marimo_studio.view_providers`. `check_provider`
  rejects other imports.
- Keep scene execution in the worker process started through
  `request.runner`, so Studio's deadlines and cancellation stop it.
- Inspection reads source with `ast` and never runs project code.
- The build publishes the page and its assets, and keeps scenes private in the
  render template.
- System tools come from `pixi.toml`, Python packages from `uv.lock`, and the
  docs site's packages from `docs/pnpm-lock.yaml`.

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
`src/marimo_manim/starters/default/files/AGENTS.md`, and in
`skills/marimo-manim/SKILL.md`. Change all three together.

## Guides

- [Contributor guide](development_docs/README.md)
- [Architecture](development_docs/architecture.md)
- [Testing](development_docs/testing.md)
- [Releasing](development_docs/releasing.md)
