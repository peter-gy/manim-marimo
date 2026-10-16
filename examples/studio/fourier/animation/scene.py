from typing import cast

import numpy as np
from manimlib import (
    BLUE_C,
    DOWN,
    GREY_B,
    TEAL_C,
    UP,
    YELLOW,
    Circle,
    Dot,
    FadeIn,
    Line,
    Scene,
    ShowCreation,
    Text,
    ValueTracker,
    VGroup,
    VMobject,
    linear,
)

from marimo_manim import value


class Animation(Scene):
    def construct(self):
        circle = [
            [[0, 0], [np.cos(t), np.sin(t)]] for t in np.linspace(0, 2 * np.pi, 61)
        ]
        chain = np.asarray(value("chain", default=circle), dtype=float)
        radii = np.asarray(value("radii", default=[1]), dtype=float)
        if chain.ndim != 3 or chain.shape[2] != 2 or chain.shape[1] != len(radii) + 1:
            raise ValueError(
                "chain must have shape [frames, vectors + 1, 2], matching radii."
            )
        offset = np.array([-1.5, -0.2, 0])
        title = Text("A path, written in rotating vectors", font="Arial", font_size=34)
        title.to_edge(UP, buff=0.55)
        subtitle = Text(
            f"{value('shape.value', default='Circle')}  /  {len(radii)} frequencies",
            font="Arial",
            font_size=20,
        )
        subtitle.next_to(title, DOWN, buff=0.22)
        progress = ValueTracker(0)
        colors = [BLUE_C, TEAL_C, GREY_B]
        vectors = VGroup(
            *[
                Line(
                    np.zeros(3),
                    np.array([0.01, 0, 0]),
                    color=colors[k % 3],
                    stroke_width=2,
                )
                for k in range(len(radii))
            ]
        )
        circles = VGroup(
            *[
                Circle(
                    radius=max(float(r), 0.001),
                    stroke_color=GREY_B,
                    stroke_width=0.7,
                    stroke_opacity=0.45,
                )
                for r in radii
            ]
        )
        trace = VMobject(stroke_color=YELLOW, stroke_width=3)
        endpoint = Dot(radius=0.055, color=YELLOW)
        reference = VMobject(stroke_color=GREY_B, stroke_width=1, stroke_opacity=0.25)
        path = np.column_stack((chain[:, -1], np.zeros(len(chain)))) + offset
        reference.set_points_as_corners(path)

        def update_geometry(_mob):
            position = cast(float, progress.get_value()) * (len(chain) - 1)
            index = min(int(position), len(chain) - 2)
            weight = position - index
            frame = chain[index] * (1 - weight) + chain[index + 1] * weight
            points = np.column_stack((frame, np.zeros(len(frame)))) + offset
            for k, (vector, circle) in enumerate(zip(vectors, circles, strict=True)):
                start, end = points[k], points[k + 1]
                if np.linalg.norm(end - start) < 1e-6:
                    end = start + np.array([1e-6, 0, 0])
                vector.put_start_and_end_on(start, end)
                circle.move_to(start)
            trace.set_points_as_corners(np.vstack((path[: index + 1], points[-1])))
            endpoint.move_to(points[-1])

        diagram = VGroup(circles, vectors, trace, endpoint)
        diagram.add_updater(update_geometry)
        note = Text("Each circle carries one frequency.", font="Arial", font_size=21)
        note.move_to(np.array([4, 0.7, 0], dtype=float))
        error = Text(
            f"RMS error  {float(value('rms_error', default=0)):.5f}",
            font="Arial",
            font_size=20,
            color=GREY_B,
        )
        error.move_to(np.array([4, 0.1, 0], dtype=float))
        self.play(
            FadeIn(VGroup(title, subtitle, note, error)),
            ShowCreation(reference),
            run_time=0.8,
        )
        self.add(diagram)
        self.play(progress.animate.set_value(1), run_time=6, rate_func=linear)
        diagram.clear_updaters()
        self.wait(0.7)
