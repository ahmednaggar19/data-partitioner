from __future__ import annotations

from data_partitioner import FileFormat, RebalanceResult


def test_rebalance_result_as_dict() -> None:
    result = RebalanceResult(
        input_files=2,
        total_rows=10,
        output_files=3,
        target_rows_per_file=4,
        input_rows_per_file=[3, 7],
        output_rows_per_file=[4, 4, 2],
        output_format=FileFormat.CSV,
        output_paths=["/tmp/part-00001.csv"],
    )

    payload = result.as_dict()
    assert payload == {
        "input_files": 2,
        "total_rows": 10,
        "output_files": 3,
        "target_rows_per_file": 4,
        "input_rows_per_file": [3, 7],
        "output_rows_per_file": [4, 4, 2],
        "output_format": "csv",
        "output_paths": ["/tmp/part-00001.csv"],
    }
