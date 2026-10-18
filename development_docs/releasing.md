# Releasing

manim-marimo publishes two kinds of builds from `.github/workflows/publish.yml`.

| Channel | Trigger                             | Version                    | Destination                                    |
| ------- | ----------------------------------- | -------------------------- | ---------------------------------------------- |
| Preview | CI succeeds on a push to `main`     | `X.Y.(Z+1).devN`           | The `preview` GitHub release, one wheel per commit |
| Release | An annotated `vX.Y.Z` tag on `main` | `X.Y.Z` from `pyproject.toml` | A `vX.Y.Z` GitHub release, and PyPI            |

`N` counts the commits since the last release tag, so preview versions sort in
commit order. Install a preview wheel by URL, in the notebook's script metadata
and in the marimo server, so the provider and the worker share one release:

```python
# dependencies = [
#     "manim-marimo[render] @ https://github.com/peter-gy/manim-marimo/releases/download/preview/manim_marimo-0.1.1.dev3-py3-none-any.whl",
# ]
```

```sh
uvx --with "manim-marimo @ https://github.com/peter-gy/manim-marimo/releases/download/preview/manim_marimo-0.1.1.dev3-py3-none-any.whl" \
  marimo edit analysis.py --sandbox=pixi --watch
```

## Cut a release

1. Set `version` in `pyproject.toml` and merge it to `main`.
2. Pin `marimo-studio` to a release on PyPI. PyPI rejects packages whose
   dependencies are direct URLs, so the release job fails while the dependency
   names a preview wheel.
3. Tag the merged commit and push the tag:

   ```sh
   git tag -a v0.1.0 -m "manim-marimo 0.1.0"
   git push origin v0.1.0
   ```

The workflow checks that the tag matches `pyproject.toml`, builds the wheel and
sdist, attaches them to a GitHub release with generated notes, and publishes
them to the [`manim-marimo`](https://pypi.org/project/manim-marimo/) project on
PyPI through [trusted publishing](https://docs.pypi.org/trusted-publishers/).
The project trusts `peter-gy/manim-marimo`, workflow `publish.yml`, and
environment `pypi`.

## What a build contains

`uv build` runs the `agent_plugins.build.uv_build` backend. The wheel holds the
`manim_marimo` package with its starter files, and
`manim_marimo-<version>.agent-plugin/` with `plugin.json` and
`skills/manim-marimo/`. Check both after changing the build configuration:

```sh
pixi run build
unzip -l dist/manim_marimo-*.whl
```

## Documentation

`.github/workflows/pages.yml` builds `docs/` with VitePress on every pull
request and deploys it to GitHub Pages from `main`. The site's base path comes
from the Pages configuration, so local builds serve from `/`.
