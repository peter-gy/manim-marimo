---
title: A notebook is a dataflow graph
description: A notebook analyzes a small notebook the way marimo does, and its scene draws which cells each slider reruns.
aside: false
---

# A notebook is a dataflow graph

marimo reads which names each cell defines and which it reads. An edge runs
from the cell that defines a name to every cell that reads it, and the edges
form a directed acyclic graph. When you move a slider, marimo reruns the cells
downstream of it, in an order where every edge points forward.

[`examples/dataflow.py`](https://github.com/peter-gy/manim-marimo/blob/main/examples/dataflow.py)
runs that analysis on a small notebook of eleven cells. The scene draws the
cells in the order the file lists them, slides them into topological order
until every reference points forward, then lights up the cells the chosen
slider reruns.

<ManimExample
  name="dataflow"
  notebook="examples/dataflow.py"
  scene="examples/studio/dataflow/animation/scene.py"
  stage="movie"
>

<<< ../../examples/studio/dataflow/animation/scene.py{python:line-numbers}

</ManimExample>

Open the notebook and its view in Studio from a clone of the repository:

```sh
pixi run edit dataflow
```

## The notebook computes the graph

A marimo file lists each cell as a function. Its parameters are the names it
reads and its return value names what it defines, so the notebook builds the
graph with Python's `ast` module alone:

```python
for _node in ast.parse(source).body:
    _returned = _node.body[-1].value
    _names = _returned.elts if isinstance(_returned, ast.Tuple) else [_returned]
    cells.append(
        {
            "name": _node.name,
            "reads": [argument.arg for argument in _node.args.args],
            "defines": [name.id for name in _names],
        }
    )
```

Kahn's algorithm then repeatedly takes the earliest cell whose inputs have all
run. A walk from the cells that read the chosen slider finds everything
downstream of it. The scene reads four results:

| Value      | Holds                                                                  |
| ---------- | ---------------------------------------------------------------------- |
| `nodes`    | Each cell's name, its position in the file, and its topological rank   |
| `edges`    | One `[source, target]` pair per reference between cells                |
| `backward` | How many references point back up the file                             |
| `rerun`    | The slider's cell and the cells it reruns, in topological order        |

The scene places the cells, draws an arc for each reference, and moves the
cells to their ranks. It sorts nothing and walks no graph itself.

| Slider moved | Cells that rerun                                              |
| ------------ | ------------------------------------------------------------- |
| `noise`      | 6: sample, fit, predict, chart, error, report                 |
| `points`     | 8: grid, truth, sample, fit, predict, chart, error, report    |
| `degree`     | 5: fit, predict, chart, error, report                         |

## The page

The view's page places the notebook's `controls` and `summary` cells under the
movie. A zero-python export prepares one movie per slider, and the **Page**
stage above switches between them.

```html
<marimo-output render="scene.py" aria-label="The notebook's cells, sorted and rerun">...</marimo-output>
<marimo-cell name="controls"></marimo-cell>
<marimo-cell name="summary"></marimo-cell>
```
