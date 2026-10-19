"""Render view-authored Manim scenes beside a page of native notebook results.

A view project holds a page, ``index.html`` with its styles and scripts, and
scene files. Each ``<marimo-output render="scene.py">`` host on the page
declares a render of that scene file. A scene reads notebook results with
``manim_marimo.value()``, ``output()``, and ``cell()``, and inspection finds
those calls in the scene and the project modules it imports, without running
them.

The build publishes the page, keeps the scenes private in the render template,
and constructs each scene with every read at its default, so a scene that
cannot run keeps the last published view. Studio renders a scene whenever a
result it reads changes, in an owned worker process, and publishes the movie,
its poster, and its metadata together.

A render also traces the shapes of each frame to the notebook results they
show, and returns them as regions of the movie and its poster. A page then
lets a reader select a shape at the moment it is on screen and follow it to the
cells that computed it.
"""

from __future__ import annotations

import ast
import html
import json
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from typing import Any

from marimo_studio.view_providers import (
    BuildInput,
    BuildProfile,
    BuildRequest,
    BuildResult,
    InspectionRequest,
    PackagedStarter,
    ProjectDiagnostic,
    ProjectInspection,
    ProviderAvailability,
    ProviderError,
    ProviderInfo,
    ProviderStarter,
    Rect,
    Render,
    RenderCell,
    RenderFile,
    RenderOutput,
    RenderRegion,
    RenderRequest,
    RenderResult,
    RenderValue,
    Representation,
    Size,
    SourceDocument,
    SourceLocation,
    StarterContext,
    StarterMarkers,
    StarterPlan,
    ViewProject,
    copy_inputs,
    create_starter,
    html_sites,
    probe_tool,
    project_files,
    project_path,
)

from manim_marimo._render import (
    RenderFailure,
    SceneJob,
    VideoFormat,
    run_scene,
    worker,
)

_INSTALL = (
    "Add manim-marimo[render] to the notebook's dependencies and open it with "
    "marimo edit --sandbox=pixi, or install manim-marimo[render] where Studio runs."
)

_PAGE = PurePosixPath("index.html")
_VIDEO = PurePosixPath(".manim-marimo/video.json")
_READS = PurePosixPath(".manim-marimo/reads")
_MOVIE = PurePosixPath("animation.mp4")
_POSTER = PurePosixPath("poster.png")
_METADATA = PurePosixPath("metadata.json")
_LANGUAGES = {
    ".html": "html",
    ".css": "css",
    ".js": "javascript",
    ".py": "python",
    ".json": "json",
    ".md": "markdown",
    ".toml": "toml",
    ".svg": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}
_QUALITY = {
    "draft": VideoFormat(640, 360, 15),
    "preview": VideoFormat(960, 540, 24),
    "production": VideoFormat(1920, 1080, 30),
}
# ImageMobject reads these through Pillow, in order of preference.
_IMAGES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
_ACCEPT = tuple(_IMAGES)
# ManimGL scales Text by 0.0076 scene units per SVG pixel, and Pango draws one
# point as 4/3 pixels, so a scene unit holds about 99 points of Text.
_POINTS_PER_UNIT = 1 / (0.0076 * 4 / 3)


def _markers(context: StarterContext) -> StarterMarkers:
    targets = context.output_cells
    return StarterMarkers(
        {
            # index.html indents the marker inside <section class="context">.
            "__CELLS__": "\n      ".join(
                f'<marimo-cell name="{html.escape(target.target, quote=True)}">'
                "</marimo-cell>"
                for target in targets
            )
        },
        targets,
    )


_STARTERS = (
    PackagedStarter(
        ProviderStarter(
            key="default",
            title="Manim animation",
            summary="A Manim scene, a video player, and native notebook context.",
            documents=(_PAGE, PurePosixPath("scene.py")),
        ),
        package="manim_marimo.starters.default",
        markers=_markers,
    ),
)


def _video(project: ViewProject, profile: BuildProfile) -> VideoFormat:
    quality = project.options.get(
        "quality", "production" if profile == "production" else "preview"
    )
    if not isinstance(quality, str) or quality not in _QUALITY:
        raise ProviderError(
            "quality must be draft, preview, or production.",
            source=SourceLocation(PurePosixPath("view.toml"), 1, 1),
            code="manim-options-invalid",
        )
    return _QUALITY[quality]


