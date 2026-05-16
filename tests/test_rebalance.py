from __future__ import annotations

import pandas as pd
import pytest

from data_partitioner import FileFormat, rebalance
from tests.helpers import make_frame


def test_rebalance_csv_target_rows(tmp_path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "balanced"
    source.mkdir()

    make_frame(3, start=0).to_csv(source / "part_a.csv", index=False)
    make_frame(7, start=3).to_csv(source / "part_b.csv", index=False)
    (source / "ignore.txt").write_text("not a dataset")

    result = rebalance(
        input_path=source,
        output_dir=output,
        input_formats=[FileFormat.CSV],
        output_format=FileFormat.CSV,
        target_rows_per_file=4,
    )

    assert result.total_rows == 10
    assert result.output_files == 3
    assert result.output_rows_per_file == [4, 4, 2]

    produced = sorted(output.glob("*.csv"))
    assert len(produced) == 3
    assert [len(pd.read_csv(path)) for path in produced] == [4, 4, 2]


def test_rebalance_parquet_with_num_output_files(tmp_path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "balanced"
    source.mkdir()

    make_frame(5, start=0).to_parquet(source / "piece_1.parquet", index=False)
    make_frame(5, start=5).to_parquet(source / "piece_2.parquet", index=False)

    result = rebalance(
        input_path=source,
        output_dir=output,
        input_formats=[FileFormat.PARQUET],
        output_format=FileFormat.PARQUET,
        num_output_files=4,
    )

    assert result.total_rows == 10
    assert result.target_rows_per_file == 3
    assert result.output_files == 4
    assert result.output_rows_per_file == [3, 3, 3, 1]

    produced = sorted(output.glob("*.parquet"))
    assert len(produced) == 4
    assert [len(pd.read_parquet(path)) for path in produced] == [3, 3, 3, 1]


def test_rebalance_raises_on_column_mismatch(tmp_path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "balanced"
    source.mkdir()

    pd.DataFrame({"id": [1, 2], "value": ["a", "b"]}).to_csv(source / "one.csv", index=False)
    pd.DataFrame({"id": [3, 4], "different": ["x", "y"]}).to_csv(source / "two.csv", index=False)

    with pytest.raises(ValueError, match="Column mismatch"):
        rebalance(
            input_path=source,
            output_dir=output,
            input_formats=[FileFormat.CSV],
            output_format=FileFormat.CSV,
            target_rows_per_file=2,
        )
