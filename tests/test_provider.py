import os
import subprocess
from collections.abc import Mapping, Sequence
from importlib.metadata import version
from pathlib import Path, PurePosixPath

import pytest
from marimo_studio.view_providers import (
    BuildRequest,
    InspectionRequest,
    ProviderCancellation,
    ProviderCommandResult,
    Render,
    RenderCell,
    RenderOutput,
    RenderValue,
    SourceLocation,
    ViewProject,
)
from marimo_studio.view_providers.testing import check_provider

from marimo_manim._provider import provider

IMAGES = ("image/png", "image/jpeg", "image/webp")


class UnusedRunner:
    def run(self, *args: object, **kwargs: object) -> ProviderCommandResult:
        raise AssertionError("Inspection must not execute commands")


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


def inspect_project(root: Path, page: str, files: dict[str, str]):
    (root / "index.html").write_text(page)
    for name, source in files.items():
        root.joinpath(name).parent.mkdir(parents=True, exist_ok=True)
        root.joinpath(name).write_text(source)
    project = ViewProject("test", root, root / "view.toml", "marimo-manim/manim", {})
    return provider.inspect(
        InspectionRequest(project, UnusedRunner(), ProviderCancellation(), root, 10)
    )


def test_each_page_render_host_declares_its_scene_with_the_reads_it_reaches(
    tmp_path: Path,
):
    result = inspect_project(
        tmp_path,
        '<marimo-output render="intro.py"></marimo-output>\n'
        '<marimo-output render="scenes/main.py"></marimo-output>\n',
        {
            "intro.py": 'from marimo_manim import value\ntitle = value("title")\n',
            "scenes/main.py": (
                "import marimo_manim as mm\n"
                "from helpers.layout import grid\n"
                'figure = mm.output("figure")\n'
            ),
            "helpers/__init__.py": "",
            "helpers/layout.py": (
                "from marimo_manim import cell as place\n"
                'chart = place("distribution_chart")\n'
            ),
            "unused.py": 'from marimo_manim import value\nvalue("unused")\n',
        },
    )
    intro = PurePosixPath("intro.py")
    main = PurePosixPath("scenes/main.py")
    layout = PurePosixPath("helpers/layout.py")
    assert result.renders == (
        Render(intro, values=(RenderValue("title", SourceLocation(intro, 2, 15)),)),
        Render(
            main,
            outputs=(RenderOutput("figure", SourceLocation(main, 3, 20), IMAGES),),
            cells=(
                RenderCell("distribution_chart", SourceLocation(layout, 2, 15), IMAGES),
            ),
        ),
    )
    assert result.diagnostics == ()


def test_source_opens_view_files_in_their_editor_language(tmp_path: Path):
    result = inspect_project(
        tmp_path,
        '<marimo-output render="scene.py"></marimo-output>\n',
        {
            "scene.py": "from manimlib import Scene\n",
            "style.css": "body { margin: 0; }\n",
            "states.yaml": "schema: marimo-export.states.v1\n",
            "notes.md": "# Storyboard\n",
        },
    )

    assert {str(document.path): document.language for document in result.documents} == {
        "index.html": "html",
        "notes.md": "markdown",
        "scene.py": "python",
        "states.yaml": "yaml",
        "style.css": "css",
    }


def test_a_render_host_for_a_missing_scene_reports_the_host(tmp_path: Path):
    result = inspect_project(
        tmp_path, '<main>\n  <marimo-output render="scene.py"></marimo-output>\n', {}
    )
    (diagnostic,) = result.diagnostics
    assert (diagnostic.code, diagnostic.severity) == ("manim-scene-missing", "error")
    assert diagnostic.source == SourceLocation(PurePosixPath("index.html"), 2, 3)
    assert result.renders == ()


