# /// script
# requires-python = ">=3.10,<3.15"
#
# [tool.marimo-studio]
# default = "animation"
# runtimes = ["server"]
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium", app_title="A notebook is a dataflow graph")


@app.cell
def _():
    import ast
    import textwrap

    import marimo as mo

    return ast, mo, textwrap


@app.cell(hide_code=True)
def introduction(mo):
    mo.md(r"""
    # A notebook is a dataflow graph

    marimo reads which names each cell defines and which it references. An edge
    runs from the cell that defines a name to every cell that reads it, and the
    edges form a directed acyclic graph. Its cells therefore have a
    *topological order*, in which every edge points forward. When you move a
    slider, marimo reruns exactly the cells downstream of it, in that order.

    This notebook analyzes the small notebook below the same way: it parses
    the file, builds the graph, sorts it, lays it out in layers, and finds the
    cells each slider reruns. The Animation view's `scene.py` draws what this
    notebook computes and computes nothing of its own.
    """)
    return


@app.cell(hide_code=True)
def program(mo, textwrap):
    # A marimo file lists each cell as a function: its parameters are the names
    # it reads, and its return value names what it defines. Cells may appear in
    # any order.
    source = textwrap.dedent("""
    @app.cell
    def report(mo, figure, rmse):
        page = mo.vstack([figure, mo.md(f"RMS error {rmse:.3f}")])
        return (page,)

    @app.cell
    def points(mo):
        points = mo.ui.slider(20, 200, value=60, label="points")
        return (points,)

    @app.cell
    def grid(np, points):
        x = np.linspace(-1, 1, points.value)
        return (x,)

    @app.cell
    def chart(plt, x, y, y_hat):
        figure, axes = plt.subplots()
        axes.scatter(x, y)
        axes.plot(x, y_hat)
        return (figure,)

    @app.cell
    def truth(np, x):
        y_true = np.sin(3 * x)
        return (y_true,)

    @app.cell
    def noise(mo):
        noise = mo.ui.slider(0.0, 1.0, value=0.3, label="noise")
        return (noise,)

    @app.cell
    def sample(np, y_true, noise):
        y = y_true + noise.value * np.random.default_rng(0).normal(size=y_true.size)
        return (y,)

    @app.cell
    def degree(mo):
        degree = mo.ui.slider(1, 9, value=3, label="degree")
        return (degree,)

    @app.cell
    def fit(np, x, y, degree):
        coefficients = np.polyfit(x, y, degree.value)
        return (coefficients,)

    @app.cell
    def error(np, y, y_hat):
        rmse = float(np.sqrt(np.mean((y - y_hat) ** 2)))
        return (rmse,)

    @app.cell
    def predict(np, x, coefficients):
        y_hat = np.polyval(coefficients, x)
        return (y_hat,)
    """).strip()
    mo.md(f"```python\n{source}\n```")
    return (source,)


@app.cell
def graph(ast, source):
    # Each cell reads the names in its parameters and defines the names it
    # returns. Names no cell defines, such as mo and np, come from setup.
    cells = []
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
    definer = {
        name: index for index, cell in enumerate(cells) for name in cell["defines"]
    }
    edges = sorted(
        {
            (definer[name], target)
            for target, cell in enumerate(cells)
            for name in cell["reads"]
            if name in definer
        }
    )
    return cells, definer, edges


@app.cell
def topology(cells, edges):
    # Kahn's algorithm: repeatedly take the earliest cell in the file whose
    # inputs have all run. A cycle would leave cells behind.
    children = [
        [target for source_cell, target in edges if source_cell == index]
        for index in range(len(cells))
    ]
    _waiting = [
        sum(1 for _, target in edges if target == index) for index in range(len(cells))
    ]
    _ready = [index for index, count in enumerate(_waiting) if count == 0]
    topological = []
    while _ready:
        _current = min(_ready)
        _ready.remove(_current)
        topological.append(_current)
        for _child in children[_current]:
            _waiting[_child] -= 1
            if _waiting[_child] == 0:
                _ready.append(_child)
    if len(topological) != len(cells):
        raise ValueError("The cells form a cycle.")
    backward = sum(1 for source_cell, target in edges if source_cell > target)
    return backward, children, topological


@app.cell
def layout(cells, children, edges, topological):
    # A cell's layer is the longest path to it from a slider. Sliders sit one
    # layer before their first reader, and the cells of a layer stack by the
    # average height of their parents.
    _parents = [
        [source_cell for source_cell, target in edges if target == index]
        for index in range(len(cells))
    ]
    _layer = [0 for _ in cells]
    for _current in topological:
        for _child in children[_current]:
            _layer[_child] = max(_layer[_child], _layer[_current] + 1)
    for _index in range(len(cells)):
        if not _parents[_index] and children[_index]:
            _layer[_index] = min(_layer[child] for child in children[_index]) - 1
    _height = [0.0 for _ in cells]
    for _depth in range(max(_layer) + 1):
        _members = sorted(
            (index for index in topological if _layer[index] == _depth),
            key=lambda index: (
                -sum(_height[parent] for parent in _parents[index])
                / max(len(_parents[index]), 1)
            ),
        )
        for _slot, _member in enumerate(_members):
            _height[_member] = (len(_members) - 1) / 2 - _slot
    nodes = [
        {
            "name": cell["name"],
            "file": index,
            "rank": topological.index(index),
            "layer": _layer[index],
            "height": _height[index],
        }
        for index, cell in enumerate(cells)
    ]
    return (nodes,)


@app.cell(hide_code=True)
def nodes_table(mo, nodes):
    mo.ui.table(
        [
            {
                "cell": node["name"],
                "file position": node["file"] + 1,
                "topological position": node["rank"] + 1,
                "layer": node["layer"],
            }
            for node in sorted(nodes, key=lambda node: node["rank"])
        ],
        selection=None,
        pagination=False,
        label="The cells in topological order",
    )
    return


@app.cell(hide_code=True)
def controls(mo):
    changed = mo.ui.radio(
        ["points", "noise", "degree"], value="noise", label="Move a slider", inline=True
    )
    mo.hstack([changed], justify="start")
    return (changed,)


@app.cell
def cascade(cells, changed, children, definer, topological):
    # Moving a slider reruns the cells that read it, then everything
    # downstream of them, in topological order.
    _stale = {
        index for index, cell in enumerate(cells) if changed.value in cell["reads"]
    }
    _frontier = list(_stale)
    while _frontier:
        for _child in children[_frontier.pop()]:
            if _child not in _stale:
                _stale.add(_child)
                _frontier.append(_child)
    rerun = {
        "slider": definer[changed.value],
        "cells": [index for index in topological if index in _stale],
    }
    return (rerun,)


@app.cell(hide_code=True)
def summary(cells, changed, mo, rerun):
    mo.md(
        f"Moving **{changed.value}** reruns {len(rerun['cells'])} of {len(cells)} "
        "cells: " + " → ".join(f"`{cells[index]['name']}`" for index in rerun["cells"])
    )
    return


if __name__ == "__main__":
    app.run()
