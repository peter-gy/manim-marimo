"""Run one scene in an owned worker process."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from marimo_studio.view_providers import ProviderRunner


@dataclass(frozen=True)
class VideoFormat:
    """The video format a view renders, fixed by its build."""

    width: int
    height: int
    fps: int


@dataclass(frozen=True)
class SceneJob:
    """One worker run of the scene file ``scene`` beneath ``root``.

    A check constructs the scene with every read at its default and skips
    encoding. A render writes ``animation.mp4``, ``poster.png``, and
    ``metadata.json`` to ``output``. ``values`` names a JSON file, and
    ``outputs`` and ``cells`` map targets to image files.
    """

    root: str
    scene: str
    video: VideoFormat
    work: str
    output: str
    check: bool = False
    values: str | None = None
    outputs: dict[str, str] = field(default_factory=dict)
    cells: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RenderFailure(Exception):
    message: str
    path: str | None = None
    line: int = 1


def run_scene(job: SceneJob, runner: ProviderRunner, timeout: float) -> None:
    """Run ``job`` and raise ``RenderFailure`` at the first scene error."""
    work = Path(job.work)
    work.mkdir(parents=True, exist_ok=True)
    report = work / "report.json"
    file = work / "job.json"
    file.write_text(json.dumps(asdict(job)), encoding="utf-8")
    completed = runner.run(
        [sys.executable, "-I", "-m", "marimo_manim._worker", str(file)],
        cwd=Path(job.root),
        timeout=timeout,
    )
    if not report.is_file():
        raise RenderFailure(
            "Manim stopped before producing a render report. "
            + completed.stderr.strip()[-2000:]
        )
    record = json.loads(report.read_text(encoding="utf-8"))
    if "error" in record:
        raise RenderFailure(record["error"], record.get("path"), record.get("line", 1))
    if completed.returncode != 0:
        raise RenderFailure(
            completed.stderr.strip()[-2000:] or "Manim rendering failed."
        )
