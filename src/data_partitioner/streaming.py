from __future__ import annotations

from pathlib import Path
from typing import Iterator, Sequence

import pandas as pd
import pyarrow.dataset as ds

from data_partitioner.core import (
    FileFormat,
    RebalanceResult,
    _infer_format,
    _normalize_input_formats,
    _validate_partitioning_args,
    _write_file,
    discover_input_files,
)


def rebalance_streaming(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    target_rows_per_file: int,
    max_memory_mb: int = 512,
    input_formats: Sequence[str | FileFormat] | None = None,
    output_format: str | FileFormat | None = None,
    glob_pattern: str = "*",
    output_prefix: str = "part",
    num_output_files: int | None = None,
) -> RebalanceResult:
    """
    Repartition inputs using bounded-memory streaming I/O.

    Reads inputs in chunks sized from ``max_memory_mb`` and writes output
    partitions without concatenating the full dataset in memory.

    Only ``target_rows_per_file`` is supported; ``num_output_files`` requires
    knowing the full row count upfront and is rejected here (use ``rebalance()`` or
    a future two-pass mode).
    """
    if num_output_files is not None:
        raise ValueError(
            "num_output_files is not supported in streaming mode. "
            "Use target_rows_per_file or the in-memory rebalance() API."
        )
    _validate_partitioning_args(target_rows_per_file, None)
    if max_memory_mb <= 0:
        raise ValueError("max_memory_mb must be > 0.")

    in_path = Path(input_path).expanduser().resolve()
    out_path = Path(output_dir).expanduser().resolve()
    normalized_input_formats = _normalize_input_formats(input_formats)
    files = discover_input_files(in_path, normalized_input_formats, glob_pattern=glob_pattern)
    if not files:
        requested = ", ".join(fmt.value for fmt in normalized_input_formats)
        raise ValueError(f"No matching input files found in {in_path} for formats: {requested}")

    selected_output_format = (
        FileFormat.from_value(output_format) if output_format is not None else _infer_format(files[0])
    )

    read_chunk_rows = _derive_read_chunk_rows(files[0], _infer_format(files[0]), max_memory_mb, target_rows_per_file)
    expected_columns = _read_columns(files[0], _infer_format(files[0]))

    out_path.mkdir(parents=True, exist_ok=True)
    writer = _StreamingPartitionWriter(
        output_dir=out_path,
        output_format=selected_output_format,
        target_rows=target_rows_per_file,
        output_prefix=output_prefix,
    )

    input_row_distribution: list[int] = []
    total_rows = 0

    for file_path in files:
        file_format = _infer_format(file_path)
        _validate_columns(file_path, file_format, expected_columns)
        file_rows = 0
        for batch in _iter_file_batches(file_path, file_format, read_chunk_rows):
            writer.add_batch(batch)
            file_rows += len(batch)
        input_row_distribution.append(file_rows)
        total_rows += file_rows

    if total_rows == 0:
        raise ValueError("Input files contain zero rows; nothing to rebalance.")

    output_paths, output_row_distribution = writer.finalize()
    return RebalanceResult(
        input_files=len(files),
        total_rows=total_rows,
        output_files=len(output_paths),
        target_rows_per_file=target_rows_per_file,
        input_rows_per_file=input_row_distribution,
        output_rows_per_file=output_row_distribution,
        output_format=selected_output_format,
        output_paths=output_paths,
    )


_MIN_CHUNK_ROWS = 1_000
_MAX_CHUNK_ROWS = 500_000
_MEMORY_FRACTION_FOR_READ = 0.4


def _derive_read_chunk_rows(
    sample_path: Path,
    file_format: FileFormat,
    max_memory_mb: int,
    target_rows_per_file: int,
) -> int:
    sample = _read_sample_rows(sample_path, file_format, rows=1_000)
    if sample.empty:
        return _MIN_CHUNK_ROWS

    bytes_per_row = float(sample.memory_usage(deep=True).sum()) / len(sample)
    bytes_per_row = max(bytes_per_row, 64.0)
    budget_bytes = max_memory_mb * 1024 * 1024 * _MEMORY_FRACTION_FOR_READ
    derived = int(budget_bytes / bytes_per_row)
    derived = max(_MIN_CHUNK_ROWS, min(derived, _MAX_CHUNK_ROWS))
    return min(derived, target_rows_per_file)


def _read_sample_rows(path: Path, file_format: FileFormat, *, rows: int) -> pd.DataFrame:
    if file_format == FileFormat.CSV:
        return pd.read_csv(path, nrows=rows)
    dataset = ds.dataset(str(path), format=_arrow_dataset_format(file_format))
    for batch in dataset.to_batches(batch_size=rows):
        return batch.to_pandas()
    return pd.DataFrame()


def _read_columns(path: Path, file_format: FileFormat) -> list[str]:
    if file_format == FileFormat.CSV:
        return list(pd.read_csv(path, nrows=0).columns)
    dataset = ds.dataset(str(path), format=_arrow_dataset_format(file_format))
    return list(dataset.schema.names)


def _validate_columns(path: Path, file_format: FileFormat, expected: list[str]) -> None:
    columns = _read_columns(path, file_format)
    if columns != expected:
        raise ValueError(
            f"Column mismatch in {path}. Expected columns {expected}, got {columns}."
        )


def _arrow_dataset_format(file_format: FileFormat) -> str:
    if file_format == FileFormat.PARQUET:
        return "parquet"
    if file_format == FileFormat.ORC:
        return "orc"
    raise ValueError(f"Arrow streaming is not used for {file_format}")


def _iter_file_batches(
    path: Path,
    file_format: FileFormat,
    chunk_rows: int,
) -> Iterator[pd.DataFrame]:
    if file_format == FileFormat.CSV:
        yield from pd.read_csv(path, chunksize=chunk_rows)
        return

    dataset = ds.dataset(str(path), format=_arrow_dataset_format(file_format))
    for batch in dataset.to_batches(batch_size=chunk_rows):
        yield batch.to_pandas()


class _StreamingPartitionWriter:
    def __init__(
        self,
        *,
        output_dir: Path,
        output_format: FileFormat,
        target_rows: int,
        output_prefix: str,
    ) -> None:
        self._output_dir = output_dir
        self._output_format = output_format
        self._target_rows = target_rows
        self._output_prefix = output_prefix
        self._buffer = pd.DataFrame()
        self._part_index = 0
        self._output_paths: list[str] = []
        self._output_rows: list[int] = []

    def add_batch(self, batch: pd.DataFrame) -> None:
        if batch.empty:
            return
        if self._buffer.empty:
            self._buffer = batch.reset_index(drop=True)
        else:
            self._buffer = pd.concat([self._buffer, batch], ignore_index=True)
        while len(self._buffer) >= self._target_rows:
            self._write_partition(self._target_rows)

    def finalize(self) -> tuple[list[str], list[int]]:
        if not self._buffer.empty:
            self._write_partition(len(self._buffer))
        return self._output_paths, self._output_rows

    def _write_partition(self, row_count: int) -> None:
        chunk = self._buffer.iloc[:row_count].reset_index(drop=True)
        self._buffer = self._buffer.iloc[row_count:].reset_index(drop=True)
        self._part_index += 1
        filename = f"{self._output_prefix}-{self._part_index:05d}.{self._output_format.value}"
        destination = self._output_dir / filename
        _write_file(chunk, destination, self._output_format)
        self._output_paths.append(str(destination))
        self._output_rows.append(len(chunk))
