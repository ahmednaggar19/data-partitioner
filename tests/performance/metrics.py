from __future__ import annotations

import gc
import json
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Callable, TypeVar

from data_partitioner.core import RebalanceResult

T = TypeVar("T")


def directory_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(
        item.stat().st_size
        for item in path.rglob("*")
        if item.is_file()
    )


@dataclass(frozen=True)
class RebalancePerformanceMetrics:
    elapsed_seconds: float
    peak_traced_memory_bytes: int
    input_disk_bytes: int
    output_disk_bytes: int
    total_rows: int
    input_files: int
    output_files: int
    output_format: str
    target_rows_per_file: int

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["peak_traced_memory_mb"] = round(self.peak_traced_memory_bytes / (1024 * 1024), 3)
        payload["input_disk_mb"] = round(self.input_disk_bytes / (1024 * 1024), 3)
        payload["output_disk_mb"] = round(self.output_disk_bytes / (1024 * 1024), 3)
        return payload

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.as_dict(), indent=indent)


def measure_callable(
    callable_fn: Callable[[], RebalanceResult],
    *,
    input_path: Path,
    output_dir: Path,
) -> tuple[RebalanceResult, RebalancePerformanceMetrics]:
    input_disk_bytes = directory_size_bytes(input_path)

    gc.collect()
    tracemalloc.start()
    started = perf_counter()
    result = callable_fn()
    elapsed_seconds = perf_counter() - started
    _, peak_traced_memory_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    output_disk_bytes = directory_size_bytes(output_dir)
    metrics = RebalancePerformanceMetrics(
        elapsed_seconds=elapsed_seconds,
        peak_traced_memory_bytes=peak_traced_memory_bytes,
        input_disk_bytes=input_disk_bytes,
        output_disk_bytes=output_disk_bytes,
        total_rows=result.total_rows,
        input_files=result.input_files,
        output_files=result.output_files,
        output_format=result.output_format.value,
        target_rows_per_file=result.target_rows_per_file,
    )
    return result, metrics


def measure_rebalance(**rebalance_kwargs: object) -> tuple[RebalanceResult, RebalancePerformanceMetrics]:
    from data_partitioner import rebalance

    input_path = Path(str(rebalance_kwargs["input_path"]))
    output_dir = Path(str(rebalance_kwargs["output_dir"]))
    return measure_callable(
        lambda: rebalance(**rebalance_kwargs),
        input_path=input_path,
        output_dir=output_dir,
    )


def measure_rebalance_streaming(**rebalance_kwargs: object) -> tuple[RebalanceResult, RebalancePerformanceMetrics]:
    from data_partitioner import rebalance_streaming

    input_path = Path(str(rebalance_kwargs["input_path"]))
    output_dir = Path(str(rebalance_kwargs["output_dir"]))
    return measure_callable(
        lambda: rebalance_streaming(**rebalance_kwargs),
        input_path=input_path,
        output_dir=output_dir,
    )


def run_timed(callable_fn: Callable[[], T]) -> tuple[T, float]:
    gc.collect()
    started = perf_counter()
    value = callable_fn()
    return value, perf_counter() - started
