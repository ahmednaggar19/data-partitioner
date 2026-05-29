from __future__ import annotations

import pandas as pd
import pytest

from data_partitioner import FileFormat, rebalance, rebalance_streaming
from tests.helpers import make_frame


def test_streaming_matches_in_memory_csv(tmp_path) -> None:
    source = tmp_path / "source"
    memory_out = tmp_path / "memory_out"
    stream_out = tmp_path / "stream_out"
    source.mkdir()

    make_frame(3, start=0).to_csv(source / "a.csv", index=False)
    make_frame(7, start=3).to_csv(source / "b.csv", index=False)

    memory_result = rebalance(
        input_path=source,
        output_dir=memory_out,
        input_formats=[FileFormat.CSV],
        output_format=FileFormat.CSV,
        target_rows_per_file=4,
    )
    stream_result = rebalance_streaming(
        input_path=source,
        output_dir=stream_out,
        input_formats=[FileFormat.CSV],
        output_format=FileFormat.CSV,
        target_rows_per_file=4,
        max_memory_mb=64,
    )

    assert stream_result.total_rows == memory_result.total_rows
    assert stream_result.output_rows_per_file == memory_result.output_rows_per_file

    memory_rows = pd.concat(
        [pd.read_csv(path) for path in sorted(memory_out.glob("*.csv"))],
        ignore_index=True,
    )
    stream_rows = pd.concat(
        [pd.read_csv(path) for path in sorted(stream_out.glob("*.csv"))],
        ignore_index=True,
    )
    pd.testing.assert_frame_equal(memory_rows, stream_rows)


def test_streaming_parquet_input(tmp_path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    make_frame(12).to_parquet(source / "data.parquet", index=False)

    result = rebalance_streaming(
        input_path=source,
        output_dir=output,
        input_formats=[FileFormat.PARQUET],
        target_rows_per_file=5,
        max_memory_mb=64,
    )

    assert result.total_rows == 12
    assert result.output_rows_per_file == [5, 5, 2]


def test_streaming_rejects_num_output_files() -> None:
    with pytest.raises(ValueError, match="num_output_files is not supported"):
        rebalance_streaming(
            "in",
            "out",
            target_rows_per_file=100,
            num_output_files=4,
        )


def test_streaming_rejects_invalid_memory_budget() -> None:
    with pytest.raises(ValueError, match="max_memory_mb must be > 0"):
        rebalance_streaming(
            "in",
            "out",
            target_rows_per_file=100,
            max_memory_mb=0,
        )


def test_streaming_raises_on_column_mismatch(tmp_path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    make_frame(2).to_csv(source / "one.csv", index=False)
    pd.DataFrame({"id": [1], "other": ["x"]}).to_csv(source / "two.csv", index=False)

    with pytest.raises(ValueError, match="Column mismatch"):
        rebalance_streaming(
            input_path=source,
            output_dir=output,
            input_formats=[FileFormat.CSV],
            target_rows_per_file=2,
        )
