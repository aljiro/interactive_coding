"""Prediction CSV adapter: the server never executes student code for this type.

Format (header required, column order free, extra columns ignored)::

    dataset,id,probability
    test,0,0.021
    grid,0,0.001
"""

from __future__ import annotations

import csv
import io
import math
from pathlib import Path

import numpy as np

from app.core.submission_adapter import (
    AdapterContext,
    PredictionSet,
    SubmissionAdapter,
    SubmissionError,
)

MAX_REPORTED = 15
REQUIRED_COLUMNS = ("dataset", "id", "probability")


class PredictionCsvAdapter(SubmissionAdapter):
    id = "prediction_csv"
    label = "Prediction CSV"
    accepted_extensions = (".csv",)
    description = (
        "A CSV file with columns dataset,id,probability containing one row for every id of "
        "every required dataset. probability is the predicted probability of class 1."
    )

    def run(self, artifact: Path, ctx: AdapterContext) -> PredictionSet:
        try:
            text = artifact.read_bytes().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise SubmissionError("File is not valid UTF-8 text.", [str(exc)]) from None
        return parse_prediction_csv(text, ctx)


def parse_prediction_csv(text: str, ctx: AdapterContext) -> PredictionSet:
    reader = csv.reader(io.StringIO(text.lstrip("\ufeff")))
    try:
        header = next(reader)
    except StopIteration:
        raise SubmissionError("The CSV file is empty.") from None
    columns = [h.strip().lower() for h in header]
    missing = [c for c in REQUIRED_COLUMNS if c not in columns]
    if missing:
        raise SubmissionError(
            "CSV header is missing required column(s): " + ", ".join(missing),
            [f"Found columns: {', '.join(columns) or '(none)'}"],
        )
    idx = {c: columns.index(c) for c in REQUIRED_COLUMNS}

    expected: dict[str, dict[int, int]] = {
        name: {int(i): pos for pos, i in enumerate(ds.ids)} for name, ds in ctx.inputs.items()
    }
    values: dict[str, np.ndarray] = {
        name: np.full(ds.n, np.nan, dtype=np.float64) for name, ds in ctx.inputs.items()
    }
    seen: dict[str, np.ndarray] = {
        name: np.zeros(ds.n, dtype=bool) for name, ds in ctx.inputs.items()
    }

    errors: list[str] = []

    def err(line: int, msg: str) -> None:
        if len(errors) < MAX_REPORTED:
            errors.append(f"line {line}: {msg}")
        elif len(errors) == MAX_REPORTED:
            errors.append("... further problems omitted")

    n_rows = 0
    for line_no, row in enumerate(reader, start=2):
        if not row or all(not c.strip() for c in row):
            continue
        n_rows += 1
        if len(row) < len(columns):
            err(line_no, f"expected {len(columns)} columns, found {len(row)}")
            continue
        dataset = row[idx["dataset"]].strip().lower()
        if dataset not in expected:
            err(line_no, f"unknown dataset '{dataset}' (expected one of {', '.join(expected)})")
            continue
        try:
            row_id = int(row[idx["id"]].strip())
        except ValueError:
            err(line_no, f"id '{row[idx['id']]}' is not an integer")
            continue
        pos = expected[dataset].get(row_id)
        if pos is None:
            err(line_no, f"unknown id {row_id} for dataset '{dataset}'")
            continue
        if seen[dataset][pos]:
            err(line_no, f"duplicate id {row_id} for dataset '{dataset}'")
            continue
        raw = row[idx["probability"]].strip()
        try:
            p = float(raw)
        except ValueError:
            err(line_no, f"probability '{raw}' is not a number")
            continue
        if math.isnan(p) or math.isinf(p):
            err(line_no, f"probability must be finite, got {raw}")
            continue
        if p < 0.0 or p > 1.0:
            err(line_no, f"probability {p} is outside [0, 1]")
            continue
        values[dataset][pos] = p
        seen[dataset][pos] = True

    if n_rows == 0:
        raise SubmissionError("The CSV file contains a header but no data rows.")

    for name, ds in ctx.inputs.items():
        n_missing = int((~seen[name]).sum())
        if n_missing:
            first = [str(int(ds.ids[i])) for i in np.flatnonzero(~seen[name])[:10]]
            errors.append(
                f"dataset '{name}': {n_missing} of {ds.n} ids are missing "
                f"(e.g. {', '.join(first)}{', ...' if n_missing > 10 else ''})"
            )

    if errors:
        raise SubmissionError("Prediction CSV failed validation.", errors)

    return PredictionSet(values, info={"rows": n_rows, "source": "prediction_csv"})
