from pathlib import Path

import manimpango
import numpy as np
from manimlib import (
    DOWN,
    LEFT,
    UL,
    UP,
    Dot,
    FadeIn,
    LaggedStart,
    Line,
    Scene,
    ShowCreation,
    Text,
    VGroup,
)

from manim_marimo import value

FONTS = Path(__file__).with_name("fonts")
for face in FONTS.glob("*.ttf"):
    manimpango.register_font(str(face))

SERIF = "CMU Serif"
INK = "#ececec"
MUTED = "#848b94"
SCENE = "#58c4dd"


class Spectrum(Scene):
    def construct(self):
        frequencies = np.asarray(value("frequencies", default=[1, -1]), dtype=int)
        radii = np.asarray(value("radii", default=[0.25, 0.1]), dtype=float)
        order = np.argsort(frequencies)
        frequencies, radii = frequencies[order], radii[order]

        title = Text("One radius for each frequency", font=SERIF, font_size=44)
        title.set_fill(INK).to_corner(UL, buff=0.7)
        subtitle = Text(
            "The notebook's coefficients, from the slowest turn outward",
            font=SERIF,
            font_size=26,
            fill_color=MUTED,
        )
        subtitle.next_to(title, DOWN, buff=0.16, aligned_edge=LEFT)

        span = max(int(np.abs(frequencies).max()), 1)
        baseline = -2.4
        height = 4.4 / max(float(radii.max()), 1e-9)

        def x_of(frequency: int) -> float:
            return 6 * frequency / span

        axis = Line(np.array([-6.4, baseline, 0]), np.array([6.4, baseline, 0]))
        axis.set_stroke(INK, width=1.2, opacity=0.4)
        stems = VGroup()
        for frequency, radius in zip(frequencies, radii, strict=True):
            top = np.array([x_of(frequency), baseline + radius * height, 0])
            stem = Line(np.array([x_of(frequency), baseline, 0]), top)
            stem.set_stroke(SCENE, width=2)
            stems.add(VGroup(stem, Dot(top, radius=0.045, fill_color=SCENE)))
        ticks = VGroup()
        step = max(1, span // 4)
        for frequency in range(-span, span + 1, step):
            tick = Text(str(frequency), font=SERIF, font_size=20, fill_color=MUTED)
            tick.next_to(np.array([x_of(frequency), baseline, 0]), DOWN, buff=0.18)
            ticks.add(tick)

        self.play(FadeIn(title, shift=0.2 * UP), FadeIn(subtitle), run_time=0.8)
        self.play(ShowCreation(axis), FadeIn(ticks), run_time=0.6)
        self.play(
            LaggedStart(
                *(
                    ShowCreation(stems[index])
                    for index in np.argsort(np.abs(frequencies), kind="stable")
                ),
                lag_ratio=0.03,
            ),
            run_time=2.4,
        )
        self.wait(1)
