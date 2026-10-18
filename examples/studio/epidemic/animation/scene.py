# The city and SIR graph of 3Blue1Brown's "Simulating an epidemic", adapted
# from SIRSimulation and SIRGraph in
# https://github.com/3b1b/videos/blob/master/_2020/sir.py. That code is shared
# under CC BY-NC-SA 4.0, and so is this file. The notebook simulates every
# person, and this scene choreographs the result.
from pathlib import Path
from typing import cast

import manimpango
import numpy as np
from manimlib import (
    DOWN,
    GREY_B,
    LEFT,
    ORIGIN,
    RIGHT,
    UP,
    Axes,
    Circle,
    DashedLine,
    DecimalNumber,
    Dot,
    FadeIn,
    FadeOut,
    Integer,
    Line,
    Scene,
    Square,
    Text,
    ValueTracker,
    VGroup,
    VMobject,
    linear,
)

from manim_marimo import output, value

FONTS = Path(__file__).with_name("fonts")
for face in FONTS.glob("*.ttf"):
    manimpango.register_font(str(face))

SERIF = "CMU Serif"

SUSCEPTIBLE, INFECTIOUS, RECOVERED = "#58C4DD", "#FC6255", "#4f5661"
PALETTE = (SUSCEPTIBLE, INFECTIOUS, RECOVERED)
CITY = np.array([-3.3, -0.2, 0])
DAY_SECONDS = 0.5
NOBODY = [{"infected": None, "recovered": None, "source": None}]


