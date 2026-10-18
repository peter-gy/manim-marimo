#!/usr/bin/env bash
# Install a published release from PyPI in an isolated environment and check
# that it registers the provider and ships its agent skill. PyPI's index can
# lag a fresh upload, so the check retries for three minutes.
# Usage: verify-pypi.sh X.Y.Z
set -euo pipefail

version="${1:?Usage: verify-pypi.sh X.Y.Z}"
export UV_NO_CONFIG=1 RELEASE_VERSION="$version"

verify() {
	uv run --no-cache --no-project --isolated --default-index https://pypi.org/simple \
		--with "manim-marimo==$version" --with agent-plugins \
		python - <<'PY'
import os
import subprocess
from importlib.metadata import distribution, entry_points

assert distribution("manim-marimo").version == os.environ["RELEASE_VERSION"]
(point,) = [p for p in entry_points(group="marimo_studio.view_provider") if p.dist.name == "manim-marimo"]
assert point.name == "manim" and point.load().info.title == "Manim"
skill = subprocess.run(
    ["agent-plugins", "read", "manim-marimo"], check=True, capture_output=True, text=True
).stdout
assert "manim-marimo" in skill, skill
PY
}

for attempt in $(seq 1 18); do
	if verify; then
		echo "PyPI serves manim-marimo $version."
		exit 0
	fi
	echo "Attempt $attempt of 18 could not verify manim-marimo $version on PyPI."
	sleep 10
done
echo "ERROR: PyPI did not serve a working manim-marimo $version within three minutes." >&2
exit 1
