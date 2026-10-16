# Security policy

## Supported versions

The latest release and `main` receive security fixes.

## Report a vulnerability

Report vulnerabilities through GitHub's
[private vulnerability reporting](https://github.com/peter-gy/marimo-manim/security/advisories/new).
Include the affected version, the steps or files that reproduce the issue, and
the impact you observed.

## Trust boundaries

A Manim view runs code. Studio renders a view's scene files as Python in a
worker process with the permissions of the user running Studio, and a notebook
runs its cells the same way. Open notebooks and view projects only from sources
you trust. Notebook values reach a scene as data, through JSON and image files
the worker reads.
