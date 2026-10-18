import io
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from itertools import pairwise
from pathlib import Path, PurePosixPath
from typing import Any

import pytest
from marimo_studio.view_providers import (
    ProviderCancellation,
    ProviderCommandResult,
    RenderRegion,
    RenderRequest,
    Representation,
    SourceLocation,
)
from PIL import Image

from marimo_manim._provider import provider

pytestmark = pytest.mark.render

SCENE = """\
import numpy as np
from manimlib import Circle, Dot, Scene, Square, ValueTracker, VGroup, linear
from marimo_manim import output, value


class Animation(Scene):
    def construct(self):
        heights, colors = value("heights", default=[1, 1]), value("colors", default=[])
        bars = VGroup()
        for index, (height, color) in enumerate(zip(heights, colors)):
            bar = Square(side_length=0.5, color=color).stretch_to_fit_height(height)
            bar.move_to(np.array([index - 3.0, 0, 0]))
            bars.add(bar)
        # Ticks follow the number of heights and show none of them.
        ticks = VGroup()
        for index in range(len(heights)):
            ticks.add(Dot(radius=0.02).move_to(np.array([index - 3.0, -1, 0])))
        # Markers sit on rings built from the heights and show none of them.
        rings = VGroup(*[Circle(radius=0.1 * height) for height in heights])
        markers = VGroup(*[Dot(radius=0.02) for _ in rings])
        for marker, ring in zip(markers, rings):
            marker.move_to(ring)
        path = np.asarray(value("path", default=[[0, 0], [1, 1]]), dtype=float)
        dot = Dot()
        progress = ValueTracker(0)

        def follow(mob):
            index = min(int(progress.get_value() * len(path)), len(path) - 1)
            mob.move_to(np.array([*path[index], 0]))

        dot.add_updater(follow)
        chart = output("figure", height=1)
        chart.to_corner()
        self.add(bars, ticks, rings, markers, dot, chart)
        self.play(progress.animate.set_value(1), run_time=1, rate_func=linear)
"""


class Runner:
    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        timeout: float = 120.0,
        environment: Mapping[str, str] | None = None,
    ) -> ProviderCommandResult:
        completed = subprocess.run(
            command, cwd=cwd, timeout=timeout, capture_output=True, text=True
        )
        return ProviderCommandResult(
            completed.returncode, completed.stdout, completed.stderr
        )


MOVING = """\
import numpy as np
from manimlib import Dot, Scene, ValueTracker, linear
from marimo_manim import value


class Animation(Scene):
    def construct(self):
        path = np.asarray(value("path", default=[0, 1]), dtype=float)
        dot = Dot()
        progress = ValueTracker(0)

        def follow(mob):
            index = min(int(progress.get_value() * len(path)), len(path) - 1)
            mob.move_to(np.array([path[index], 0, 0]))

        dot.add_updater(follow)
        self.add(dot)
        self.play(progress.animate.set_value(1), run_time=2, rate_func=linear)
"""


class SmallBudget(Runner):
    """Run the worker with room for four regions, as a long movie fills 4,000."""

    def run(self, command: Sequence[str], **kwargs: Any) -> ProviderCommandResult:
        start = (
            "import runpy, marimo_manim._lineage as lineage; lineage.MAX_REGIONS = 4; "
            "runpy.run_module('marimo_manim._worker', run_name='__main__')"
        )
        return super().run([sys.executable, "-c", start, command[-1]], **kwargs)


def render(
    tmp_path: Path,
    scene: str = SCENE,
    values: Mapping[str, Any] | None = None,
    runner: Runner | None = None,
) -> tuple[RenderRegion, ...]:
    template = tmp_path / "template"
    template.joinpath(".marimo-manim").mkdir(parents=True)
    template.joinpath(".marimo-manim", "video.json").write_text(
        json.dumps({"width": 320, "height": 180, "fps": 10})
    )
    template.joinpath("scene.py").write_text(scene)
    output = tmp_path / "output"
    output.mkdir()
    figure = io.BytesIO()
    Image.new("RGB", (64, 36), (255, 0, 0)).save(figure, format="PNG")
    result = provider.render(
        RenderRequest(
            source=PurePosixPath("scene.py"),
            template_root=template,
            values=values
            or {
                "heights": [1, 2],
                "colors": ["#ff0000", "#00ff00"],
                "path": [[-1, -1], [0, 0], [1, 1]],
            },
            outputs={"figure": Representation("image/png", figure.getvalue())},
            cells={},
            output_root=output,
            cancellation=ProviderCancellation(),
            runner=runner or Runner(),
            command_timeout=120,
        )
    )
    return result.regions


def test_shapes_that_show_reads_become_regions(tmp_path: Path):
    regions = render(tmp_path)

    assert {item.label for item in regions} == {
        "bar: Square",
        "rings: VGroup",
        "dot: Dot",
        "chart: ImageMobject",
    }


