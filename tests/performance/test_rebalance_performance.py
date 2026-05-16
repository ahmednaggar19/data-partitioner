from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_partitioner import FileFormat
from tests.performance.metrics import RebalancePerformanceMetrics, measure_rebalance


@pytest.mark.performance
def test_csv_rebalance_performance_metrics(
    tmp_path: Path,
    uneven_csv_dataset: tuple[Path, int],
    performance_report: list[dict[str, object]],
) -> None:
    source, expected_rows = uneven_csv_dataset
    output = tmp_path / "perf_output_csv"

    result, metrics = measure_rebalance(
        input_path=source,
        output_dir=output,
        input_formats=[FileFormat.CSV],
        output_format=FileFormat.CSV,
        target_rows_per_file=10_000,
    )

    assert result.total_rows == expected_rows
    _assert_reasonable_metrics(metrics)
    performance_report.append(
        {
            "test": "csv_target_rows",
            **metrics.as_dict(),
        }
    )


@pytest.mark.performance
def test_parquet_rebalance_performance_metrics(
    tmp_path: Path,
    uneven_parquet_dataset: tuple[Path, int],
    performance_report: list[dict[str, object]],
) -> None:
    source, expected_rows = uneven_parquet_dataset
    output = tmp_path / "perf_output_parquet"

    result, metrics = measure_rebalance(
        input_path=source,
        output_dir=output,
        input_formats=[FileFormat.PARQUET],
        num_output_files=8,
    )

    assert result.total_rows == expected_rows
    _assert_reasonable_metrics(metrics)
    performance_report.append(
        {
            "test": "parquet_num_output_files",
            **metrics.as_dict(),
        }
    )


@pytest.mark.performance
def test_rebalance_writes_performance_report_json(
    tmp_path: Path,
    uneven_csv_dataset: tuple[Path, int],
) -> None:
    source, _ = uneven_csv_dataset
    output = tmp_path / "perf_output_report"
    report_path = tmp_path / "rebalance_performance.json"

    _, metrics = measure_rebalance(
        input_path=source,
        output_dir=output,
        input_formats=[FileFormat.CSV],
        target_rows_per_file=10_000,
    )

    report_path.write_text(metrics.to_json(), encoding="utf-8")
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert payload["elapsed_seconds"] > 0
    assert payload["peak_traced_memory_bytes"] > 0
    assert payload["input_disk_bytes"] > 0
    assert payload["output_disk_bytes"] > 0


def _assert_reasonable_metrics(metrics: RebalancePerformanceMetrics) -> None:
    assert metrics.elapsed_seconds > 0
    assert metrics.peak_traced_memory_bytes > 0
    assert metrics.input_disk_bytes > 0
    assert metrics.output_disk_bytes > 0
    assert metrics.total_rows > 0
    assert metrics.input_files > 0
    assert metrics.output_files > 0
