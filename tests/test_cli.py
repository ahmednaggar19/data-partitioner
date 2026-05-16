from __future__ import annotations

import json

import pytest

from data_partitioner.cli import build_parser, main
from tests.helpers import make_frame


def test_build_parser_requires_sizing_mode() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["input", "output"])


def test_main_human_output(tmp_path, capsys) -> None:
    source = tmp_path / "source"
    output = tmp_path / "balanced"
    source.mkdir()
    make_frame(5).to_csv(source / "data.csv", index=False)

    code = main(
        [
            str(source),
            str(output),
            "--target-rows-per-file",
            "3",
            "--input-formats",
            "csv",
            "--output-format",
            "csv",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert "Input files: 1" in captured.out
    assert "Total rows: 5" in captured.out
    assert "Output files: 2" in captured.out


def test_main_json_output(tmp_path, capsys) -> None:
    source = tmp_path / "source"
    output = tmp_path / "balanced"
    source.mkdir()
    make_frame(4).to_csv(source / "data.csv", index=False)

    code = main(
        [
            str(source),
            str(output),
            "--num-output-files",
            "2",
            "--input-formats",
            "csv",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["total_rows"] == 4
    assert payload["output_format"] == "csv"
    assert payload["output_files"] == 2
