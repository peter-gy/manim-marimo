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
app = marimo.App(width="medium", app_title="Fourier drawing")


@app.cell
def _():
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np

    return mo, np, plt


@app.cell(hide_code=True)
def introduction(mo):
    mo.md(r"""
    # Fourier drawing

    A closed path becomes a sum of rotating complex vectors. Sample the path,
    compute its Fourier coefficients, and compare the reconstruction as more
    frequencies enter the sum.

    \[
    c_k = \frac{1}{N}\sum_{j=0}^{N-1}z_j e^{-2\pi i k j/N},
    \qquad z(t) \approx \sum_k c_k e^{2\pi i k t}.
    \]

    Inspired by 3Blue1Brown's *Complex Fourier series*. The animation's layout
    and choreography live in the Studio view's `scene.py`.
    """)
    return


@app.cell(hide_code=True)
def controls(mo):
    shape = mo.ui.dropdown(["Heart", "Trefoil", "Ellipse"], value="Heart", label="Path")
    order = mo.ui.slider(
        1, 15, value=5, step=1, label="Frequency pairs", show_value=True
    )
    mo.hstack([shape, order], justify="start", gap=2)
    return order, shape


@app.cell
def sample_path(np, shape):
    sample_count = 512
    phase = np.arange(sample_count) / sample_count
    theta = 2 * np.pi * phase
    if shape.value == "Heart":
        signal = (
            16 * np.sin(theta) ** 3
            + 1j
            * (
                13 * np.cos(theta)
                - 5 * np.cos(2 * theta)
                - 2 * np.cos(3 * theta)
                - np.cos(4 * theta)
            )
        ) / 8
    elif shape.value == "Trefoil":
        signal = (2 + np.cos(3 * theta)) * np.exp(2j * theta) / 1.5
    else:
        signal = 2 * np.cos(theta) + 1.2j * np.sin(theta)
    return phase, sample_count, signal


@app.cell
def spectrum(np, order, sample_count, signal):
    all_coefficients = np.fft.fft(signal) / sample_count
    frequencies = np.array(
        [0] + [k for n in range(1, order.value + 1) for k in (n, -n)]
    )
    coefficients = all_coefficients[frequencies % sample_count]
    radii = np.abs(coefficients)
    return coefficients, frequencies, radii


@app.cell
def reconstruction(coefficients, frequencies, np, phase, signal):
    components = np.exp(2j * np.pi * phase[:, None] * frequencies) * coefficients
    approximation = components.sum(axis=1)
    rms_error = float(np.sqrt(np.mean(np.abs(signal - approximation) ** 2)))
    animation_phase = np.linspace(0, 1, 241)
    animation_vectors = (
        np.exp(2j * np.pi * animation_phase[:, None] * frequencies) * coefficients
    )
    chain_complex = np.column_stack(
        (np.zeros(len(animation_phase)), animation_vectors.cumsum(axis=1))
    )
    chain = np.stack((chain_complex.real, chain_complex.imag), axis=-1)
    return approximation, chain, rms_error


@app.cell(hide_code=True)
def comparison(approximation, mo, plt, rms_error, signal):
    figure, axes = plt.subplots(figsize=(7, 4))
    axes.plot(
        signal.real, signal.imag, color="#8997a7", linewidth=2, label="Sampled path"
    )
    axes.plot(
        approximation.real,
        approximation.imag,
        color="#2b8cbe",
        label="Fourier reconstruction",
    )
    axes.set_aspect("equal")
    axes.set(xlabel="Real", ylabel="Imaginary")
    axes.legend(frameon=False)
    mo.vstack([figure, mo.md(f"Root mean square error: **{rms_error:.5f}**")])
    return


if __name__ == "__main__":
    app.run()
