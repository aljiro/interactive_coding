"""Write the *public* Moons files into examples/data/ so Colab can fetch them from GitHub.

    python -m app.scripts.export_public_data [--out ../examples/data]

Only resources that every student may download are exported. Hidden labels are never written.
``tests/test_public_data.py`` checks that the committed files match the generated data.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.challenges.moons import data

PUBLIC_FILES = {
    "train.csv": data.train_csv,
    "test_features.csv": data.test_features_csv,
    "visualization_grid.csv": data.grid_csv,
    "sample_predictions.csv": data.sample_predictions_csv,
}

DEFAULT_OUT = Path(__file__).resolve().parents[3] / "examples" / "data"


def export(out: Path = DEFAULT_OUT) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, loader in PUBLIC_FILES.items():
        path = out / name
        path.write_bytes(loader())
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    for path in export(args.out):
        print(f"wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
