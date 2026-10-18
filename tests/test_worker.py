import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from marimo_studio.view_providers import ProviderCommandResult
from PIL import Image

from manim_marimo._render import RenderFailure, SceneJob, VideoFormat, run_scene

pytestmark = pytest.mark.render


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


def run(
    root: Path,
    source: str,
    *,
    check: bool = False,
    values: str | None = None,
    outputs: dict[str, str] | None = None,
) -> Path:
    template = root / "template"
    template.mkdir()
    (template / "scene.py").write_text(source)
    output = root / "output"
    run_scene(
        SceneJob(
            str(template),
            "scene.py",
            VideoFormat(320, 180, 15),
            str(root / "work"),
            str(output),
            check=check,
            values=values,
            outputs=outputs or {},
        ),
        Runner(),
        60,
    )
    return output


def test_scene_reads_render_values_and_uses_owned_cache(tmp_path: Path):
    (tmp_path / "values.json").write_text('{"total": 17}')
    output = run(
        tmp_path,
        f"""
from pathlib import Path
from manimlib import Circle, Scene
from manimlib.utils.cache import _cache
from manim_marimo import value
assert Path(_cache.directory) == Path({str(tmp_path / "work" / "manim-cache")!r})
class Animation(Scene):
    def construct(self):
        assert value("total") == 17
        self.add(Circle())
        self.wait(0.2)
""",
        values=str(tmp_path / "values.json"),
    )
    assert json.loads((output / "metadata.json").read_text())["duration"] > 0
    assert sorted(path.name for path in (tmp_path / "template").iterdir()) == [
        "scene.py"
    ]


def test_scene_places_a_notebook_figure(tmp_path: Path):
    Image.new("RGB", (64, 36), (255, 0, 0)).save(tmp_path / "figure.png")
    output = run(
        tmp_path,
        """
from manimlib import FRAME_HEIGHT, Scene
from manim_marimo import output
class Animation(Scene):
    def construct(self):
        self.add(output("figure", height=FRAME_HEIGHT))
        self.wait(0.1)
""",
        outputs={"figure": str(tmp_path / "figure.png")},
    )
    with Image.open(output / "poster.png") as poster:
        assert poster.convert("RGB").getpixel((160, 90)) == (255, 0, 0)


def test_check_constructs_the_scene_at_its_defaults_without_encoding(tmp_path: Path):
    output = run(
        tmp_path,
        """
from manimlib import Circle, Scene
from manim_marimo import output, value
class Animation(Scene):
    def construct(self):
        assert value("radius", default=1) == 1 and output("figure") is None
        self.play(Circle().animate.shift([1, 0, 0]), run_time=30)
""",
        check=True,
    )
    assert not output.exists() or not any(output.iterdir())


def test_scene_failure_reports_authored_location(tmp_path: Path):
    with pytest.raises(RenderFailure) as failure:
        run(
            tmp_path,
            """from manimlib import Scene
class Animation(Scene):
    def construct(self):
        self.wait(0.1)
        raise ValueError("invalid trajectory")
""",
        )
    assert failure.value == RenderFailure(
        "ValueError: invalid trajectory", "scene.py", 5
    )


def test_failure_inside_python_import_machinery_reports_the_scene(tmp_path: Path):
    template = tmp_path / "template"
    template.mkdir()
    with pytest.raises(RenderFailure) as failure:
        run_scene(
            SceneJob(
                str(template),
                "scene.py",
                VideoFormat(320, 180, 15),
                str(tmp_path / "work"),
                str(tmp_path / "output"),
                check=True,
            ),
            Runner(),
            60,
        )
    assert (failure.value.path, failure.value.line) == ("scene.py", 1)


def test_scene_file_renders_its_one_leaf_scene(tmp_path: Path):
    output = run(
        tmp_path,
        """
from manimlib import Scene, WHITE
class Styled(Scene):
    default_camera_config = {"background_color": WHITE}
class Drawing(Styled):
    def construct(self):
        self.wait(0.1)
""",
    )
    with Image.open(output / "poster.png") as image:
        assert image.convert("RGB").getpixel((0, 0)) == (255, 255, 255)


def test_scene_file_with_two_scenes_reports_the_file(tmp_path: Path):
    with pytest.raises(RenderFailure) as failure:
        run(
            tmp_path,
            "from manimlib import Scene\n"
            "class One(Scene): ...\n"
            "class Two(Scene): ...\n",
            check=True,
        )
    assert failure.value.path == "scene.py"
    assert "Found One, Two." in failure.value.message


def test_failed_encoder_is_rejected_before_publication(tmp_path: Path):
    with pytest.raises(RenderFailure) as failure:
        run(
            tmp_path,
            """
from types import SimpleNamespace
from manimlib import Scene
class Animation(Scene):
    def run(self):
        self.file_writer.writing_process = SimpleNamespace(poll=lambda: 1, returncode=1)
""",
        )
    assert failure.value.message == (
        "ValueError: The video encoder failed with status 1."
    )
