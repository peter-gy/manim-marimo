from pathlib import Path
from typing import Any

from marimo_manim import cell, output, value
from marimo_manim._reads import SceneReads, scene_reads


def test_value_reads_the_render_values_by_selector():
    with scene_reads(SceneReads(values={"spectrum.radii": [1, 2], "peak": None})):
        assert value("spectrum.radii") == [1, 2]
        assert value("peak", default=3) is None
        assert value("absent", default=3) == 3


def test_reads_return_their_defaults_outside_a_render():
    placeholder: Any = object()
    assert value("spectrum.radii", default=[]) == []
    assert output("figure", default=placeholder) is placeholder
    assert cell("chart") is None


def test_media_reads_without_a_current_image_return_their_defaults():
    placeholder: Any = object()
    with scene_reads(SceneReads(outputs={"figure": Path("figure.png")})):
        assert output("other", default=placeholder) is placeholder
        assert cell("figure") is None
