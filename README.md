# data-partitioner

`data-partitioner` is a Python library for rebalancing uneven datasets into consistently sized files.

Initial supported formats:
- CSV
- Parquet
- ORC

## Install

```bash
pip install -e .
```

## Python API

```python
from data_partitioner import rebalance

result = rebalance(
    input_path="data/raw",
    output_dir="data/balanced",
    target_rows_per_file=100_000,
    output_format="parquet",
)
print(result.as_dict())
```

## CLI

```bash
data-partitioner data/raw data/balanced --target-rows-per-file 100000 --output-format parquet
```

Or drive by output file count:

```bash
data-partitioner data/raw data/balanced --num-output-files 12 --output-format parquet
```

## Current implementation notes

Version `0.1.0` uses a straightforward in-memory approach (read all matched files, concatenate, repartition, write outputs). This gives a usable baseline quickly and is a good foundation for future large-scale/streaming optimizations.