def _is_page_file(path: PurePosixPath) -> bool:
    return path == _PAGE or path.suffix in {".css", ".js"} or path.parts[0] == "assets"


class _RenderHosts(HTMLParser):
    """Collect each ``<marimo-output render>`` host with its position."""

    def __init__(self) -> None:
        super().__init__()
        self.hosts: list[tuple[str, SourceLocation]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        render = dict(attrs).get("render")
        if tag == "marimo-output" and render:
            line, offset = self.getpos()
            self.hosts.append((render, SourceLocation(_PAGE, line, offset + 1)))


@dataclass
class _Module:
    """The project modules one Python file imports and the results it reads."""

    imports: set[str] = field(default_factory=set)
    values: list[RenderValue] = field(default_factory=list)
    outputs: list[RenderOutput] = field(default_factory=list)
    cells: list[RenderCell] = field(default_factory=list)
    # The literal height in scene units at which ``output()`` places a target.
    heights: dict[str, float] = field(default_factory=dict)


def _module_name(path: PurePosixPath) -> str:
    parts = path.with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _module(
    path: PurePosixPath, tree: ast.Module
) -> tuple[_Module, list[ProjectDiagnostic]]:
    """Return the imports and literal ``manim_marimo`` reads of one module."""
    reads = {"value", "output", "cell"}
    functions = {f"manim_marimo.{read}": read for read in reads}
    modules: set[str] = set()
    found = _Module()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.imports.add(node.module)
            found.imports.update(f"{node.module}.{alias.name}" for alias in node.names)
            if node.module == "manim_marimo":
                functions.update(
                    (alias.asname or alias.name, alias.name)
                    for alias in node.names
                    if alias.name in reads
                )
        elif isinstance(node, ast.Import):
            found.imports.update(alias.name for alias in node.names)
            modules.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "manim_marimo"
            )
    diagnostics: list[ProjectDiagnostic] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Name):
            read = functions.get(function.id)
        elif (
            isinstance(function, ast.Attribute)
            and function.attr in reads
            and isinstance(function.value, ast.Name)
            and function.value.id in modules
        ):
            read = function.attr
        else:
            read = None
        if read is None:
            continue
        target = node.args[0] if node.args else None
        if not (isinstance(target, ast.Constant) and isinstance(target.value, str)):
            diagnostics.append(
                ProjectDiagnostic(
                    "manim-read-dynamic",
                    "warning",
                    f"{read}() needs a string literal target, so this call "
                    "always returns its default.",
                    f'Write the target as text, such as {read}("spectrum").',
                    SourceLocation(path, node.lineno, node.col_offset + 1),
                )
            )
            continue
        location = SourceLocation(path, target.lineno, target.col_offset + 1)
        if read == "value":
            found.values.append(RenderValue(target.value, location))
        elif read == "output":
            found.outputs.append(RenderOutput(target.value, location, _ACCEPT))
            height = next(
                (item.value for item in node.keywords if item.arg == "height"), None
            )
            if isinstance(height, ast.Constant) and isinstance(
                height.value, int | float
            ):
                found.heights.setdefault(target.value, float(height.value))
        else:
            found.cells.append(RenderCell(target.value, location, _ACCEPT))
    return found, diagnostics


def _reached(
    scene: PurePosixPath, modules: dict[PurePosixPath, _Module]
) -> list[_Module]:
    """Return ``scene`` and every project module it imports, directly or not."""
    names = {_module_name(path): path for path in modules}
    seen: set[PurePosixPath] = set()
    pending = [scene]
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        pending.extend(names[name] for name in modules[path].imports if name in names)
    return [modules[path] for path in sorted(seen)]


def _render(scene: PurePosixPath, modules: dict[PurePosixPath, _Module]) -> Render:
    """Declare ``scene`` with the reads of every project module it reaches."""
    reached = _reached(scene, modules)
    return Render(
        scene,
        values=tuple(read for module in reached for read in module.values),
        outputs=tuple(read for module in reached for read in module.outputs),
        cells=tuple(read for module in reached for read in module.cells),
    )


