#!/usr/bin/env bash
# Check that a tag push may publish a release: the tag is an annotated vX.Y.Z
# on main, it matches the package version, its release notes exist, CI passed
# for its commit, and the built wheel declares only dependencies PyPI accepts.
# Usage: check-release.sh, with GITHUB_REF, GITHUB_REF_NAME, GITHUB_SHA, and
# GH_REPO set as in a GitHub Actions tag push, and the wheel built in dist/.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

fail() {
	echo "ERROR: $1" >&2
	exit 1
}

for name in GITHUB_REF GITHUB_REF_NAME GITHUB_SHA GH_REPO; do
	[[ -n "${!name:-}" ]] || fail "$name is not set."
done

[[ "$GITHUB_REF_NAME" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] ||
	fail "Release tags take the form vX.Y.Z, not $GITHUB_REF_NAME."
[[ "$GITHUB_REF" == "refs/tags/$GITHUB_REF_NAME" ]] ||
	fail "$GITHUB_REF is not the tag $GITHUB_REF_NAME."
[[ "$(git cat-file -t "$GITHUB_REF")" == tag ]] ||
	fail "Tag $GITHUB_REF_NAME must be annotated: git tag -a $GITHUB_REF_NAME -m \"manim-marimo ${GITHUB_REF_NAME#v}\""

version="$(grep -m1 '^version = ' pyproject.toml | cut -d'"' -f2)"
[[ "v$version" == "$GITHUB_REF_NAME" ]] ||
	fail "Tag $GITHUB_REF_NAME does not match version $version in pyproject.toml."

notes=".github/release-notes/$GITHUB_REF_NAME.md"
[[ -s "$notes" ]] || fail "Release notes are missing or empty: $notes"

git merge-base --is-ancestor "$GITHUB_SHA" origin/main ||
	fail "Commit $GITHUB_SHA of $GITHUB_REF_NAME is not on main."

passed="$(gh run list --repo "$GH_REPO" --workflow ci.yml --commit "$GITHUB_SHA" --event push \
	--status success --json databaseId --jq length)"
[[ "$passed" -gt 0 ]] || fail "CI has not passed for $GITHUB_SHA on main."

# PyPI rejects packages whose dependencies name a URL instead of a release.
wheel="$(ls dist/manim_marimo-"$version"-*.whl)"
direct="$(unzip -p "$wheel" '*.dist-info/METADATA' | grep '^Requires-Dist: .* @ ' || true)"
[[ -z "$direct" ]] || fail "PyPI rejects direct URL dependencies. Pin a release instead of:
$direct"

echo "$GITHUB_REF_NAME may publish manim-marimo $version from $GITHUB_SHA."
