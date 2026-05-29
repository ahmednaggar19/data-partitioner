from __future__ import annotations

from pathlib import Path

import pytest

from data_partitioner import FileFormat, rebalance, rebalance_streaming
from tests.performance.metrics import (
    RebalancePerformanceMetrics,
    measure_rebalance,
    measure_rebalance_streaming,
)


def _comparison_dict(mode: str, metrics: RebalancePerformanceMetrics) -> dict[str, object]:
    payload = metrics.as_dict()
    payload["mode"] = mode
    return payload


def _memory_reduction_ratio(in_memory: RebalancePerformanceMetrics, streaming: RebalancePerformanceMetrics) -> float:
    if in_memory.peak_traced_memory_bytes == 0:
        return 0.0
    saved = in_memory.peak_traced_memory_bytes - streaming.peak_traced_memory_bytes
    return saved / in_memory.peak_traced_memory_bytes


@pytest.mark.performance
def test_streaming_vs_in_memory_performance_comparison(
    tmp_path: Path,
    comparison_csv_dataset: tuple[Path, int],
    performance_report: list[dict[str, object]],
) -> None:
    """
    Compare rebalance() (full in-memory) vs rebalance_streaming() on the same CSV workload.

    Streaming should use materially less peak traced memory; wall time may be similar or slightly higher.
    """
    source, expected_rows = comparison_csv_dataset
    target_rows = 10_000
    memory_out = tmp_path / "compare_memory"
    stream_out = tmp_path / "compare_streaming"

    memory_result, memory_metrics = measure_rebalance(
        input_path=source,
        output_dir=memory_out,
        input_formats=[FileFormat.CSV],
        output_format=FileFormat.CSV,
        target_rows_per_file=target_rows,
    )
    stream_result, stream_metrics = measure_rebalance_streaming(
        input_path=source,
        output_dir=stream_out,
        input_formats=[FileFormat.CSV],
        output_format=FileFormat.CSV,
        target_rows_per_file=target_rows,
        max_memory_mb=64,
    )

    assert memory_result.total_rows == expected_rows
    assert stream_result.total_rows == expected_rows
    assert memory_result.output_rows_per_file == stream_result.output_rows_per_file

    reduction = _memory_reduction_ratio(memory_metrics, stream_metrics)
    performance_report.append(_comparison_dict("in_memory", memory_metrics))
    performance_report.append(_comparison_dict("streaming", stream_metrics))
    performance_report.append(
        {
            "test": "streaming_vs_in_memory",
            "workload_rows": expected_rows,
            "workload_input_mb": memory_metrics.as_dict()["input_disk_mb"],
            "memory_reduction_ratio": round(reduction, 4),
            "memory_mb_in_memory": memory_metrics.as_dict()["peak_traced_memory_mb"],
            "memory_mb_streaming": stream_metrics.as_dict()["peak_traced_memory_mb"],
            "elapsed_s_in_memory": round(memory_metrics.elapsed_seconds, 4),
            "elapsed_s_streaming": round(stream_metrics.elapsed_seconds, 4),
        }
    )

    # Streaming must beat in-memory on peak traced memory for this workload.
    assert stream_metrics.peak_traced_memory_bytes < memory_metrics.peak_traced_memory_bytes, (
        f"expected streaming peak memory < in-memory; "
        f"got streaming={stream_metrics.peak_traced_memory_bytes} "
        f"in_memory={memory_metrics.peak_traced_memory_bytes}"
    )
    assert reduction >= 0.15, (
        f"expected >=15% peak memory reduction from streaming; got {reduction:.1%}"
    )