def _output_sizes(request: BuildRequest) -> dict[PurePosixPath, dict[str, Size]]:
    """Return the size of each output a scene places at a literal height.

    Studio draws a figure at that size, so its text appears at the scene's own
    font sizes, as ``Text(font_size=10)`` beside a 10 point label.
    """
    modules: dict[PurePosixPath, _Module] = {}
    for path in project_files(request.project, exclude=("__pycache__",)):
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(request.project.root.joinpath(*path.parts).read_bytes())
        except SyntaxError:
            tree = ast.Module([], [])
        modules[path] = _module(path, tree)[0]
    sizes: dict[PurePosixPath, dict[str, Size]] = {}
    for render in request.inspection.renders:
        placed: dict[str, Size] = {}
        for module in _reached(render.source, modules):
            for target, height in module.heights.items():
                # Size bounds its lengths, and an output beyond them draws at
                # the notebook's own size.
                with suppress(ValueError):
                    placed.setdefault(target, Size(height=height * _POINTS_PER_UNIT))
        if placed:
            sizes[render.source] = placed
    return sizes


def _failure(error: RenderFailure, hint: str) -> ProviderError:
    source = None
    if error.path:
        source = SourceLocation(project_path(error.path), error.line, 1)
    return ProviderError(
        error.message, source=source, code="manim-render-failed", hint=hint
    )


def _write_reads(
    root: Path, kind: str, reads: Mapping[str, Representation]
) -> dict[str, str]:
    """Write each read image beneath ``root`` and return its path by target."""
    folder = root.joinpath(*_READS.parts, kind)
    folder.mkdir(parents=True, exist_ok=True)
    files = {}
    for index, (target, image) in enumerate(sorted(reads.items())):
        file = folder / f"{index}{_IMAGES[image.media_type]}"
        file.write_bytes(image.data)
        files[target] = str(file)
    return files


