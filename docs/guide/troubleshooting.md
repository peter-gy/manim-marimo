---
title: Troubleshooting
description: Match a Manim view symptom to its cause and repair.
---

# Troubleshooting

Studio shows provider diagnostics beside the source line they name. Start with
the first error in Source or in `marimo-studio view inspect`.

| Symptom                                                  | Cause                                                       | Repair                                                                      |
| -------------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------- |
| The build fails at a scene line                          | The scene fails with every read at its default              | Give the read a default the scene can render                                |
| `manim-scene-missing` at a host in `index.html`          | The host names a scene file that does not exist             | Create the file or show another scene                                       |
| `Found none` in a render error                           | The scene file defines no `manimlib.Scene` subclass         | Define one scene class in the file                                          |
| `Found A, B` in a render error                           | The file defines two unrelated scene classes                | Move one into its own scene file with its own render host                   |
| `manim-read-dynamic` warning                             | A read's target is computed                                 | Write the target as a string literal                                        |
| The toolbar says `Showing the default for <target>.`     | The notebook has no current result, or it has no image form | Run the cell, check the selector, or read a figure variable with `output()` |
| `The scene contains no frames`                           | `construct()` neither plays nor waits                       | Add `self.play()` or `self.wait()`                                          |
| A movie stays `stale` for a long time                    | The scene renders slowly                                    | Set `quality = "draft"` while iterating, or shorten `run_time`              |
| OpenGL errors on Linux                                   | No usable OpenGL driver                                     | Install Mesa as [Run and export](./run-and-export.md#linux-servers) shows   |
| `Tex` fails to render                                    | No LaTeX on the machine that renders                        | Install LaTeX, or use `Text`                                                |

Studio's
[troubleshooting guide](https://marimo-team.github.io/marimo-studio/guide/troubleshooting)
covers builds, previews, and sessions for every view.
