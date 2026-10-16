import numpy as np
from manimlib import (
    BLUE_C,
    DOWN,
    GREY_B,
    UP,
    FadeIn,
    GrowFromEdge,
    LaggedStart,
    Line,
    Rectangle,
    Scene,
    Text,
    VGroup,
)

from marimo_manim import value


class Spectrum(Scene):
    def construct(self):
        frequencies = np.asarray(value("frequencies", default=[0]), dtype=int)
        radii = np.asarray(value("radii", default=[1]), dtype=float)
        order = np.argsort(frequencies)
        frequencies, radii = frequencies[order], radii[order]
        title = Text("One radius for each frequency", font="Arial", font_size=34)
        title.to_edge(UP, buff=0.6)
        width = min(0.8, 11 / len(radii))
        scale = 3.6 / max(float(radii.max()), 1e-9)
        baseline = -1.6
        axis = Line(
            np.array([-6, baseline, 0]), np.array([6, baseline, 0]), stroke_color=GREY_B
        )
        bars = VGroup()
        labels = VGroup()
        for index, (frequency, radius) in enumerate(
            zip(frequencies, radii, strict=True)
        ):
            x = (index - (len(radii) - 1) / 2) * width * 1.15
            bar = Rectangle(
                width=width,
                height=max(float(radius) * scale, 0.02),
                fill_color=BLUE_C,
                fill_opacity=0.9,
                stroke_width=0,
            )
            bar.move_to(np.array([x, baseline, 0]), aligned_edge=DOWN)
            bars.add(bar)
            label = Text(str(frequency), font="Arial", font_size=16, color=GREY_B)
            label.next_to(bar, DOWN, buff=0.12).set_y(baseline - 0.25)
            labels.add(label)
        self.play(FadeIn(VGroup(title, axis, labels)), run_time=0.6)
        self.play(
            LaggedStart(*(GrowFromEdge(bar, DOWN) for bar in bars), lag_ratio=0.08),
            run_time=2,
        )
        self.wait(0.8)