class ManimProvider:
    info = ProviderInfo(
        title="Manim",
        summary="Renders ManimGL scenes from notebook results beside a page.",
        options=frozenset({"quality"}),
    )

    def availability(self) -> ProviderAvailability:
        # The worker renders with its own manim-marimo, which reads the jobs
        # this provider writes, so both come from one release.
        provider = version("manim-marimo")
        found = probe_tool(
            [*worker(), "--version"],
            minimum="0",
            install=_INSTALL,
        )
        if found.available and found.version != provider:
            return ProviderAvailability(
                False,
                version=found.version,
                reason=f"Scenes render with manim-marimo {found.version}, "
                f"and Studio runs manim-marimo {provider}.",
                action="Install one manim-marimo release in the notebook's "
                "environment and where Studio runs.",
            )
        return found

    def starters(self) -> tuple[ProviderStarter, ...]:
        return tuple(starter.info for starter in _STARTERS)

    def create(self, starter: ProviderStarter, context: StarterContext) -> StarterPlan:
        return create_starter(_STARTERS, starter, context)

    def inspect(self, request: InspectionRequest) -> ProjectInspection:
        project = request.project
        files = project_files(project, exclude=("__pycache__",))
        documents = tuple(
            SourceDocument(path, _LANGUAGES[path.suffix], "edit")
            for path in files
            if path.suffix in _LANGUAGES
        )
        inputs = tuple(BuildInput(path, "file") for path in files)
        diagnostics: list[ProjectDiagnostic] = []
        sites = ()
        hosts = _RenderHosts()
        modules: dict[PurePosixPath, _Module] = {}
        for path in files:
            request.cancellation.raise_if_cancelled("Manim inspection")
            source = project.root.joinpath(*path.parts).read_bytes()
            if path == _PAGE:
                sites, problems = html_sites(path, source)
                diagnostics.extend(problems)
                hosts.feed(source.decode("utf-8", errors="replace"))
            elif path.suffix == ".py":
                try:
                    tree = ast.parse(source, filename=path.as_posix())
                except SyntaxError as error:
                    diagnostics.append(
                        ProjectDiagnostic(
                            "manim-source-invalid",
                            "error",
                            error.msg,
                            source=SourceLocation(
                                path, error.lineno or 1, error.offset or 1
                            ),
                        )
                    )
                    modules[path] = _Module()
                    continue
                modules[path], problems = _module(path, tree)
                diagnostics.extend(problems)
        if _PAGE not in files:
            diagnostics.append(
                ProjectDiagnostic(
                    "manim-input-missing",
                    "error",
                    f"{_PAGE} is missing.",
                    "Restore the page that shows the scenes.",
                )
            )
        renders: dict[PurePosixPath, Render] = {}
        for render, location in hosts.hosts:
            scene = PurePosixPath(render)
            if scene.suffix != ".py" or scene in renders:
                continue
            if scene in modules:
                renders[scene] = _render(scene, modules)
            else:
                diagnostics.append(
                    ProjectDiagnostic(
                        "manim-scene-missing",
                        "error",
                        f"The page shows the scene {render}, which is missing.",
                        "Create the scene file or show another one.",
                        location,
                    )
                )
        return ProjectInspection(
            documents,
            inputs,
            sites=sites,
            diagnostics=tuple(diagnostics),
            renders=tuple(renders.values()),
        )

    def build(self, request: BuildRequest) -> BuildResult:
        video = _video(request.project, request.profile)
        copy_inputs(request, request.staging_root, include=_is_page_file)
        copy_inputs(
            request, request.template_root, include=lambda path: not _is_page_file(path)
        )
        file = request.template_root.joinpath(*_VIDEO.parts)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(asdict(video)), encoding="utf-8")
        for index, render in enumerate(request.inspection.renders):
            work = request.work_root / f"check-{index}"
            job = SceneJob(
                str(request.template_root),
                render.source.as_posix(),
                video,
                str(work),
                str(work / "output"),
                check=True,
            )
            try:
                run_scene(job, request.runner, request.command_timeout)
            except RenderFailure as error:
                raise _failure(
                    error, "Fix the scene so it renders with every read at its default."
                ) from error
        return BuildResult(_PAGE, output_sizes=_output_sizes(request))

    def render(self, request: RenderRequest) -> RenderResult:
        root = request.template_root
        video = VideoFormat(
            **json.loads(root.joinpath(*_VIDEO.parts).read_text(encoding="utf-8"))
        )
        values = root.joinpath(*_READS.parts, "values.json")
        values.parent.mkdir(parents=True, exist_ok=True)
        values.write_text(json.dumps(dict(request.values)), encoding="utf-8")
        job = SceneJob(
            str(root),
            request.source.as_posix(),
            video,
            str(root / ".manim-marimo" / "work"),
            str(request.output_root),
            values=str(values),
            outputs=_write_reads(root, "outputs", request.outputs),
            cells=_write_reads(root, "cells", request.cells),
        )
        try:
            run_scene(job, request.runner, request.command_timeout)
        except RenderFailure as error:
            raise _failure(
                error, "Fix the scene, then save it to render again."
            ) from error
        return RenderResult(
            (
                RenderFile(_MOVIE, "video/mp4"),
                RenderFile(_POSTER, "image/png"),
                RenderFile(_METADATA, "application/json"),
            ),
            main=_MOVIE,
            preview=_POSTER,
            regions=_regions(Path(job.work, "lineage.json"), video.fps),
        )


def _region(
    record: dict[str, Any], file: PurePosixPath, fps: int, *, timed: bool
) -> RenderRegion:
    x, y, width, height = record["box"]
    source = record["source"]
    start, end = record.get("start"), record.get("end")
    return RenderRegion(
        file,
        Rect(x, y, width, height),
        reads=tuple(record["reads"]),
        source=SourceLocation(
            PurePosixPath(source["path"]), source["line"], source["column"]
        ),
        label=str(record["label"]),
        start=start / fps if timed and isinstance(start, int) else None,
        end=end / fps if timed and isinstance(end, int) else None,
    )


def _regions(lineage: Path, fps: int) -> tuple[RenderRegion, ...]:
    """Return the traced shapes as regions of the movie and of its poster.

    The worker writes ``lineage.json`` beside its report, with frame ranges
    for the movie and the shapes of the last frame, which the poster shows.
    """
    # Regions are evidence beside the movie, so unreadable lineage leaves them
    # out and the render publishes.
    try:
        records = json.loads(lineage.read_text(encoding="utf-8"))
        return (
            *(_region(item, _MOVIE, fps, timed=True) for item in records["regions"]),
            *(_region(item, _POSTER, fps, timed=False) for item in records["last"]),
        )
    except (OSError, ValueError, KeyError, TypeError):
        return ()


provider = ManimProvider()
