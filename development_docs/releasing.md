# Releasing

marimo-manim publishes two kinds of builds from `.github/workflows/publish.yml`.

| Channel | Trigger                             | Version                    | Destination                                    |
| ------- | ----------------------------------- | -------------------------- | ---------------------------------------------- |
| Preview | CI succeeds on a push to `main`     | `X.Y.(Z+1).devN`           | The `preview` GitHub release, one wheel per commit |
| Release | An annotated `vX.Y.Z` tag on `main` | `X.Y.Z` from `pyproject.toml` | A `vX.Y.Z` GitHub release, and PyPI            |

`N` counts the commits since the last release tag, so preview versions sort in
commit order. Install a preview wheel by URL:

```sh
uv add "marimo-manim @ https://github.com/peter-gy/marimo-manim/releases/download/preview/marimo_manim-0.1.1.dev3-py3-none-any.whl"
```

## Cut a release

1. Set `version` in `pyproject.toml` and merge it to `main`.
2. Pin `marimo-studio` to a release on PyPI. PyPI rejects packages whose
   dependencies are direct URLs, so the release job fails while the dependency
   names a preview wheel.
3. Tag the merged commit and push the tag:

   ```sh
   git tag -a v0.1.0 -m "marimo-manim 0.1.0"
   git push origin v0.1.0
   ```

The workflow checks that the tag matches `pyproject.toml`, builds the wheel and
sdist, attaches them to a GitHub release with generated notes, and publishes
them to PyPI through [trusted publishing](https://docs.pypi.org/trusted-publishers/).
Register `peter-gy/marimo-manim`, workflow `publish.yml`, environment `pypi`
as a trusted publisher on PyPI before the first release.

## What a build contains

`uv build` runs the `agent_plugins.build.uv_build` backend. The wheel holds the
`marimo_manim` package with its starter files, and
`marimo_manim-<version>.agent-plugin/` with `plugin.json` and
`skills/marimo-manim/`. Check both after changing the build configuration:

```sh
pixi run build
unzip -l dist/marimo_manim-*.whl
```

## Documentation

`.github/workflows/pages.yml` builds `docs/` with VitePress on every pull
request and deploys it to GitHub Pages from `main`. The site's base path comes
from the Pages configuration, so local builds serve from `/`.