def test_shapes_carry_the_parts_of_the_reads_they_show(tmp_path: Path):
    regions = render(tmp_path)

    movie = [item for item in regions if item.file == PurePosixPath("animation.mp4")]
    bars = {item.reads for item in movie if item.label == "bar: Square"}
    assert bars == {("colors[0]", "heights[0]"), ("colors[1]", "heights[1]")}
    (chart,) = {
        (item.reads, item.source)
        for item in movie
        if item.label == "chart: ImageMobject"
    }
    assert chart == (("figure",), SourceLocation(PurePosixPath("scene.py"), 32, 9))
    # An updater moves the dot along the path, so each part of the video shows
    # the sample the dot sits on.
    dot = sorted(
        (item for item in movie if item.label == "dot: Dot"),
        key=lambda item: item.start or 0,
    )
    assert [item.reads for item in dot] == [("path[0]",), ("path[1]",), ("path[2]",)]
    assert dot[-1].end is None
    assert all(earlier.end == later.start for earlier, later in pairwise(dot))


def test_the_poster_carries_the_shapes_of_the_last_frame(tmp_path: Path):
    regions = render(tmp_path)

    poster = {
        item.label: item.reads
        for item in regions
        if item.file == PurePosixPath("poster.png")
    }
    assert poster["dot: Dot"] == ("path[2]",)
    assert poster["chart: ImageMobject"] == ("figure",)
    assert all(
        item.start is None and item.end is None
        for item in regions
        if item.file == PurePosixPath("poster.png")
    )


def test_a_shape_moving_on_every_frame_keeps_regions_for_the_whole_movie(
    tmp_path: Path,
):
    regions = render(
        tmp_path,
        MOVING,
        values={"path": [-2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2]},
        runner=SmallBudget(),
    )

    movie = sorted(
        (item for item in regions if item.file == PurePosixPath("animation.mp4")),
        key=lambda item: item.start or 0,
    )
    assert len(movie) == 3
    assert (movie[0].start, movie[-1].end) == (0.0, None)
    assert all(earlier.end == later.start for earlier, later in pairwise(movie))
    assert {read for item in movie for read in item.reads} == {
        f"path[{index}]" for index in range(9)
    }


def scene(body: str) -> str:
    lines = "".join(f"        {line}\n" for line in body.strip("\n").splitlines())
    return (
        "import numpy as np\n"
        "from manimlib import *\n"
        "from marimo_manim import value\n\n\n"
        "class Animation(Scene):\n"
        "    def construct(self):\n" + lines
    )


Shown = set[tuple[str | None, tuple[str, ...]]]


def poster(regions: tuple[RenderRegion, ...]) -> Shown:
    return {
        (item.label, item.reads)
        for item in regions
        if item.file == PurePosixPath("poster.png")
    }


def test_shapes_a_statement_only_places_beside_keep_their_reads(tmp_path: Path):
    regions = render(
        tmp_path,
        scene("""
names = value("names", default=["a"])
dot = Dot()
self.play(FadeIn(dot), run_time=value("speed", default=1))
label = Text(names[0]).next_to(dot, UP)
self.add(label)
self.wait(0.2)
"""),
        values={"names": ["hello"], "speed": 0.5},
    )

    assert poster(regions) == {('label: Text "hello"', ("names[0]",))}


def test_a_shape_shows_the_reads_of_the_animation_moving_it(tmp_path: Path):
    regions = render(
        tmp_path,
        scene("""
path = value("path", default=[0, 1])
dot = Dot()
self.add(dot)
self.play(dot.animate.move_to(RIGHT * path[0]), run_time=1)
self.play(dot.animate.move_to(RIGHT * path[1]), run_time=1)
"""),
        values={"path": [2, -2]},
    )

    movie = [item for item in regions if item.file == PurePosixPath("animation.mp4")]
    first = {read for item in movie if (item.start or 0) < 1 for read in item.reads}
    second = {read for item in movie if (item.start or 0) >= 1 for read in item.reads}
    assert (first, second) == ({"path[0]"}, {"path[1]"})


def test_a_name_holding_another_value_drops_the_read(tmp_path: Path):
    regions = render(
        tmp_path,
        scene("""
heights, probs = value("heights", default=[1]), value("probs", default=[0.1])
for i, v in enumerate(heights):
    self.add(Square(side_length=v).shift(RIGHT * i))
best = 0
for i, v in enumerate(probs):
    if v > best:
        best = v
self.add(Text(f"{best}"))
self.wait(0.2)
"""),
        values={"heights": [1, 2], "probs": [0.1, 0.9, 0.3]},
    )

    # The squares show heights, and the text shows probs[1] while the loop's
    # index has moved on to 2, so it names no part of probs.
    assert poster(regions) == {
        ("Square", ("heights[0]",)),
        ("Square", ("heights[1]",)),
    }


def test_a_shape_a_helper_builds_takes_the_reads_of_the_call(tmp_path: Path):
    regions = render(
        tmp_path,
        scene("""
heights = value("heights", default=[1])
p = value("p", default=0.5)

def make(p):
    return Square(side_length=p)

bar = make(heights[0])
self.add(bar)
self.wait(0.2)
"""),
        values={"heights": [2], "p": 0.75},
    )

    assert poster(regions) == {("bar: Square", ("heights[0]",))}


