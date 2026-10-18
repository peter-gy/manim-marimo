from pathlib import Path
from typing import cast

import manimpango
import numpy as np
from manimlib import (
    DOWN,
    LEFT,
    UL,
    UP,
    Circle,
    Dot,
    FadeIn,
    Line,
    Mobject,
    Scene,
    StrokeArrow,
    Text,
    ValueTracker,
    VGroup,
    VMobject,
    linear,
)

from manim_marimo import value

FONTS = Path(__file__).with_name("fonts")
for face in FONTS.glob("*.ttf"):
    manimpango.register_font(str(face))

SERIF = "CMU Serif"
INK = "#ececec"
MUTED = "#848b94"
SCENE = "#58c4dd"
PLANE = "#29abca"
NOTEBOOK = "#83c167"
FOCUS = "#ffff00"

# The path is one unit wide in the notebook's coordinates. It fills this much
# of the frame, whichever bound it reaches first.
FIT = np.array([7.2, 5.4])
ORIGIN = np.array([1.1, -0.55, 0.0])
TURN = 9.0


def plane() -> VGroup:
    # A faint complex plane that fades away from the origin, as in
    # 3Blue1Brown's Fourier series scenes.
    lines = VGroup()
    for offset in np.arange(-7, 8):
        fade = max(0.0, 1 - abs(offset) / 7.5)
        line = Line(np.array([offset, -5, 0]), np.array([offset, 5, 0]))
        lines.add(line.set_stroke(PLANE, width=1, opacity=0.22 * fade))
        if abs(offset) <= 5:
            line = Line(np.array([-7.5, offset, 0]), np.array([7.5, offset, 0]))
            lines.add(line.set_stroke(PLANE, width=1, opacity=0.22 * fade))
    for start, end in (((-7.5, 0, 0), (7.5, 0, 0)), ((0, -5, 0), (0, 5, 0))):
        axis = Line(np.array(start), np.array(end))
        axis.set_stroke(INK, width=1.2, opacity=0.3)
        lines.add(axis)
    return lines.shift(ORIGIN)


class Animation(Scene):
    def construct(self):
        terms = np.asarray(value("terms", default=[[1, 0.25, 0.0]]), dtype=float)
        path_name = str(value("path.value", default="A circle"))
        circle = [
            [0.25 * np.cos(t), 0.25 * np.sin(t)] for t in np.linspace(0, 6.28, 64)
        ]
        traced = np.asarray(value("traced", default=circle), dtype=float)
        if terms.ndim != 2 or terms.shape[1] != 3:
            raise ValueError(
                "terms must have one [frequency, real, imaginary] row each."
            )
        # Vectors of no length add nothing to draw.
        terms = terms[np.hypot(terms[:, 1], terms[:, 2]) > 1e-6]

        frequencies = terms[:, 0]
        coefficients = terms[:, 1] + 1j * terms[:, 2]
        scale = float(min(FIT / np.maximum(np.ptp(traced, axis=0), 1e-6)))
        radii = np.abs(coefficients) * scale

        def chain(phase: float) -> np.ndarray:
            sums = np.cumsum(coefficients * np.exp(2j * np.pi * frequencies * phase))
            tips = np.concatenate(([0], sums)) * scale
            return np.column_stack((tips.real, tips.imag, np.zeros(len(tips)))) + ORIGIN

        path = np.column_stack((traced * scale, np.zeros(len(traced)))) + ORIGIN

        title = Text("A sum of rotating vectors", font=SERIF, font_size=44)
        title.set_fill(INK).to_corner(UL, buff=0.7)
        subtitle = Text(
            f"{path_name}: {len(terms)} rotating vectors, computed in the notebook",
            font=SERIF,
            font_size=26,
            fill_color=MUTED,
        )
        subtitle.next_to(title, DOWN, buff=0.16, aligned_edge=LEFT)

        circles = VGroup(
            *(
                Circle(radius=max(float(radius), 1e-3)).set_stroke(
                    SCENE, width=1, opacity=0.65 * min(1.0, float(radius) / 0.35)
                )
                for radius in radii
            )
        )
        vectors = VGroup(
            *(
                StrokeArrow(
                    ORIGIN,
                    ORIGIN + np.array([max(float(radius), 1e-3), 0, 0]),
                    buff=0,
                    stroke_color=INK,
                    stroke_width=2.2,
                    tip_width_ratio=5,
                )
                for radius in radii
            )
        )
        trace = VMobject().set_stroke(NOTEBOOK, width=3.5)
        pen = Dot(radius=0.06, fill_color=FOCUS)
        phase = ValueTracker(0)

        def follow(_group: Mobject) -> None:
            current = cast(float, phase.get_value())
            points = chain(current)
            for index, (circle, vector) in enumerate(
                zip(circles, vectors, strict=True)
            ):
                circle.move_to(points[index])
                start, end = points[index], points[index + 1]
                if np.linalg.norm(end - start) < 1e-4:
                    end = start + np.array([1e-4, 0, 0])
                vector.put_start_and_end_on(start, end)
            reached = max(1, int(current * len(path)))
            trace.set_points_as_corners([*path[:reached], points[-1]])
            pen.move_to(points[-1])

        machine = VGroup(circles, vectors, trace, pen)
        machine.add_updater(follow)
        follow(machine)

        self.play(FadeIn(plane()), FadeIn(title, shift=0.2 * UP), run_time=1)
        self.play(FadeIn(subtitle), FadeIn(machine), run_time=0.8)
        self.play(phase.animate.set_value(1), run_time=TURN, rate_func=linear)
        machine.clear_updaters()
        self.wait(1.6)
