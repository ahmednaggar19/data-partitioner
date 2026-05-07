from __future__ import annotations

import argparse
import json
from typing import Sequence

from data_partitioner.core import FileFormat, rebalance


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data-partitioner",
        description="Rebalance uneven CSV/Parquet/ORC files into uniform output partitions.",
    )
    parser.add_argument("input_path", help="Input file or directory.")
    parser.add_argument("output_dir", help="Directory where balanced output files are written.")
    parser.add_argument(
        "--input-formats",
        nargs="+",
        choices=[fmt.value for fmt in FileFormat],
        default=[fmt.value for fmt in FileFormat],
        help="Input file formats to include (default: csv parquet orc).",
    )
    parser.add_argument(
        "--output-format",
        choices=[fmt.value for fmt in FileFormat],
        default=None,
        help="Output file format (default: infer from first input file).",
    )
    parser.add_argument(
        "--glob-pattern",
        default="*",
        help="Glob pattern for recursive file discovery inside input directory.",
    )
    parser.add_argument(
        "--output-prefix",
        default="part",
        help="Prefix for output files (default: part).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print output summary as JSON.",
    )

    sizing = parser.add_mutually_exclusive_group(required=True)
    sizing.add_argument(
        "--target-rows-per-file",
        type=int,
        default=None,
        help="Desired number of rows in each output file.",
    )
    sizing.add_argument(
        "--num-output-files",
        type=int,
        default=None,
        help="Desired number of output files (row target is derived automatically).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = rebalance(
        input_path=args.input_path,
        output_dir=args.output_dir,
        input_formats=args.input_formats,
        output_format=args.output_format,
        target_rows_per_file=args.target_rows_per_file,
        num_output_files=args.num_output_files,
        glob_pattern=args.glob_pattern,
        output_prefix=args.output_prefix,
    )
    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        print(f"Input files: {result.input_files}")
        print(f"Total rows: {result.total_rows}")
        print(f"Output files: {result.output_files}")
        print(f"Target rows/file: {result.target_rows_per_file}")
        print(f"Output format: {result.output_format.value}")
        print("Output row distribution:", ", ".join(str(n) for n in result.output_rows_per_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
