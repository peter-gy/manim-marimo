import numpy as np
from manimlib import (
    BLUE_C,
    DOWN,
    GOLD_C,
    GREY_B,
    TEAL_C,
    UP,
    FadeIn,
    FadeOut,
    FadeTransform,
    Rectangle,
    Scene,
    Text,
    VGroup,
)

from marimo_manim import output, value

FAIR = np.full(6, 1 / 6)


class Animation(Scene):
    def construct(self):
        joint = np.asarray(
            value("joint", default=np.outer(FAIR, FAIR).tolist()), dtype=float
        )
        probabilities = np.asarray(
            value("probabilities", default=np.convolve(FAIR, FAIR).tolist()),
            dtype=float,
        )
        if joint.shape != (6, 6) or probabilities.shape != (11,):
            raise ValueError(
                "joint must be a 6 x 6 table and probabilities must contain 11 sums."
            )
        title = Text("Convolution adds the diagonals", font="Arial", font_size=36)
        title.to_edge(UP, buff=0.55)
        subtitle = Text(
            "Every pair contributes to exactly one sum.", font="Arial", font_size=21
        )
        subtitle.next_to(title, DOWN, buff=0.25)
        squares = VGroup()
        for i in range(6):
            for j in range(6):
                square = Rectangle(
                    width=0.49,
                    height=0.49,
                    stroke_color=GREY_B,
                    stroke_width=0.6,
                    fill_color=BLUE_C,
                    fill_opacity=0.15 + 0.7 * joint[i, j] / joint.max(),
                )
                square.move_to(
                    np.array([-4.1 + 0.54 * j, 1.2 - 0.54 * i, 0], dtype=float)
                )
                squares.add(square)
        grid_label = Text("Joint probability", font="Arial", font_size=21)
        grid_label.move_to(np.array([-2.75, -2.3, 0], dtype=float))
        bars = VGroup()
        labels = VGroup()
        for index in range(len(probabilities)):
            x = 0.3 + 0.48 * index
            bar = Rectangle(
                width=0.32,
                height=0.01,
                fill_color=TEAL_C,
                fill_opacity=1,
                stroke_width=0,
            )
            bar.move_to(np.array([x, -1.5 + 0.005, 0], dtype=float))
            bars.add(bar)
            label = Text(str(index + 2), font="Arial", font_size=16)
            label.move_to(np.array([x, -1.8, 0], dtype=float))
            labels.add(label)
        chart_label = Text("Distribution of the sum", font="Arial", font_size=21)
        chart_label.move_to(np.array([2.7, -2.3, 0], dtype=float))
        self.play(
            FadeIn(
                VGroup(title, subtitle, squares, grid_label, bars, labels, chart_label)
            ),
            run_time=0.7,
        )
        for diagonal, probability in enumerate(probabilities):
            animations = []
            for i in range(6):
                for j in range(6):
                    active = i + j == diagonal
                    animations.append(
                        squares[i * 6 + j].animate.set_fill(
                            GOLD_C if active else BLUE_C,
                            opacity=0.9
                            if active
                            else 0.12 + 0.55 * joint[i, j] / joint.max(),
                        )
                    )
            height = max(0.01, float(probability) * 12)
            target = bars[diagonal].copy().set_height(height, stretch=True)
            target.move_to(
                np.array([0.3 + 0.48 * diagonal, -1.5 + height / 2, 0], dtype=float)
            )
            animations.append(bars[diagonal].animate.become(target))
            self.play(*animations, run_time=0.35)
        mean = Text(
            f"Expected sum  {float(value('mean', default=7)):.2f}",
            font="Arial",
            font_size=22,
        )
        mean.move_to(np.array([2.7, 1.9, 0], dtype=float))
        self.play(FadeIn(mean), run_time=0.4)
        self.wait(0.7)
        chart = output("distribution_figure", height=2.6)
        if chart is not None:
            chart.move_to(np.array([2.7, -0.55, 0], dtype=float))
            caption = Text("The notebook's chart", font="Arial", font_size=21)
            caption.move_to(chart_label)
            self.play(
                FadeOut(VGroup(bars, labels)),
                FadeIn(chart),
                FadeTransform(chart_label, caption),
                run_time=0.8,
            )
            self.wait(1.2)
