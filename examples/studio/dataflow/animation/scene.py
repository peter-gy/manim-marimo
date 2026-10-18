from pathlib import Path

import manimpango
import numpy as np
from manimlib import (
    DOWN,
    RIGHT,
    UL,
    UP,
    Circle,
    FadeIn,
    FadeOut,
    LaggedStart,
    Scene,
    ShowCreation,
    StrokeArrow,
    SurroundingRectangle,
    Text,
    Transform,
    VGroup,
    smooth,
    squish_rate_func,
)

from manim_marimo import value

FONTS = Path(__file__).with_name("fonts")
for face in FONTS.glob("*.ttf"):
    manimpango.register_font(str(face))

SERIF = "CMU Serif"
MONO = "CMU Typewriter Text"
INK = "#ececec"
MUTED = "#848b94"
NOTEBOOK = "#83c167"
FOCUS = "#ffff00"
BACKWARD = "#fc6255"

ROW = -2.0
SPACING = 1.16
BEND = -np.pi / 1.8


def place(slot: float, count: int) -> np.ndarray:
    return np.array([(slot - (count - 1) / 2) * SPACING, ROW, 0.0])


def reference(
    start: np.ndarray, end: np.ndarray, color: str, opacity: float = 1
) -> StrokeArrow:
    # Every reference arcs above the row, so its tip shows its direction.
    # Restyling a StrokeArrow rebuilds its tip, so each style is a new arrow.
    bend = BEND if end[0] > start[0] else -BEND
    return StrokeArrow(
        start,
        end,
        buff=0.24,
        path_arc=bend,
        stroke_color=color,
        stroke_opacity=opacity,
        stroke_width=2.4,
        tip_width_ratio=4.5,
    )


def caption(text: str, colors: dict[str, str] | None = None) -> Text:
    line = Text(text, font=SERIF, font_size=28, fill_color=MUTED, t2c=colors or {})
    return line.to_corner(UL, buff=0.7).shift(0.62 * DOWN)


def swap(old: Text, new: Text) -> tuple[FadeOut, FadeIn]:
    # The old caption leaves before the new one arrives, so they never overlap.
    return (
        FadeOut(old, shift=0.15 * UP, rate_func=squish_rate_func(smooth, 0, 0.4)),
        FadeIn(new, shift=0.15 * UP, rate_func=squish_rate_func(smooth, 0.4, 0.8)),
    )


def name_label(name: str) -> Text:
    # A hidden bar gives every label the same height, so names with and
    # without descenders share one baseline below their cells.
    label = Text(f"{name}|", font=MONO, font_size=19, fill_color=INK)
    label[-1].set_opacity(0)
    return label


def hang(label: Text, point: np.ndarray) -> None:
    label.next_to(point, DOWN, buff=0.39)
    label.shift((point[0] - label[:-1].get_x()) * RIGHT)


class Animation(Scene):
    def construct(self):
        nodes = value(
            "nodes",
            default=[
                {"name": "a", "file": 1, "rank": 0},
                {"name": "b", "file": 0, "rank": 1},
            ],
        )
        edges = [tuple(edge) for edge in value("edges", default=[[1, 0]])]
        backward = int(value("backward", default=1))
        rerun = value("rerun", default={"slider": 1, "cells": [0]})
        slider = str(value("changed.value", default="a"))
        count = len(nodes)

        title = Text("A notebook is a dataflow graph", font=SERIF, font_size=44)
        title.to_corner(UL, buff=0.7)
        title.set_fill(INK)

        dots = VGroup()
        labels = VGroup()
        for node in nodes:
            dot = Circle(radius=0.17)
            dot.set_stroke(NOTEBOOK, width=2.5)
            dot.set_fill(NOTEBOOK, opacity=0.18)
            dot.move_to(place(node["file"], count))
            label = name_label(node["name"])
            hang(label, dot.get_center())
            dots.add(dot)
            labels.add(label)

        def link(
            source: int, target: int, color: str | None = None, opacity: float = 1
        ) -> StrokeArrow:
            start = dots[source].get_center()
            end = dots[target].get_center()
            if abs(end[0] - start[0]) < 1e-3:
                end = end + np.array([1e-3, 0, 0])
            forward = INK if end[0] > start[0] else BACKWARD
            return reference(start, end, color or forward, opacity)

        references = VGroup(*(link(source, target) for source, target in edges))

        first = caption(f"{count} cells, in the order the file lists them")
        self.play(FadeIn(title, shift=0.2 * UP), run_time=0.8)
        self.play(
            FadeIn(first),
            LaggedStart(
                *(
                    FadeIn(VGroup(dot, label), shift=0.15 * UP)
                    for dot, label in zip(dots, labels, strict=True)
                ),
                lag_ratio=0.08,
            ),
            run_time=1.6,
        )
        self.play(
            LaggedStart(*(ShowCreation(arrow) for arrow in references), lag_ratio=0.12),
            run_time=3,
        )
        second = caption(
            f"{backward} of {len(edges)} references point back up the file",
            {"point back up the file": BACKWARD},
        )
        self.play(*swap(first, second), run_time=1)
        self.wait(0.8)

        # As the cells slide into topological order, each backward reference
        # flips forward at the moment its cells pass each other.
        for arrow, (source, target) in zip(references, edges, strict=True):
            arrow.add_updater(
                lambda mob, source=source, target=target: mob.become(
                    link(source, target)
                )
            )
        for label, dot in zip(labels, dots, strict=True):
            label.add_updater(lambda mob, dot=dot: hang(mob, dot.get_center()))
        third = caption("In topological order, every reference points forward")
        self.play(
            *(
                dot.animate.move_to(place(node["rank"], count))
                for dot, node in zip(dots, nodes, strict=True)
            ),
            *swap(second, third),
            run_time=3,
        )
        for mob in [*references, *labels]:
            mob.clear_updaters()
        self.wait(1)

        trigger = rerun["slider"]
        affected = rerun["cells"]
        ring = SurroundingRectangle(VGroup(dots[trigger], labels[trigger]), buff=0.12)
        ring.set_stroke(FOCUS, width=3)
        fourth = caption(
            f"Moving {slider} reruns {len(affected)} of {count} cells, in this order",
            {slider: FOCUS},
        )
        quiet = [
            index
            for index in range(count)
            if index not in affected and index != trigger
        ]
        self.play(
            ShowCreation(ring),
            *swap(third, fourth),
            *(dots[index].animate.set_opacity(0.3) for index in quiet),
            *(labels[index][:-1].animate.set_opacity(0.35) for index in quiet),
            *(
                Transform(arrow, link(source, target, opacity=0.22))
                for arrow, (source, target) in zip(references, edges, strict=True)
                if target not in affected or source not in {trigger, *affected}
            ),
            run_time=1,
        )

        reached = {trigger}
        for step, index in enumerate(affected, start=1):
            incoming = [
                (arrow, source)
                for arrow, (source, target) in zip(references, edges, strict=True)
                if target == index and source in reached
            ]
            number = Text(str(step), font=SERIF, font_size=22, fill_color=FOCUS)
            number.move_to(dots[index])
            self.play(
                *(
                    Transform(arrow, link(source, index, FOCUS))
                    for arrow, source in incoming
                ),
                dots[index].animate.set_fill(FOCUS, opacity=0.25).set_stroke(FOCUS),
                FadeIn(number, scale=0.6),
                run_time=0.55,
            )
            reached.add(index)
        self.wait(2)
        self.play(FadeOut(ring), run_time=0.4)
        self.wait(0.6)
