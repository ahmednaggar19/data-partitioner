# Agent guide — data-partitioner

Use this file as the entry point when working on this repository with agentic AI tools (Cursor, Copilot, Codex, etc.).

## What this project does

Python library (alpha v0.1.0) that **rebalances uneven CSV/Parquet/ORC files** into uniformly sized output partitions. V1 loads all data in memory via pandas, concatenates, slices by row count, and writes `part-00001.{ext}` style outputs.

## Read first

| Document | Purpose |
|----------|---------|
| [docs/architecture.md](docs/architecture.md) | Modules, data flow, API surface, errors, V1 limits |
| [docs/testing.md](docs/testing.md) | Unit vs performance tests, coverage, `PERF_SCALE` |
| [README.md](README.md) | User-facing install and usage |

## Source of truth

- **Core logic**: `src/data_partitioner/core.py` — `rebalance()`, `discover_input_files()`, I/O
- **Streaming**: `src/data_partitioner/streaming.py` — `rebalance_streaming()` (bounded memory)
- **CLI**: `src/data_partitioner/cli.py` — `data-partitioner` entry point
- **Public exports**: `src/data_partitioner/__init__.py`

Do not duplicate business logic outside `core.py`; CLI should remain a thin wrapper.

## Conventions

- Python **3.9+**, `src/` layout, package name `data_partitioner`
- Dependencies: `pandas`, `pyarrow` (see `pyproject.toml`)
- Tests: pytest; shared frame builder in `tests/conftest.py`
- Only create git commits when the user explicitly asks

## Safe change patterns

1. **New format** — extend `FileFormat`, `_FORMAT_BY_SUFFIX`, `_read_file`, `_write_file`, CLI choices, tests
2. **New sizing mode** — update `_validate_partitioning_args`, `rebalance()` chunk logic, CLI mutually exclusive group, tests
3. **Performance work** — prefer extending `tests/performance/metrics.py`; keep unit tests fast
4. **Breaking API** — bump version and document in README; preserve `RebalanceResult` fields when possible

## Commands

```bash
pip install -e ".[dev]"

# Unit tests + coverage
pytest tests/ --ignore=tests/performance --cov=data_partitioner --cov-report=term-missing

# Performance benchmarks
pytest tests/performance -m performance -v

# Lint
flake8 .
```

## Out of scope for drive-by changes

- Large refactors unrelated to the task
- New markdown docs unless requested
- Committing without user request
- Force-pushing `master`

See **Known limitations** in `docs/architecture.md` for V1 vs streaming behavior.
