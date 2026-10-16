---
title: View provider
description: The marimo-manim/manim provider's starter, options, project files, renders, and diagnostics.
---

# View provider

marimo-manim registers one marimo-studio
[view provider](https://marimo-team.github.io/marimo-studio/guide/view-providers)
under the key `marimo-manim/manim`, through the `marimo_studio.view_provider`
entry point. Studio discovers it in the notebook's environment when Studio
starts.

## Starter

| Starter ID                     | Title           | Files                                                           |
| ------------------------------ | --------------- | --------------------------------------------------------------- |
| `marimo-manim/manim:default`   | Manim animation | `scene.py`, `index.html`, `style.css`, `player.js`, `AGENTS.md` |

`index.html` lists the notebook's output cells as `<marimo-cell>` hosts beside
the player.

## Options

```toml
schema = 1
provider = "marimo-manim/manim"

[options]
quality = "preview"
```

| Option    | Values                              | Default                                                     |
| --------- | ----------------------------------- | ----------------------------------------------------------- |
| `quality` | `draft`, `preview`, `production`    | `preview` in Studio Preview, `production` in run mode and export |

## Project files

| Path                         | Role                                                         |
| ---------------------------- | ------------------------------------------------------------ |
| `index.html`                 | The page. Published.                                         |
| `*.css`, `*.js`, `public/**` | Page assets. Published.                                      |
| `*.py`                       | Scenes and helper modules. Private to the render.            |
| Other files                  | Private to the render, such as data a scene loads            |

Studio's Source panel edits the project's HTML, CSS, JavaScript, Python, JSON,
Markdown, TOML, SVG, and YAML files, such as `states.yaml`, with syntax
highlighting.

## Renders

Each `<marimo-output render="path.py">` host on `index.html` declares a render
of that scene file. A render reads the targets of every literal `value()`,
`output()`, and `cell()` call in the scene file and in the project modules it
imports. `output()` and `cell()` accept `image/png`, `image/jpeg`, and
`image/webp`.

| File            | Media type         | Role                         |
| --------------- | ------------------ | ---------------------------- |
| `animation.mp4` | `video/mp4`        | Main file, downloaded        |
| `poster.png`    | `image/png`        | Preview, the last frame      |
| `metadata.json` | `application/json` | `duration`, `fps`, `width`, `height` |

Each render runs in a worker process under Studio's command deadline. The build
runs every declared scene once with all reads at their defaults, skipping
animation and encoding.

## Diagnostics

| Code                    | Severity | Raised by  | Meaning                                                     |
| ----------------------- | -------- | ---------- | ----------------------------------------------------------- |
| `manim-input-missing`   | error    | Inspection | `index.html` is missing                                     |
| `manim-scene-missing`   | error    | Inspection | A render host names a scene file that does not exist        |
| `manim-source-invalid`  | error    | Inspection | A Python file in the project does not parse                 |
| `manim-read-dynamic`    | warning  | Inspection | A read's target is not a string literal                     |
| `manim-options-invalid` | error    | Build      | `quality` is not one of the listed values                   |
| `manim-render-failed`   | error    | Build, render | The scene raised. The message names the exception, and the location points at the deepest frame in the project. |

## Availability

The provider reports itself available when `manimgl` is installed and
imageio-ffmpeg locates an FFmpeg binary. `marimo-studio doctor` shows the
installed ManimGL version.
