# Contributing

Thanks for improving manim-marimo. Read the
[contributor guide](development_docs/README.md) before a change that crosses
the provider, the worker, or the starter.

## Set up

Install [pixi](https://pixi.sh/), then run every check from a clone:

```sh
pixi run check
```

pixi installs Python, manimpango, the package in editable mode, the check and
docs tools, and on Linux the Mesa OpenGL stack, all from `pixi.lock`.

## Pull requests

- Describe the behavior a view author or reader sees before and after.
- Add or update a test through the boundary that behavior crosses: a scene
  read, an inspection record, a starter check, or a worker render.
- Update `docs/`, the starter's `AGENTS.md`, and `skills/manim-marimo/SKILL.md`
  together when authoring behavior changes.
- Run `pixi run check`, `pixi run examples`, and, for docs changes,
  `pixi run docs-build`.

## Security

Report vulnerabilities as [SECURITY.md](SECURITY.md) describes, not in public
issues.
