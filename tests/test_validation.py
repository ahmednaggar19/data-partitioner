from __future__ import annotations

import pytest

from data_partitioner import FileFormat, rebalance
from tests.helpers import make_frame


def test_rebalance_requires_exactly_one_sizing_mode() -> None:
    with pytest.raises(ValueError, match="Provide either"):
        rebalance("in", "out")

    with pytest.raises(ValueError, match="Provide only one"):
        rebalance(
            "in",
            "out",
            target_rows_per_file=10,
            num_output_files=2,
        )


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"target_rows_per_file": 0}, "target_rows_per_file must be > 0"),
        ({"target_rows_per_file": -1}, "target_rows_per_file must be > 0"),
        ({"num_output_files": 0}, "num_output_files must be > 0"),
    ],
)
def test_rebalance_rejects_invalid_sizing(kwargs: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        rebalance("in", "out", input_formats=[FileFormat.CSV], **kwargs)


def test_rebalance_raises_when_no_matching_files(tmp_path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    with pytest.raises(ValueError, match="No matching input files"):
        rebalance(
            input_path=empty,
            output_dir=tmp_path / "out",
            input_formats=[FileFormat.CSV],
            target_rows_per_file=10,
        )


def test_rebalance_raises_on_zero_rows(tmp_path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    make_frame(0).to_csv(source / "empty.csv", index=False)

    with pytest.raises(ValueError, match="zero rows"):
        rebalance(
            input_path=source,
            output_dir=output,
            input_formats=[FileFormat.CSV],
            target_rows_per_file=10,
        )


def test_rebalance_rejects_empty_input_formats() -> None:
    with pytest.raises(ValueError, match="input_formats cannot be empty"):
        rebalance(
            "in",
            "out",
            input_formats=[],
            target_rows_per_file=10,
        )


def test_rebalance_raises_on_unsupported_extension(tmp_path) -> None:
    path = tmp_path / "data.avro"
    path.write_text("not supported")

    with pytest.raises(ValueError, match="Unsupported file extension"):
        rebalance(
            input_path=path,
            output_dir=tmp_path / "out",
            input_formats=[FileFormat.CSV],
            target_rows_per_file=10,
        )
