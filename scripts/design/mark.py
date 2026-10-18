"""Print manim-marimo's mark as the Fourier example computes it.

The mark is the example's default path. Its rotating vectors are the Fourier
terms whose length is above rounding, as [frequency, real, imaginary] rows in
the order the example's scene chains them.
"""

import importlib.util
import json
import sys
from pathlib import Path

notebook = Path(__file__).resolve().parents[2] / "examples/fourier.py"
spec = importlib.util.spec_from_file_location("fourier", notebook)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
_, defs = module.app.run()
if defs["path"].value != "manim-marimo mark":
    sys.exit(f"{notebook} must default to the manim-marimo mark.")
terms = [
    [int(frequency), float(real), float(imaginary)]
    for frequency, real, imaginary in defs["terms"]
    if abs(complex(real, imaginary)) > 1e-9
]
json.dump(terms, sys.stdout)
