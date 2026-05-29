# Testing

## Unit tests

Fast correctness tests live under `tests/` (excluding `tests/performance/`).

```bash
pip install -e ".[dev]"
pytest tests/ --ignore=tests/performance --cov=data_partitioner --cov-report=term-missing
```

Pytest is configured with `pythonpath = ["src", "."]` so tests use the local package under `src/` (not an older install in `site-packages`). After pulling changes, run `pip install -e ".[dev]"` if imports still look stale.

Coverage is enforced in CI (`--cov-fail-under=90`).

### Test modules

| File | Focus |
|------|--------|
| `test_rebalance.py` | Core CSV/Parquet rebalance paths, column mismatch |
| `test_rebalance_extended.py` | Single file, data integrity, format inference, prefix, format conversion, ORC |
| `test_discover_input_files.py` | Discovery and glob behavior |
| `test_validation.py` | Argument and input validation errors |
| `test_file_format.py` | `FileFormat.from_value` |
| `test_rebalance_result.py` | `RebalanceResult.as_dict()` |
| `test_cli.py` | CLI human and JSON output |

Shared fixtures: `tests/conftest.py` (`make_frame`).

## Performance tests

Located in `tests/performance/`. Marked with `@pytest.mark.performance`.

They record:

| Metric | Meaning |
|--------|---------|
| `elapsed_seconds` | Wall-clock time for `rebalance()` |
| `peak_traced_memory_bytes` | Peak Python allocations during the call (`tracemalloc`) |
| `input_disk_bytes` | Sum of input file sizes on disk before rebalance |
| `output_disk_bytes` | Sum of output file sizes on disk after rebalance |

```bash
pytest tests/performance -m performance -v
```

### Scaling workloads

Set `PERF_SCALE` to control dataset size:

| `PERF_SCALE` | Rows per input file (approx.) | Input files |
|--------------|-------------------------------|-------------|
| `small` (default) | 5,000 | 5 |
| `medium` | 50,000 | 10 |
| `large` | 200,000 | 20 |

Example:

```bash
PERF_SCALE=medium pytest tests/performance -m performance -v
```

`tests/performance/metrics.py` provides `measure_rebalance()`, `measure_rebalance_streaming()`, and `RebalancePerformanceMetrics`.

### In-memory vs streaming comparison

`test_streaming_comparison.py` runs both APIs on a fixed **200k-row CSV** workload (8 × 25k rows, ~2.8 MB on disk) and asserts streaming uses less peak traced memory. Results are written to `reports/performance-metrics.json` under `streaming_vs_in_memory`.

```bash
pytest tests/performance/test_streaming_comparison.py -m performance -v
cat reports/performance-metrics.json
```

## CI

GitHub Actions (`.github/workflows/python-app.yml`):

1. **Lint** — `flake8`
2. **Unit tests** — pytest with coverage (performance excluded)
3. **Performance** — pytest performance suite (`PERF_SCALE=small`)
4. **Report** — `scripts/generate_ci_report.py` builds a markdown summary from JUnit XML, coverage XML, and performance JSON

On pull requests, the report is posted as an updated sticky comment and attached to the workflow **Summary** tab for each run. On pushes to `master`, only the job summary is published.
