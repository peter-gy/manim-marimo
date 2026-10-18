from typing import cast

import numpy as np
from manimlib import (
    BLUE,
    DOWN,
    UP,
    Circle,
    FadeIn,
    Scene,
    ShowCreation,
    Text,
    ValueTracker,
    VGroup,
    VMobject,
    linear,
)


class Animation(Scene):
    def construct(self):
        # Read notebook results with manim_marimo.value(), output(), and
        # cell(), such as value("trajectory", default=[]), and Studio renders
        # the scene again whenever they change.
        points = np.array([[-2, 0], [-1, 1.5], [0, 0], [1, -1.5], [2, 0]], dtype=float)
        title = Text("From data to motion", font="Arial", font_size=38)
        title.to_edge(UP, buff=0.7)
        curve = VMobject(stroke_color=BLUE, stroke_width=4)
        curve.set_points_smoothly(np.column_stack((points, np.zeros(len(points)))))
        dot = Circle(radius=0.08, fill_color=BLUE, fill_opacity=1, stroke_width=0)
        progress = ValueTracker(0)
        dot.add_updater(
            lambda mob: mob.move_to(
                curve.point_from_proportion(cast(float, progress.get_value()))
            )
        )
        caption = Text(
            "Computed in the notebook. Choreographed in the view.",
            font="Arial",
            font_size=22,
        )
        caption.to_edge(DOWN, buff=0.7)
        self.play(FadeIn(VGroup(title, caption)), ShowCreation(curve), run_time=1)
        self.add(dot)
        self.play(progress.animate.set_value(1), run_time=3, rate_func=linear)
        self.wait(0.5)