def test_inspection_warns_about_a_computed_target(tmp_path: Path):
    result = inspect_project(
        tmp_path,
        '<marimo-output render="scene.py"></marimo-output>',
        {
            "scene.py": (
                "from marimo_manim import output\n"
                'name = "chart"\n'
                "figure = output(name)\n"
            )
        },
    )
    (diagnostic,) = result.diagnostics
    assert (diagnostic.code, diagnostic.severity) == ("manim-read-dynamic", "warning")
    assert diagnostic.source == SourceLocation(PurePosixPath("scene.py"), 3, 10)
    assert result.renders == (Render(PurePosixPath("scene.py")),)


def test_inspection_reads_scene_source_and_reports_syntax_location(tmp_path: Path):
    result = inspect_project(
        tmp_path,
        '<marimo-output render="scene.py"></marimo-output>',
        {
            "scene.py": (
                'from pathlib import Path\nPath("executed").touch()\ndef broken(:\n'
            )
        },
    )
    diagnostic = next(d for d in result.diagnostics if d.code == "manim-source-invalid")
    assert diagnostic.source is not None
    assert diagnostic.source.path == PurePosixPath("scene.py")
    assert diagnostic.source.line == 3
    assert not (tmp_path / "executed").exists()


def test_availability_reports_a_worker_from_another_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    worker = tmp_path / "marimo-manim-worker"
    worker.write_text("#!/bin/sh\necho 'marimo-manim 0.0.1 with manimgl 1.7.2'\n")
    worker.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    availability = provider.availability()

    assert not availability.available
    assert availability.version == "0.0.1"
    assert availability.reason == (
        f"Scenes render with marimo-manim 0.0.1, and Studio runs marimo-manim "
        f"{version('marimo-manim')}."
    )


def test_availability_reports_the_release_that_renders_scenes():
    availability = provider.availability()

    assert availability.available
    assert availability.version == version("marimo-manim")


@pytest.mark.render
def test_installed_starter_publishes_its_page_and_renders_the_scene():
    (view,) = check_provider("marimo-manim/manim", options={"quality": "draft"})
    assert set(view.published) == {
        PurePosixPath("index.html"),
        PurePosixPath("player.js"),
        PurePosixPath("style.css"),
    }
    page = view.published[PurePosixPath("index.html")].decode()
    assert '<marimo-output render="scene.py"' in page
    render = view.renders[PurePosixPath("scene.py")]
    assert (render.main, render.preview) == (
        PurePosixPath("animation.mp4"),
        PurePosixPath("poster.png"),
    )
    assert render.media_types == {
        PurePosixPath("animation.mp4"): "video/mp4",
        PurePosixPath("poster.png"): "image/png",
        PurePosixPath("metadata.json"): "application/json",
    }
    assert render.files[PurePosixPath("animation.mp4")][4:8] == b"ftyp"
    assert not view.warnings


@pytest.mark.render
def test_build_sizes_outputs_placed_at_a_literal_height_in_points(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    inspection = inspect_project(
        root,
        '<marimo-output render="scene.py"></marimo-output>',
        {
            "scene.py": (
                "from manimlib import Scene\n"
                "from marimo_manim import output\n"
                "\n"
                "class Animation(Scene):\n"
                "    def construct(self):\n"
                '        output("chart", height=2)\n'
                '        output("photo")\n'
                "        self.wait(0.1)\n"
            )
        },
    )
    project = ViewProject("test", root, root / "view.toml", "marimo-manim/manim", {})
    roots = {name: tmp_path / name for name in ("staging", "template", "work", "cache")}
    for folder in roots.values():
        folder.mkdir()
    result = provider.build(
        BuildRequest(
            project,
            inspection,
            tuple(item.path for item in inspection.inputs),
            "revision",
            "development",
            roots["staging"],
            roots["template"],
            roots["work"],
            roots["cache"],
            ProviderCancellation(),
            Runner(),
            120,
        )
    )

    # Two scene units hold as much as Text(font_size=197).
    assert list(result.output_sizes) == [PurePosixPath("scene.py")]
    sizes = result.output_sizes[PurePosixPath("scene.py")]
    assert list(sizes) == ["chart"]
    assert sizes["chart"].width is None
    assert sizes["chart"].height == pytest.approx(197.37, abs=0.01)
