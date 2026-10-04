"""The CSVs committed under examples/data/ must match the generated challenge data exactly."""

from pathlib import Path

import pytest

from app.scripts.export_public_data import DEFAULT_OUT, PUBLIC_FILES


@pytest.mark.skipif(
    not DEFAULT_OUT.exists(), reason="examples/data not present (not in repo checkout)"
)
@pytest.mark.parametrize("name", list(PUBLIC_FILES))
def test_committed_public_file_matches_generated(name: str):
    committed = (DEFAULT_OUT / name).read_bytes()
    assert committed == PUBLIC_FILES[name](), (
        f"{name} is out of date: run `python -m app.scripts.export_public_data`"
    )


def test_no_labels_in_public_dir():
    for path in Path(DEFAULT_OUT).glob("*"):
        assert "label" not in path.name.lower()
        header = path.read_text().splitlines()[0]
        if path.name != "train.csv":
            assert "label" not in header
