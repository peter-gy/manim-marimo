#!/usr/bin/env bash
# Check that the built wheel ships the provider, its starter, and the agent
# skill, and registers the provider with Studio. Usage: check-dist.sh
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."
shopt -s nullglob
wheels=(dist/manim_marimo-*.whl)
if [[ ${#wheels[@]} -ne 1 ]]; then
	echo "ERROR: Expected one wheel in dist/, found ${#wheels[@]}." >&2
	exit 1
fi
wheel="${wheels[0]}"

contents="$(unzip -Z1 "$wheel")"
for path in \
	'manim_marimo/_provider.py' \
	'manim_marimo/starters/default/files/scene.py' \
	'manim_marimo-.*\.agent-plugin/plugin\.json' \
	'manim_marimo-.*\.agent-plugin/skills/manim-marimo/SKILL\.md'; do
	if ! grep -qx "$path" <<<"$contents"; then
		echo "ERROR: $wheel is missing $path." >&2
		exit 1
	fi
done

entry_points="$(unzip -p "$wheel" '*.dist-info/entry_points.txt')"
for line in 'manim = manim_marimo._provider:provider' 'manim-marimo-worker = manim_marimo._worker:main'; do
	if ! grep -qxF "$line" <<<"$entry_points"; then
		echo "ERROR: $wheel does not register: $line" >&2
		exit 1
	fi
done
echo "$wheel ships the provider, the starter, the worker, and the agent skill."
