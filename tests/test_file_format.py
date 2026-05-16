from __future__ import annotations

import pytest

from data_partitioner import FileFormat


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("csv", FileFormat.CSV),
        ("CSV", FileFormat.CSV),
        (" parquet ", FileFormat.PARQUET),
        (FileFormat.ORC, FileFormat.ORC),
    ],
)
def test_file_format_from_value(raw: str | FileFormat, expected: FileFormat) -> None:
    assert FileFormat.from_value(raw) == expected


def test_file_format_from_value_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unsupported file format"):
        FileFormat.from_value("avro")
