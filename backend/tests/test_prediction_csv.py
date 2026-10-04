import numpy as np
import pytest

from app.core import SubmissionError
from app.submissions.prediction_csv import parse_prediction_csv
from tests.conftest import make_csv


def test_valid_csv(moons_ctx):
    probs = {n: np.random.default_rng(0).random(ds.n) for n, ds in moons_ctx.inputs.items()}
    result = parse_prediction_csv(make_csv(moons_ctx, probs), moons_ctx)
    for n in moons_ctx.inputs:
        np.testing.assert_allclose(result[n], probs[n], atol=1e-12)
    assert result.info["rows"] == sum(ds.n for ds in moons_ctx.inputs.values())


def test_bom_and_column_order(moons_ctx):
    text = make_csv(moons_ctx)
    lines = text.splitlines()
    swapped = ["﻿probability,dataset,id"] + [
        ",".join(line.split(",")[::-1][:1] + line.split(",")[:2]) for line in lines[1:]
    ]
    # reorder: probability,dataset,id
    swapped = ["﻿probability,dataset,id"]
    for line in lines[1:]:
        d, i, p = line.split(",")
        swapped.append(f"{p},{d},{i}")
    result = parse_prediction_csv("\n".join(swapped), moons_ctx)
    assert result["test"].shape == (1000,)


def test_missing_rows(moons_ctx):
    text = make_csv(moons_ctx)
    lines = text.splitlines()
    text = "\n".join(lines[:-5])  # drop five grid rows
    with pytest.raises(SubmissionError) as exc:
        parse_prediction_csv(text, moons_ctx)
    assert any("5 of 10000 ids are missing" in d for d in exc.value.details)


def test_duplicate_ids(moons_ctx):
    text = make_csv(moons_ctx) + "test,0,0.9\n"
    with pytest.raises(SubmissionError) as exc:
        parse_prediction_csv(text, moons_ctx)
    assert any("duplicate id 0" in d for d in exc.value.details)


def test_unknown_id_and_dataset(moons_ctx):
    text = make_csv(moons_ctx) + "test,999999,0.1\nvalidation,0,0.1\n"
    with pytest.raises(SubmissionError) as exc:
        parse_prediction_csv(text, moons_ctx)
    details = " ".join(exc.value.details)
    assert "unknown id 999999" in details and "unknown dataset 'validation'" in details


@pytest.mark.parametrize("bad", ["1.5", "-0.1", "nan", "inf", "-inf", "abc"])
def test_invalid_probabilities(moons_ctx, bad):
    text = make_csv(moons_ctx).replace("test,0,0.5", f"test,0,{bad}", 1)
    with pytest.raises(SubmissionError) as exc:
        parse_prediction_csv(text, moons_ctx)
    assert any("line 2" in d for d in exc.value.details)


def test_missing_columns(moons_ctx):
    with pytest.raises(SubmissionError) as exc:
        parse_prediction_csv("dataset,id,prob\ntest,0,0.5\n", moons_ctx)
    assert "probability" in exc.value.message


def test_empty_file(moons_ctx):
    with pytest.raises(SubmissionError):
        parse_prediction_csv("", moons_ctx)
    with pytest.raises(SubmissionError):
        parse_prediction_csv("dataset,id,probability\n", moons_ctx)
