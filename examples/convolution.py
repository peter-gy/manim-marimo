# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo", "marimo-manim", "numpy", "matplotlib"]
#
# [tool.marimo-studio]
# default = "animation"
# runtimes = ["server"]
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium", app_title="Convolution of dice")


@app.cell
def _():
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np

    return mo, np, plt


@app.cell(hide_code=True)
def introduction(mo):
    mo.md(r"""
    # Convolution of dice

    Every pair of die outcomes occupies a cell of a joint probability table.
    Cells on one diagonal have the same sum. Adding their probabilities gives
    the distribution of the sum.

    \[
    P(X+Y=s)=\sum_x P(X=x)P(Y=s-x).
    \]

    Inspired by 3Blue1Brown's *Convolutions* and its diagonal-sum scenes.
    """)
    return


@app.cell(hide_code=True)
def controls(mo):
    bias = mo.ui.slider(
        0, 1, step=0.1, value=0.4, label="Bias toward six", show_value=True
    )
    mo.hstack([bias], justify="start")
    return (bias,)


@app.cell
def distributions(bias, np):
    first = np.full(6, 1 / 6)
    second = (1 - bias.value) * np.full(6, 1 / 6)
    second[-1] += bias.value
    joint = np.outer(first, second)
    sums = np.arange(2, 13)
    probabilities = np.convolve(first, second)
    mean = float(sums @ probabilities)
    return first, joint, mean, probabilities, second, sums


@app.cell(hide_code=True)
def distribution_chart(mean, mo, plt, probabilities, sums):
    distribution_figure, axes = plt.subplots(figsize=(7, 3))
    axes.bar(sums, probabilities, color="#2b8cbe", width=0.75)
    axes.set(xlabel="Sum", ylabel="Probability", xticks=sums)
    mo.vstack(
        [
            distribution_figure,
            mo.md(
                f"Expected sum: **{mean:.2f}**. "
                f"Total probability: **{probabilities.sum():.3f}**."
            ),
        ]
    )
    return (distribution_figure,)


@app.cell(hide_code=True)
def joint_table(first, mo, second):
    mo.md(
        "| X / Y | 1 | 2 | 3 | 4 | 5 | 6 |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        + "\n".join(
            f"| {i + 1} | "
            + " | ".join(f"{float(first[i] * second[j]):.4f}" for j in range(6))
            + " |"
            for i in range(6)
        )
    )
    return


if __name__ == "__main__":
    app.run()
