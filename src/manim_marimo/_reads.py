"""Read notebook results in view-authored Manim scenes."""

from __future__ import annotations

from collections.abc import Generator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from manimlib import ImageMobject, Mobject
    from marimo_studio.view_providers import JsonValue


@dataclass(frozen=True)
class SceneReads:
    """The notebook results one render supplies to its scene.

    ``outputs`` and ``cells`` map each available target to an image file.
    """

    values: Mapping[str, JsonValue] = field(default_factory=dict)
    outputs: Mapping[str, Path] = field(default_factory=dict)
    cells: Mapping[str, Path] = field(default_factory=dict)


_current: ContextVar[SceneReads | None] = ContextVar("manim_marimo_reads", default=None)


def value(selector: str, /, *, default: Any = None) -> Any:
    """Return the JSON form of the notebook value ``selector`` names.

    ``value("spectrum.radii")`` reads a field of the notebook variable
    ``spectrum``. A scene names each selector as a string literal, so the view
    knows which notebook values it renders from. Arrays arrive as nested lists,
    tables as lists of row objects, and dates as ISO 8601 text. A value the
    notebook has not computed returns ``default``, and so does every call when
    the scene runs outside Studio. A present ``None`` stays ``None``.
    """
    reads = _current.get()
    if reads is None:
        return default
    return reads.values.get(selector, default)


def output(
    selector: str, /, *, default: Mobject | None = None, **image: Any
) -> Mobject | None:
    """Return the notebook value ``selector`` names as an ``ImageMobject``.

    ``output("figure", height=3)`` places a matplotlib figure or a chart as
    the notebook draws it. Keyword arguments pass through to
    ``ImageMobject``. A value without an image form, a value the notebook has
    not computed, and every call outside a Studio render return ``default``.
    """
    reads = _current.get()
    return _image(reads.outputs.get(selector) if reads else None, default, image)


def cell(
    name: str, /, *, default: Mobject | None = None, **image: Any
) -> Mobject | None:
    """Return the output of the notebook cell ``name`` as an ``ImageMobject``.

    The cell's output arrives as marimo shows it, so a cell that ends with a
    matplotlib figure places that figure. An output that is not an image, such
    as text or a table, returns ``default``, as does every call outside a
    Studio render.
    """
    reads = _current.get()
    return _image(reads.cells.get(name) if reads else None, default, image)


def _image(
    path: Path | None, default: Mobject | None, image: Mapping[str, Any]
) -> ImageMobject | Mobject | None:
    if path is None:
        return default
    from manimlib import ImageMobject

    return ImageMobject(str(path), **image)


@contextmanager
def scene_reads(reads: SceneReads) -> Generator[None, None, None]:
    """Supply ``reads`` to ``value()``, ``output()``, and ``cell()`` calls."""
    token = _current.set(reads)
    try:
        yield
    finally:
        _current.reset(token)
