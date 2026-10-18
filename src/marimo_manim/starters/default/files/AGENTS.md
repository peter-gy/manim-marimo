# Manim view

`scene.py` owns animation layout and choreography. `index.html`, `style.css`,
and `player.js` own the surrounding page.

Read notebook results in the scene with `marimo_manim`:

- `value("spectrum.radii", default=[])` returns a value in its JSON form.
- `output("figure", height=3)` places a notebook value, such as a matplotlib
  figure, as an `ImageMobject`.
- `cell("distribution_chart", height=3)` places a named cell's output as an
  `ImageMobject` when that output is an image.

Write each target as a string literal. Studio finds those calls in the scene
and the project modules it imports, captures the results from the notebook,
and renders the scene again whenever one of them changes. Give every read a
default the scene can render: the build constructs each scene with every read
at its default, and a scene that fails there keeps the last published view.
Keep calculations and analytical controls in the notebook, and expose what
the scene needs as notebook variables.

Give `output()` a literal `height`, such as `output("figure", height=2.6)`, and
Studio draws the figure at that height, so its text reads at the scene's own
font sizes.

Each render traces every shape to the read it shows. Bind each read to a name
and index it with names and integers, such as `joint[i, j]`, or walk it with
`enumerate()` and `zip()`, so a Lens selection on a shape in Preview names the
read, such as `joint[2][3]`, and the line that created the shape.

Each `<marimo-output render="scene.py">` host on the page renders that scene
file, which defines one `manimlib.Scene` subclass. Add another scene file and
host to show a second animation. The markup inside a host is its player, and
`player.js` fills it from the host's `marimoRender` record, which lists
`animation.mp4`, `poster.png`, and `metadata.json`. The host's `data-state` is
`stale` while a new movie renders. Keep native `<marimo-cell>` hosts beside it
for the controls and outputs that belong in this view.

A static export renders one movie per state that `states.yaml` beside
`view.toml` lists. List every value each control can send:
`marimo-studio view preflight animation` warns with
`prepared-states-skip-control-values` for each control whose values the states
skip.
