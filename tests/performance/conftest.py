from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.helpers import make_frame

_COLLECTED_PERFORMANCE_METRICS: list[dict[str, object]] = []


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "performance: resource and timing benchmarks for rebalance (may be slow)",
    )


@pytest.fixture
def perf_scale() -> str:
    return os.environ.get("PERF_SCALE", "small").lower()


@pytest.fixture
def perf_rows_per_file(perf_scale: str) -> int:
    if perf_scale == "large":
        return 200_000
    if perf_scale == "medium":
        return 50_000
    return 5_000


@pytest.fixture
def perf_num_input_files(perf_scale: str) -> int:
    if perf_scale == "large":
        return 20
    if perf_scale == "medium":
        return 10
    return 5


@pytest.fixture
def uneven_csv_dataset(tmp_path, perf_rows_per_file: int, perf_num_input_files: int):
    source = tmp_path / "perf_source_csv"
    source.mkdir()
    row_cursor = 0
    for index in range(perf_num_input_files):
        rows = perf_rows_per_file + (index % 3) * 1_000
        make_frame(rows, start=row_cursor).to_csv(source / f"chunk_{index:03d}.csv", index=False)
        row_cursor += rows
    return source, row_cursor


@pytest.fixture
def uneven_parquet_dataset(tmp_path, perf_rows_per_file: int, perf_num_input_files: int):
    source = tmp_path / "perf_source_parquet"
    source.mkdir()
    row_cursor = 0
    for index in range(perf_num_input_files):
        rows = perf_rows_per_file + (index % 3) * 1_000
        make_frame(rows, start=row_cursor).to_parquet(
            source / f"chunk_{index:03d}.parquet",
            index=False,
        )
        row_cursor += rows
    return source, row_cursor


@pytest.fixture
def performance_report() -> list[dict[str, object]]:
    report: list[dict[str, object]] = []
    yield report
    if report:
        _COLLECTED_PERFORMANCE_METRICS.extend(report)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    del session, exitstatus
    if not _COLLECTED_PERFORMANCE_METRICS:
        return

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "perf_scale": os.environ.get("PERF_SCALE", "small"),
        "benchmarks": _COLLECTED_PERFORMANCE_METRICS,
    }
    (reports_dir / "performance-metrics.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