class Animation(Scene):
    def construct(self):
        people = value("people", default=NOBODY)
        paths = np.asarray(value("paths", default=[[0, 0, 0, 0]]), dtype=float)
        history = np.asarray(value("history", default=[[1, 0, 0]] * 2), dtype=float)
        summary = value(
            "summary",
            default={"peak": 0, "peak_day": 0, "infected": 0, "reproduction": 0},
        )
        days = float(value("days", default=1))
        radius = float(value("infection_radius", default=0.5))
        distancing = float(value("distancing.value", default=0))

        city = Square(side_length=6.8).set_stroke(GREY_B, 1.5).move_to(CITY)
        scale = city.get_width() / float(value("city_size", default=7))
        paths = paths.reshape(len(people), -1, 2) * scale + CITY[:2]
        samples = len(history) - 1
        infected = np.array(
            [np.inf if p["infected"] is None else p["infected"] for p in people]
        )
        recovered = np.array(
            [np.inf if p["recovered"] is None else p["recovered"] for p in people]
        )
        source = np.array([-1 if p["source"] is None else p["source"] for p in people])

        def status_on(person, day):
            """Return 0, 1, or 2 for susceptible, infectious, or recovered."""
            if person["infected"] is None or day < person["infected"]:
                return 0
            return 1 if day < person["recovered"] else 2

        def place(day):
            """Return everyone's position, on a Catmull-Rom curve through the
            positions the notebook recorded."""
            sample = min(max(day / days * samples, 0), samples)
            index = min(int(sample), samples - 1)
            t = sample - index
            before, start, end, after = (
                paths[:, min(max(index + step, 0), samples)] for step in (-1, 0, 1, 2)
            )
            points = start + 0.5 * t * (
                (end - before)
                + t * (2 * before - 5 * start + 4 * end - after)
                + t * t * (3 * (start - end) + after - before)
            )
            return np.column_stack([points, np.zeros(len(points))])

        start = place(0)
        crowd = VGroup()
        for k, person in enumerate(people):
            dot = Dot(start[k], radius=0.06, fill_color=PALETTE[status_on(person, 0)])
            crowd.add(dot)
        rings = VGroup()
        for _ in people:
            ring = Circle(radius=radius * scale).set_stroke(INFECTIOUS, 0, 0)
            rings.add(ring)
        links = VGroup()
        for _ in people:
            link = Line(ORIGIN, RIGHT).set_stroke(INFECTIOUS, 1.6, 0)
            links.add(link)

        axes = Axes(
            (0, days, 7),
            (0, 1, 0.25),
            width=5.2,
            height=3.3,
            axis_config={
                "stroke_color": GREY_B,
                "stroke_width": 1.5,
                "include_tip": False,
            },
        )
        axes.move_to(np.array([3.75, -0.35, 0]))
        areas = VGroup(VMobject(), VMobject(), VMobject()).set_stroke(width=0)
        for area, color, opacity in zip(areas, PALETTE, (0.5, 1, 1), strict=True):
            area.set_fill(color, opacity)
        ticks = VGroup()
        for day in range(0, int(days) + 1, 7):
            tick = Text(str(day), font=SERIF, font_size=15, fill_color=GREY_B)
            ticks.add(tick.next_to(axes.c2p(day, 0), DOWN, buff=0.15))
        for share in (0.5, 1):
            tick = Text(f"{share:.0%}", font=SERIF, font_size=15, fill_color=GREY_B)
            ticks.add(tick.next_to(axes.c2p(0, share), LEFT, buff=0.15))
        day_label = Text("Day", font=SERIF, font_size=15, fill_color=GREY_B)
        ticks.add(day_label.next_to(axes.x_axis, DOWN, buff=0.45))

        title = Text("Simulating an epidemic", font=SERIF, font_size=30)
        title.next_to(axes, UP, buff=1.25).align_to(axes, LEFT)
        setting = Text(
            f"{len(people)} people  ·  {distancing:.0%} keep their distance",
            font=SERIF,
            font_size=17,
            fill_color=GREY_B,
        )
        setting.next_to(title, DOWN, buff=0.18).align_to(title, LEFT)

        legend, shares = VGroup(), []
        names = ("Susceptible", "Infectious", "Recovered")
        for name, color in zip(names, PALETTE, strict=True):
            swatch = Square(side_length=0.16).set_fill(color, 1).set_stroke(width=0)
            label = Text(name, font=SERIF, font_size=17, fill_color=GREY_B)
            label.next_to(swatch, RIGHT, 0.12)
            share = DecimalNumber(
                0,
                num_decimal_places=0,
                unit="%",
                font_size=20,
                text_config={"font": SERIF},
            )
            shares.append(share.next_to(label, RIGHT, 0.14))
            legend.add(VGroup(swatch, label, share))
        legend.arrange(RIGHT, buff=0.42).next_to(axes, DOWN, buff=0.7)
        legend.align_to(axes, LEFT)

        clock = ValueTracker(0)
        today = Integer(0, font_size=26, text_config={"font": SERIF})
        counter = VGroup(
            Text("Day", font=SERIF, font_size=22, fill_color=GREY_B), today
        )
        counter.arrange(RIGHT, buff=0.14).next_to(city, UP, buff=0.18)
        counter.align_to(city, LEFT)
        origin = axes.get_origin()
        unit = np.array([axes.x_axis.get_unit_size(), axes.y_axis.get_unit_size(), 0])
        times = np.linspace(0, days, samples + 1)
        shown = np.full(len(people), -1)
        drawn = np.zeros(len(people), dtype=bool)

        def advance(world):
            day = cast(float, clock.get_value())
            points = place(day)
            status = np.where(day < infected, 0, np.where(day < recovered, 1, 2))
            changed = status != shown
            shown[:] = status
            for dot, point in zip(crowd, points, strict=True):
                dot.move_to(point)
            for k in np.flatnonzero(changed).tolist():
                crowd[k].set_fill(PALETTE[status[k]])

            # 3Blue1Brown's rings pulse once a day out to the infection radius.
            for k in np.flatnonzero((status == 1) | changed).tolist():
                phase = (day - infected[k]) % 1
                sick = status[k] == 1
                fade = min(day - infected[k], recovered[k] - day, 1) if sick else 0
                rings[k].set_width(2 * scale * radius * (0.15 + 0.85 * phase))
                rings[k].move_to(points[k])
                rings[k].set_stroke(width=2.4 * (1 - phase), opacity=0.85 * fade)
            # Each new case links to the person who infected them for a day.
            linked = (source >= 0) & (infected <= day) & (day < infected + 1)
            for k in np.flatnonzero(linked | (linked != drawn)).tolist():
                fade = 0.9 * (1 - (day - infected[k])) if linked[k] else 0
                links[k].put_start_and_end_on(points[source[k]], points[k])
                links[k].set_stroke(opacity=fade)
            drawn[:] = linked

            # 3Blue1Brown's graph stacks the shares, infectious at the bottom.
            upto = min(int(day / days * samples), samples) + 1
            x = np.append(times[:upto], day)
            curve = np.vstack([history[:upto], history[upto - 1]])
            infectious, below = curve[:, 1], curve[:, 1] + curve[:, 0]
            bands = ((below, infectious), (infectious, 0 * x), (1 + 0 * x, below))
            for area, (top, bottom) in zip(areas, bands, strict=True):
                upper = np.column_stack([x, top, 0 * x])
                lower = np.column_stack([x, bottom, 0 * x])[::-1]
                outline = origin + np.vstack([upper, lower]) * unit
                area.set_points_as_corners([*outline, outline[0]])
            # Text redraws its glyphs, so a number changes only when it reads
            # differently.
            for share, reading in zip(shares, np.round(100 * curve[-1]), strict=True):
                if share.get_value() != reading:
                    share.set_value(reading)
            if today.get_value() != int(day):
                today.set_value(int(day))

        world = VGroup(links, rings, crowd)
        world.add_updater(advance)
        advance(world)
        self.play(
            FadeIn(VGroup(city, crowd, counter, axes, ticks, title, setting, legend)),
            run_time=0.8,
        )
        self.add(areas, world)
        zero = next((k for k, p in enumerate(people) if p["infected"] == 0), None)
        if zero is not None:
            note = Text("Patient zero", font=SERIF, font_size=16, fill_color=INFECTIOUS)
            note.next_to(crowd[zero], UP, buff=0.22)
            self.play(FadeIn(note, shift=0.1 * UP), run_time=0.4)
            self.wait(0.8)
            self.play(FadeOut(note), run_time=0.3)

        # The city holds still at its peak while the graph marks it, as
        # 3Blue1Brown's videos pause on the moment that matters.
        peak_day = float(summary["peak_day"])
        marker = DashedLine(
            axes.c2p(peak_day, 0), axes.c2p(peak_day, 1), dash_length=0.06
        )
        marker.set_stroke(GREY_B, 1.5)
        peak = Text(
            f"Peak {float(summary['peak']):.0%} on day {peak_day:g}",
            font=SERIF,
            font_size=17,
        )
        peak.next_to(marker, UP, buff=0.12)
        self.play(
            clock.animate.set_value(peak_day),
            run_time=max(peak_day * DAY_SECONDS, 0.1),
            rate_func=linear,
        )
        self.play(FadeIn(marker), FadeIn(peak), run_time=0.4)
        self.wait(1.2)
        self.play(
            clock.animate.set_value(days),
            run_time=max((days - peak_day) * DAY_SECONDS, 0.1),
            rate_func=linear,
        )
        world.clear_updaters()
        self.wait(0.6)

        chart = output("flattening_figure", height=2.7)
        if chart is not None:
            chart.move_to(axes).align_to(axes, LEFT)
            caption = Text(
                f"{float(summary['infected']):.0%} infected  ·  "
                f"each early case infects {float(summary['reproduction']):.1f}",
                font=SERIF,
                font_size=17,
                fill_color=GREY_B,
            )
            caption.next_to(chart, DOWN, buff=0.35).align_to(chart, LEFT)
            self.play(
                FadeOut(VGroup(axes, ticks, areas, marker, peak, legend)),
                FadeIn(chart),
                FadeIn(caption),
                run_time=0.8,
            )
        self.wait(1.5)
