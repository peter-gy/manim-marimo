# Releasing

manim-marimo publishes two kinds of builds from `.github/workflows/publish.yml`.

| Channel | Trigger                             | Version                    | Destination                                    |
| ------- | ----------------------------------- | -------------------------- | ---------------------------------------------- |
| Preview | CI succeeds on a push to `main`     | `X.Y.(Z+1).devN`           | The `preview` GitHub release, one wheel per commit |
| Release | An annotated `vX.Y.Z` tag on `main` | `X.Y.Z` from `pyproject.toml` | PyPI, then a `vX.Y.Z` GitHub release           |

`N` counts the commits since the last release tag, so preview versions sort in
commit order. Install a preview wheel by URL, in the notebook's script metadata
and in the marimo server, so the provider and the worker share one release:

```python
# dependencies = [
#     "manim-marimo[render] @ https://github.com/peter-gy/manim-marimo/releases/download/preview/manim_marimo-0.0.2.dev3-py3-none-any.whl",
# ]
```

```sh
uvx --with "manim-marimo @ https://github.com/peter-gy/manim-marimo/releases/download/preview/manim_marimo-0.0.2.dev3-py3-none-any.whl" \
  marimo edit analysis.py --sandbox=pixi --watch
```

## Cut a release

1. On `main`, set `version` in `pyproject.toml`, and pin `marimo-studio` and
   every other dependency to releases on PyPI, which rejects dependencies that
   name a URL. Wait for CI to pass.
2. Tag that commit and push the tag:

   ```sh
   git tag -a v0.0.1 -m "manim-marimo 0.0.1"
   git push origin v0.0.1
   ```

The tag runs these jobs of `publish.yml`, each after the one before succeeds:

| Job            | Does                                                                     |
| -------------- | ------------------------------------------------------------------------ |
| Build          | Builds the wheel and sdist, then `scripts/release/check-dist.sh` and `scripts/release/check-release.sh` |
| PyPI           | Uploads both to the [`manim-marimo`](https://pypi.org/project/manim-marimo/) project through [trusted publishing](https://docs.pypi.org/trusted-publishers/) |
| Verify PyPI    | `scripts/release/verify-pypi.sh` installs the release from PyPI and loads the provider and its skill |
| GitHub release | Creates the `vX.Y.Z` release with both files and generated notes         |

`check-release.sh` stops the release unless the tag is annotated, names the
version in `pyproject.toml`, and points at a commit on `main` whose CI passed,
and unless the wheel declares no URL dependencies. The PyPI project trusts
`peter-gy/manim-marimo`, workflow `publish.yml`, and environment `pypi`.

## What a build contains

`uv build` runs the `agent_plugins.build.uv_build` backend. The wheel holds the
`manim_marimo` package with its starter files, and
`manim_marimo-<version>.agent-plugin/` with `plugin.json` and
`skills/manim-marimo/`. Check both after changing the build configuration:

```sh
pixi run build
scripts/release/check-dist.sh
```

## Documentation

`.github/workflows/pages.yml` builds `docs/` with VitePress on every pull
request and deploys it to GitHub Pages from `main`. The site's base path comes
from the Pages configuration, so local builds serve from `/`.