def test_keys_studio_reads_as_items_stay_in_brackets(tmp_path: Path):
    regions = render(
        tmp_path,
        scene("""
table = value("table", default={})
for key in ["_id", "größe", "size"]:
    self.add(Dot().set_opacity(table[key]))
self.wait(0.2)
"""),
        values={"table": {"_id": 1, "größe": 1, "size": 1}},
    )

    assert poster(regions) == {
        ("Dot", ('table["_id"]',)),
        ("Dot", ('table["größe"]',)),
        ("Dot", ("table.size",)),
    }


def test_a_tracing_error_leaves_the_render_unchanged(tmp_path: Path):
    regions = render(
        tmp_path,
        """\
from manimlib import Scene, Text, VGroup
from marimo_manim import value


class Caption(VGroup):
    def __init__(self, words):
        super().__init__()
        self.add(Text(words))

    @property
    def text(self):
        return self.submobjects[0].text


class Animation(Scene):
    def construct(self):
        self.add(Caption(value("words", default="hi")))
        self.wait(0.2)
""",
        values={"words": "hello"},
    )

    assert regions == ()


def test_a_name_reused_for_another_value_names_only_the_live_one(tmp_path: Path):
    regions = render(
        tmp_path,
        scene("""
heights = value("heights", default=[1])
bars = VGroup()
for k, height in enumerate(heights):
    color = BLUE if height > 1 else TEAL
    bars.add(Square(side_length=0.3, fill_color=color).shift(RIGHT * k))
keys = VGroup()
for color in (RED, GREEN):
    keys.add(Square(side_length=0.2, fill_color=color).shift(DOWN))
target = bars[0].copy().scale(2)
self.add(bars, keys, target)
self.wait(0.2)
"""),
        values={"heights": [1, 2]},
    )

    # The keys take their color from constants after the bars' loop ends. The
    # copy of the first bar shows what the bar shows, and scaling it leaves the
    # bar alone.
    assert poster(regions) == {
        ("Square", ("heights[0]",)),
        ("Square", ("heights[1]",)),
        ("target: Square", ("heights[0]",)),
    }


def test_a_shape_holding_still_keeps_its_exact_region_under_the_budget(
    tmp_path: Path,
):
    regions = render(
        tmp_path,
        scene("""
path = np.asarray(value("path", default=[0, 1]), dtype=float)
dot = Dot()
progress = ValueTracker(0)

def follow(mob):
    index = min(int(progress.get_value() * len(path)), len(path) - 1)
    mob.move_to(np.array([path[index], 0, 0]))

dot.add_updater(follow)
self.add(dot)
self.play(progress.animate.set_value(0.5), run_time=1, rate_func=linear)
self.wait(1)
self.play(progress.animate.set_value(1), run_time=1, rate_func=linear)
"""),
        values={"path": [-2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2]},
        runner=SmallBudget(),
    )

    # The pause from one to two seconds keeps a box the size of the dot, while
    # the movement around it shares the rest of the budget.
    movie = [item for item in regions if item.file == PurePosixPath("animation.mp4")]
    (pause,) = [
        item for item in movie if (item.start or 0) <= 1.1 and (item.end or 3) >= 1.9
    ]
    others = [item for item in movie if item is not pause]
    assert pause.rect.width < min(item.rect.width for item in others)


def test_a_comprehension_keeps_its_names_to_itself(tmp_path: Path):
    regions = render(
        tmp_path,
        scene("""
rows = value("rows", default=[{"size": 1}])
sizes = np.array([p["size"] for p in rows])
for k, p in enumerate(rows):
    self.add(Dot().shift(RIGHT * k).scale(float(sizes[k])))
self.wait(0.2)
"""),
        values={"rows": [{"size": 1}, {"size": 2}]},
    )

    # sizes holds a field of every row, so the dots name the table, and the
    # loop's own p and k leave the comprehension's p alone.
    assert poster(regions) == {("Dot", ("rows",))}


def test_a_shape_takes_the_reads_of_the_calls_made_on_it(tmp_path: Path):
    regions = render(
        tmp_path,
        scene("""
shift, speed = value("shift", default=1), value("speed", default=1)
flags = value("flags", default=[False])
dot = Dot()
square = Square(side_length=0.3)
self.play(dot.animate.shift(RIGHT * shift), run_time=speed)
if flags[0]: square.set_opacity(speed)
self.add(square)
self.wait(0.2)
"""),
        values={"shift": 1, "speed": 0.5, "flags": [False]},
    )

    # The play() call times the dot's move, and the square's change never ran.
    assert poster(regions) == {("dot: Dot", ("shift",))}


def test_an_updater_sees_the_binding_its_name_holds(tmp_path: Path):
    regions = render(
        tmp_path,
        scene("""
a, b = value("a", default=1), value("b", default=1)
x = a * 2
x = b * 2
dot = Dot()
dot.add_updater(lambda m: m.set_x(x))
self.add(dot)
self.wait(0.3)
"""),
        values={"a": 1, "b": 2},
    )

    assert poster(regions) == {("dot: Dot", ("b",))}
