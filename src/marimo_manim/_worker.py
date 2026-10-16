"""Run Manim in a fresh process, with notebook results bound to scene construction."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from marimo_manim._reads import SceneReads, scene_reads


def _scene_type(module: Any, scene: type) -> type:
    """Return the one Scene subclass ``module`` defines that no other extends."""
    defined = [
        item
        for item in vars(module).values()
        if isinstance(item, type)
        and issubclass(item, scene)
        and item.__module__ == module.__name__
    ]
    leaves = [
        item
        for item in defined
        if not any(other is not item and issubclass(other, item) for other in defined)
    ]
    if len(leaves) != 1:
        found = ", ".join(sorted(item.__name__ for item in leaves)) or "none"
        raise ValueError(
            "A scene file defines one manimlib.Scene subclass to render. "
            f"Found {found}."
        )
    return leaves[0]


def _use_headless_opengl() -> None:
    """Open OpenGL contexts through EGL on Linux machines without a display.

    ManimGL asks moderngl for an X11 context on Linux. Mesa's EGL renders the
    same scenes in software with no window system, as on servers and CI.
    """
    if not sys.platform.startswith("linux") or os.environ.get("DISPLAY"):
        return
    import moderngl

    # moderngl's stub types each keyword argument as a dict, so the original
    # function and its replacement pass through Any.
    create = cast("Callable[..., moderngl.Context]", moderngl.create_standalone_context)

    def create_with_egl(**settings: Any) -> moderngl.Context:
        return create(**settings, backend="egl")

    moderngl.create_standalone_context = cast(Any, create_with_egl)


def _encoder_closed(scene: Any) -> None:
    # Scene.run skips teardown after an arbitrary construct() error. Close its
    # encoder before the supervisor releases the worker.
    encoder = scene.file_writer.writing_process
    if encoder is not None and encoder.poll() is None:
        if encoder.stdin is not None:
            encoder.stdin.close()
        try:
            encoder.wait(timeout=3)
        except subprocess.TimeoutExpired:
            encoder.kill()
            encoder.wait()


def _run(job: dict[str, Any]) -> None:
    import yaml

    root = Path(job["root"])
    work = Path(job["work"])
    output = Path(job["output"])
    video = job["video"]
    cache = work / "manim-cache"
    cache.mkdir(parents=True, exist_ok=True)
    config = work / "manim.yml"
    config.write_text(
        yaml.safe_dump(
            {
                "directories": {"cache": str(cache), "temporary_storage": str(cache)},
                "camera": {"background_color": "#11161c"},
                "text": {"font": "Arial"},
            }
        ),
        encoding="utf-8",
    )
    # Manim parses process arguments during import. Its configuration belongs
    # to this worker, independently of Studio's command line.
    sys.argv = ["manim", "--config_file", str(config)]
    sys.dont_write_bytecode = True
    import imageio_ffmpeg
    from manimlib import Scene

    _use_headless_opengl()

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    reads = SceneReads(
        json.loads(Path(job["values"]).read_text(encoding="utf-8"))
        if job["values"]
        else {},
        {target: Path(path) for target, path in job["outputs"].items()},
        {target: Path(path) for target, path in job["cells"].items()},
    )
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("_studio_scene", root / job["scene"])
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot import {job['scene']}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    with scene_reads(reads):
        spec.loader.exec_module(module)
        scene_type = _scene_type(module, Scene)
        scene = scene_type(
            skip_animations=job["check"],
            camera_config={
                "resolution": (video["width"], video["height"]),
                "fps": video["fps"],
            },
            file_writer_config={
                "write_to_movie": not job["check"],
                "save_last_frame": not job["check"],
                "output_directory": str(output),
                "file_name": "animation",
                "ffmpeg_bin": ffmpeg,
                "quiet": True,
            },
        )
        try:
            scene.run()
        finally:
            _encoder_closed(scene)
    encoder = scene.file_writer.writing_process
    if not job["check"] and (encoder is None or encoder.returncode != 0):
        status = encoder.returncode if encoder is not None else "not started"
        raise ValueError(f"The video encoder failed with status {status}.")
    if scene.num_plays == 0:
        raise ValueError("The scene contains no frames. Add a play() or wait() call.")
    if job["check"]:
        return
    movie = output / "animation.mp4"
    ready = output / "ready.mp4"
    completed = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-xerror",
            "-i",
            str(movie),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            "-y",
            str(ready),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode:
        raise ValueError(
            f"FFmpeg could not finalize the video: {completed.stderr[-2000:]}"
        )
    ready.replace(movie)
    (output / "animation.png").replace(output / "poster.png")
    (output / "metadata.json").write_text(
        json.dumps(
            {
                "duration": scene.time,
                "fps": video["fps"],
                "width": video["width"],
                "height": video["height"],
            }
        ),
        encoding="utf-8",
    )


def main() -> int:
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root = Path(job["root"]).resolve()
    report = Path(job["work"], "report.json")
    try:
        _run(job)
    except Exception as error:
        frames = traceback.extract_tb(error.__traceback__)
        if isinstance(error, SyntaxError) and error.filename:
            frames.append(traceback.FrameSummary(error.filename, error.lineno or 1, ""))
        # Errors outside authored code, such as a missing scene class, belong
        # to the scene file.
        location: dict[str, object] = {"path": job["scene"], "line": 1}
        for frame in frames:
            try:
                relative = Path(frame.filename).resolve().relative_to(root)
            except ValueError:
                continue
            location = {"path": relative.as_posix(), "line": frame.lineno}
        report.write_text(
            json.dumps({"error": f"{type(error).__name__}: {error}", **location}),
            encoding="utf-8",
        )
        return 1
    report.write_text("{}", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
