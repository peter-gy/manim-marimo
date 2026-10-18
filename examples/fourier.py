# /// script
# requires-python = ">=3.10,<3.15"
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
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath

    return FontProperties, TextPath, mo, np, plt


@app.cell(hide_code=True)
def introduction(mo):
    mo.md(r"""
    # Fourier drawing

    Any closed path is a sum of rotating vectors. Sample the path as complex
    numbers $z_j$, and its Fourier coefficients give each vector its length
    and starting angle:

    \[
    c_k = \frac{1}{N}\sum_{j=0}^{N-1}z_j e^{-2\pi i k j/N},
    \qquad z(t) \approx \sum_k c_k e^{2\pi i k t}.
    \]

    The notebook keeps the frequencies $\pm1, \pm2, \dots$ up to the slider's
    value and reconstructs the path from them. The Animation view's
    `scene.py` turns the vectors and traces their tip. Inspired by
    3Blue1Brown's *But what is a Fourier series?*
    """)
    return


@app.cell(hide_code=True)
def controls(mo):
    path = mo.ui.dropdown(
        ["manim-marimo mark", "TeX's italic m"], value="manim-marimo mark", label="Path"
    )
    pairs = mo.ui.slider(
        steps=[2, 4, 8, 16, 32, 48], value=48, label="Frequency pairs", show_value=True
    )
    mo.hstack([path, pairs], justify="start", gap=2)
    return pairs, path


@app.cell
def mark(np):
    # manim-marimo's mark is marimo's looped circle, drawn by five rotating
    # vectors: one turns four times while four short ones let the loops drift.
    # Each row is a frequency, a length, and a starting angle.
    mark_vectors = [
        (4, 1.0, np.pi / 4),
        (-4, 0.05, 1.2),
        (1, 0.06, 2.8),
        (2, 0.045, 0.0),
        (3, 0.032, 1.7),
    ]
    return (mark_vectors,)


@app.cell
def outline(FontProperties, TextPath, mark_vectors, np, path):
    sample_count = 1024
    phase = np.arange(sample_count) / sample_count
    if path.value == "manim-marimo mark":
        signal = sum(
            length * np.exp(1j * (2 * np.pi * frequency * phase + angle))
            for frequency, length, angle in mark_vectors
        )
    else:
        # The glyph's outline is one closed curve. Resampling it at equal arc
        # length gives every stretch of the path the same weight.
        glyph = TextPath(
            (0, 0), "$m$", size=1, prop=FontProperties(math_fontfamily="cm")
        )
        polygon = glyph.to_polygons(closed_only=True)[0]
        arc = np.r_[0, np.cumsum(np.hypot(*np.diff(polygon, axis=0).T))]
        along = phase * arc[-1]
        signal = np.interp(along, arc, polygon[:, 0]) + 1j * np.interp(
            along, arc, polygon[:, 1]
        )
    signal = (signal - signal.mean()) / np.ptp(signal.real)
    return phase, sample_count, signal


@app.cell
def spectrum(np, pairs, sample_count, signal):
    all_coefficients = np.fft.fft(signal) / sample_count
    frequencies = np.array([k for n in range(1, pairs.value + 1) for k in (n, -n)])
    # Chaining the longest vectors first keeps the chain's tip steady.
    frequencies = frequencies[
        np.argsort(-np.abs(all_coefficients[frequencies % sample_count]), kind="stable")
    ]
    coefficients = all_coefficients[frequencies % sample_count]
    radii = np.abs(coefficients)
    terms = np.column_stack((frequencies, coefficients.real, coefficients.imag))
    return coefficients, frequencies, radii, terms


@app.cell
def reconstruction(coefficients, frequencies, np, phase, signal):
    approximation = (
        np.exp(2j * np.pi * phase[:, None] * frequencies) * coefficients
    ).sum(axis=1)
    rms_error = float(np.sqrt(np.mean(np.abs(signal - approximation) ** 2)))
    # The scene traces this path, one point per frame of its single turn.
    traced = np.column_stack((approximation.real, approximation.imag))[::2]
    return approximation, rms_error, traced


@app.cell(hide_code=True)
def comparison(approximation, mo, pairs, plt, rms_error, signal):
    figure, axes = plt.subplots(figsize=(7, 3.6))
    axes.plot(
        signal.real, signal.imag, color="#9aa1a9", linewidth=3, label="Sampled path"
    )
    axes.plot(
        approximation.real,
        approximation.imag,
        color="#1c758a",
        linewidth=1.5,
        label=f"{2 * pairs.value} rotating vectors",
    )
    axes.set_aspect("equal")
    axes.axis("off")
    axes.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.32, 1))
    mo.vstack([figure, mo.md(f"Root mean square error: **{rms_error:.4f}**")])
    return


if __name__ == "__main__":
    app.run()
