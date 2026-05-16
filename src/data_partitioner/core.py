from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd


class FileFormat(str, Enum):
    CSV = "csv"
    PARQUET = "parquet"
    ORC = "orc"

    @classmethod
    def from_value(cls, value: str | FileFormat) -> FileFormat:
        if isinstance(value, FileFormat):
            return value
        normalized = value.strip().lower()
        for item in cls:
            if item.value == normalized:
                return item
        raise ValueError(f"Unsupported file format: {value!r}")


@dataclass(frozen=True)
class RebalanceResult:
    input_files: int
    total_rows: int
    output_files: int
    target_rows_per_file: int
    input_rows_per_file: list[int]
    output_rows_per_file: list[int]
    output_format: FileFormat
    output_paths: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "input_files": self.input_files,
            "total_rows": self.total_rows,
            "output_files": self.output_files,
            "target_rows_per_file": self.target_rows_per_file,
            "input_rows_per_file": self.input_rows_per_file,
            "output_rows_per_file": self.output_rows_per_file,
            "output_format": self.output_format.value,
            "output_paths": self.output_paths,
        }


_FORMAT_BY_SUFFIX = {
    ".csv": FileFormat.CSV,
    ".parquet": FileFormat.PARQUET,
    ".orc": FileFormat.ORC,
}


def rebalance(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    input_formats: Sequence[str | FileFormat] | None = None,
    output_format: str | FileFormat | None = None,
    target_rows_per_file: int | None = None,
    num_output_files: int | None = None,
    glob_pattern: str = "*",
    output_prefix: str = "part",
) -> RebalanceResult:
    """
    Repartition uneven input files into uniformly sized output files.

    V1 strategy is intentionally straightforward:
    1) read input files into pandas DataFrames,
    2) concatenate all rows,
    3) split into balanced partitions,
    4) write output files.
    """
    _validate_partitioning_args(target_rows_per_file, num_output_files)
    in_path = Path(input_path).expanduser().resolve()
    out_path = Path(output_dir).expanduser().resolve()
    normalized_input_formats = _normalize_input_formats(input_formats)
    files = discover_input_files(in_path, normalized_input_formats, glob_pattern=glob_pattern)
    if not files:
        requested = ", ".join(fmt.value for fmt in normalized_input_formats)
        raise ValueError(f"No matching input files found in {in_path} for formats: {requested}")

    input_row_distribution: list[int] = []
    frames: list[pd.DataFrame] = []
    expected_columns: list[str] | None = None

    for file_path in files:
        current_format = _infer_format(file_path)
        frame = _read_file(file_path, current_format)
        columns = list(frame.columns)
        if expected_columns is None:
            expected_columns = columns
        elif columns != expected_columns:
            raise ValueError(
                f"Column mismatch in {file_path}. Expected columns {expected_columns}, got {columns}."
            )
        input_row_distribution.append(len(frame))
        frames.append(frame)

    combined = pd.concat(frames, ignore_index=True)
    total_rows = len(combined)
    if total_rows == 0:
        raise ValueError("Input files contain zero rows; nothing to rebalance.")

    if num_output_files is not None:
        target_rows = math.ceil(total_rows / num_output_files)
    else:
        target_rows = target_rows_per_file or 0

    selected_output_format = (
        FileFormat.from_value(output_format) if output_format is not None else _infer_format(files[0])
    )

    out_path.mkdir(parents=True, exist_ok=True)
    output_paths: list[str] = []
    output_row_distribution: list[int] = []

    for part_index, start_idx in enumerate(range(0, total_rows, target_rows), start=1):
        end_idx = min(start_idx + target_rows, total_rows)
        chunk = combined.iloc[start_idx:end_idx]
        filename = f"{output_prefix}-{part_index:05d}.{selected_output_format.value}"
        destination = out_path / filename
        _write_file(chunk, destination, selected_output_format)
        output_paths.append(str(destination))
        output_row_distribution.append(len(chunk))

    return RebalanceResult(
        input_files=len(files),
        total_rows=total_rows,
        output_files=len(output_paths),
        target_rows_per_file=target_rows,
        input_rows_per_file=input_row_distribution,
        output_rows_per_file=output_row_distribution,
        output_format=selected_output_format,
        output_paths=output_paths,
    )


def discover_input_files(
    input_path: Path,
    input_formats: Iterable[FileFormat],
    *,
    glob_pattern: str = "*",
) -> list[Path]:
    allowed = set(input_formats)
    if input_path.is_file():
        current_format = _infer_format(input_path)
        return [input_path] if current_format in allowed else []

    if not input_path.exists():
        raise ValueError(f"Input path does not exist: {input_path}")
    if not input_path.is_dir():
        raise ValueError(f"Input path must be a file or directory: {input_path}")

    files: list[Path] = []
    for candidate in input_path.rglob(glob_pattern):
        if not candidate.is_file():
            continue
        try:
            current_format = _infer_format(candidate)
        except ValueError:
            continue
        if current_format in allowed:
            files.append(candidate)
    return sorted(files)


def _validate_partitioning_args(
    target_rows_per_file: int | None,
    num_output_files: int | None,
) -> None:
    if target_rows_per_file is not None and num_output_files is not None:
        raise ValueError("Provide only one of target_rows_per_file or num_output_files, not both.")
    if target_rows_per_file is None and num_output_files is None:
        raise ValueError("Provide either target_rows_per_file or num_output_files.")
    if target_rows_per_file is not None and target_rows_per_file <= 0:
        raise ValueError("target_rows_per_file must be > 0.")
    if num_output_files is not None and num_output_files <= 0:
        raise ValueError("num_output_files must be > 0.")


def _normalize_input_formats(input_formats: Sequence[str | FileFormat] | None) -> list[FileFormat]:
    if input_formats is None:
        return [FileFormat.CSV, FileFormat.PARQUET, FileFormat.ORC]
    normalized = [FileFormat.from_value(item) for item in input_formats]
    if not normalized:
        raise ValueError("input_formats cannot be empty.")
    return normalized


def _infer_format(path: Path) -> FileFormat:
    suffix = path.suffix.lower()
    if suffix not in _FORMAT_BY_SUFFIX:
        raise ValueError(f"Unsupported file extension for {path}. Allowed: .csv, .parquet, .orc")
    return _FORMAT_BY_SUFFIX[suffix]


def _read_file(path: Path, file_format: FileFormat) -> pd.DataFrame:
    if file_format == FileFormat.CSV:
        return pd.read_csv(path)
    if file_format == FileFormat.PARQUET:
        return pd.read_parquet(path)
    if file_format == FileFormat.ORC:
        if not hasattr(pd, "read_orc"):
            raise RuntimeError("Your pandas version does not support ORC. Upgrade pandas/pyarrow.")
        return pd.read_orc(path)
    raise ValueError(f"Unsupported format: {file_format}")


def _write_file(frame: pd.DataFrame, path: Path, file_format: FileFormat) -> None:
    if file_format == FileFormat.CSV:
        frame.to_csv(path, index=False)
        return
    if file_format == FileFormat.PARQUET:
        frame.to_parquet(path, index=False)
        return
    if file_format == FileFormat.ORC:
        if not hasattr(frame, "to_orc"):
            raise RuntimeError("Your pandas version does not support ORC writing. Upgrade pandas/pyarrow.")
        # ORC writer requires a default RangeIndex; iloc slices keep source row labels.
        frame.reset_index(drop=True).to_orc(path, index=False)
        return
    raise ValueError(f"Unsupported format: {file_format}")
