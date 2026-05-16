from __future__ import annotations

import pandas as pd
import pytest

from data_partitioner import FileFormat, rebalance
from tests.helpers import make_frame


def test_rebalance_single_input_file(tmp_path) -> None:
    source = tmp_path / "single.csv"
    output = tmp_path / "balanced"
    make_frame(6).to_csv(source, index=False)

    result = rebalance(
        input_path=source,
        output_dir=output,
        input_formats=[FileFormat.CSV],
        target_rows_per_file=4,
    )

    assert result.input_files == 1
    assert result.output_rows_per_file == [4, 2]


def test_rebalance_preserves_row_values_and_order(tmp_path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "balanced"
    source.mkdir()
    make_frame(3, start=0).to_csv(source / "a.csv", index=False)
    make_frame(2, start=3).to_csv(source / "b.csv", index=False)

    rebalance(
        input_path=source,
        output_dir=output,
        input_formats=[FileFormat.CSV],
        target_rows_per_file=10,
    )

    combined = pd.concat(
        [pd.read_csv(path) for path in sorted(output.glob("*.csv"))],
        ignore_index=True,
    )
    expected = pd.concat(
        [pd.read_csv(source / "a.csv"), pd.read_csv(source / "b.csv")],
        ignore_index=True,
    )
    pd.testing.assert_frame_equal(combined, expected)


def test_rebalance_infers_output_format_from_first_input(tmp_path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "balanced"
    source.mkdir()
    make_frame(2).to_parquet(source / "first.parquet", index=False)

    result = rebalance(
        input_path=source,
        output_dir=output,
        input_formats=[FileFormat.PARQUET],
        target_rows_per_file=2,
    )

    assert result.output_format == FileFormat.PARQUET
    assert list(output.glob("*.parquet"))


def test_rebalance_custom_output_prefix(tmp_path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "balanced"
    source.mkdir()
    make_frame(2).to_csv(source / "data.csv", index=False)

    rebalance(
        input_path=source,
        output_dir=output,
        input_formats=[FileFormat.CSV],
        target_rows_per_file=1,
        output_prefix="shard",
    )

    names = sorted(p.name for p in output.glob("shard-*.csv"))
    assert names == ["shard-00001.csv", "shard-00002.csv"]


def test_rebalance_csv_to_parquet_format_change(tmp_path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "balanced"
    source.mkdir()
    make_frame(3).to_csv(source / "data.csv", index=False)

    result = rebalance(
        input_path=source,
        output_dir=output,
        input_formats=[FileFormat.CSV],
        output_format=FileFormat.PARQUET,
        target_rows_per_file=2,
    )

    assert result.output_format == FileFormat.PARQUET
    assert result.output_rows_per_file == [2, 1]
    assert len(list(output.glob("*.parquet"))) == 2


@pytest.mark.skipif(
    not hasattr(pd.DataFrame(), "to_orc"),
    reason="ORC write support unavailable in this pandas build",
)
def test_rebalance_orc_round_trip(tmp_path) -> None:
    if not hasattr(pd, "read_orc"):
        pytest.skip("ORC read support unavailable in this pandas build")

    source = tmp_path / "source"
    output = tmp_path / "balanced"
    source.mkdir()
    make_frame(5).to_orc(source / "data.orc", index=False)

    result = rebalance(
        input_path=source,
        output_dir=output,
        input_formats=[FileFormat.ORC],
        output_format=FileFormat.ORC,
        num_output_files=2,
    )

    assert result.total_rows == 5
    assert result.output_format == FileFormat.ORC
    assert len(list(output.glob("*.orc"))) == 2
