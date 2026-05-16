from __future__ import annotations

import pytest

from data_partitioner.core import FileFormat, discover_input_files
from tests.helpers import make_frame


def test_discover_single_csv_file(tmp_path) -> None:
    path = tmp_path / "only.csv"
    make_frame(2).to_csv(path, index=False)

    found = discover_input_files(path, [FileFormat.CSV])
    assert found == [path]


def test_discover_single_file_wrong_format_returns_empty(tmp_path) -> None:
    path = tmp_path / "only.csv"
    make_frame(2).to_csv(path, index=False)

    assert discover_input_files(path, [FileFormat.PARQUET]) == []


def test_discover_directory_recursive(tmp_path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    make_frame(1).to_csv(tmp_path / "root.csv", index=False)
    make_frame(1).to_csv(nested / "deep.csv", index=False)
    (tmp_path / "notes.txt").write_text("skip")

    found = discover_input_files(tmp_path, [FileFormat.CSV])
    assert [p.name for p in found] == ["deep.csv", "root.csv"]


def test_discover_respects_glob_pattern(tmp_path) -> None:
    make_frame(1).to_csv(tmp_path / "keep_a.csv", index=False)
    make_frame(1).to_csv(tmp_path / "skip_b.csv", index=False)

    found = discover_input_files(tmp_path, [FileFormat.CSV], glob_pattern="keep_*.csv")
    assert [p.name for p in found] == ["keep_a.csv"]


def test_discover_skips_unsupported_extensions(tmp_path) -> None:
    make_frame(1).to_csv(tmp_path / "data.csv", index=False)
    (tmp_path / "data.json").write_text("{}")

    found = discover_input_files(tmp_path, [FileFormat.CSV, FileFormat.PARQUET])
    assert [p.name for p in found] == ["data.csv"]


def test_discover_raises_when_path_missing(tmp_path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ValueError, match="does not exist"):
        discover_input_files(missing, [FileFormat.CSV])
