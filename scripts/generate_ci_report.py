#!/usr/bin/env python3
"""Build a markdown CI report from pytest JUnit XML, coverage XML, and performance JSON."""

from __future__ import annotations

import argparse
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path


def _junit_stats(path: Path) -> dict[str, int | str]:
    if not path.is_file():
        return {"status": "missing", "tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}

    root = ET.parse(path).getroot()
    if root.tag == "testsuites":
        tests = failures = errors = skipped = 0
        time = 0.0
        for suite in root.findall("testsuite"):
            tests += int(suite.get("tests", 0))
            failures += int(suite.get("failures", 0))
            errors += int(suite.get("errors", 0))
            skipped += int(suite.get("skipped", 0))
            time += float(suite.get("time", 0.0))
    else:
        tests = int(root.get("tests", 0))
        failures = int(root.get("failures", 0))
        errors = int(root.get("errors", 0))
        skipped = int(root.get("skipped", 0))
        time = float(root.get("time", 0.0))

    passed = tests - failures - errors - skipped
    status = "passed" if failures == 0 and errors == 0 else "failed"
    return {
        "status": status,
        "tests": tests,
        "passed": passed,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "time": round(time, 2),
    }


def _coverage_percent(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"status": "missing", "line_rate": None}

    root = ET.parse(path).getroot()
    line_rate = root.get("line-rate")
    if line_rate is None:
        return {"status": "missing", "line_rate": None}
    percent = round(float(line_rate) * 100, 2)
    return {"status": "ok", "line_rate": percent}


def _performance_rows(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"status": "missing", "perf_scale": None, "benchmarks": []}

    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "status": "ok",
        "perf_scale": payload.get("perf_scale"),
        "benchmarks": payload.get("benchmarks", []),
    }


def _status_badge(status: str) -> str:
    if status in {"passed", "ok"}:
        return "✅"
    if status == "missing":
        return "⚠️"
    return "❌"


def build_report(
    *,
    unit_junit: Path,
    perf_junit: Path,
    coverage_xml: Path,
    performance_json: Path,
    output_path: Path,
) -> str:
    unit = _junit_stats(unit_junit)
    perf = _junit_stats(perf_junit)
    coverage = _coverage_percent(coverage_xml)
    performance = _performance_rows(performance_json)

    sha = os.environ.get("GITHUB_SHA", "")[:7]
    ref = os.environ.get("GITHUB_REF_NAME", os.environ.get("GITHUB_REF", ""))
    workflow = os.environ.get("GITHUB_WORKFLOW", "CI")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_url = f"{server}/{repo}/actions/runs/{run_id}" if run_id and repo else ""

    lines = [
        "## CI test report",
        "",
        f"| | |",
        f"|---|---|",
        f"| Workflow | `{workflow}` |",
        f"| Ref | `{ref}` |",
    ]
    if sha:
        lines.append(f"| Commit | `{sha}` |")
    if run_url:
        lines.append(f"| Run | [View workflow run]({run_url}) |")
    lines.extend(["", "### Unit tests", ""])
    lines.append(
        f"{_status_badge(str(unit['status']))} **{unit['status']}** — "
        f"{unit['passed']}/{unit['tests']} passed"
        f" ({unit['failures']} failures, {unit['errors']} errors, {unit['skipped']} skipped) "
        f"in {unit['time']}s"
    )
    if coverage["line_rate"] is not None:
        lines.extend(
            [
                "",
                f"**Coverage:** {coverage['line_rate']}% line rate (threshold: 90%)",
            ]
        )
    else:
        lines.extend(["", "**Coverage:** not available"])

    lines.extend(["", "### Performance tests", ""])
    lines.append(
        f"{_status_badge(str(perf['status']))} **{perf['status']}** — "
        f"{perf['passed']}/{perf['tests']} passed"
        f" ({perf['failures']} failures, {perf['errors']} errors) in {perf['time']}s"
    )

    if performance["status"] == "ok" and performance["benchmarks"]:
        scale = performance["perf_scale"] or "unknown"
        lines.extend(["", f"**PERF_SCALE:** `{scale}`", ""])
        lines.append("| Benchmark | Time (s) | Memory (MB) | Input (MB) | Output (MB) | Rows |")
        lines.append("|-----------|----------|-------------|------------|-------------|------|")
        for entry in performance["benchmarks"]:
            name = entry.get("test", "benchmark")
            lines.append(
                "| {name} | {elapsed:.3f} | {mem:.3f} | {inp:.3f} | {out:.3f} | {rows:,} |".format(
                    name=name,
                    elapsed=float(entry.get("elapsed_seconds", 0)),
                    mem=float(entry.get("peak_traced_memory_mb", 0)),
                    inp=float(entry.get("input_disk_mb", 0)),
                    out=float(entry.get("output_disk_mb", 0)),
                    rows=int(entry.get("total_rows", 0)),
                )
            )
    else:
        lines.append("")
        lines.append("_Performance metrics not collected._")

    lines.append("")
    lines.append(
        "<sub>Updated by GitHub Actions · "
        "Report generated from unit JUnit, coverage XML, and performance JSON artifacts.</sub>"
    )

    markdown = "\n".join(lines) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit-junit", type=Path, default=Path("reports/unit-junit.xml"))
    parser.add_argument("--perf-junit", type=Path, default=Path("reports/perf-junit.xml"))
    parser.add_argument("--coverage-xml", type=Path, default=Path("reports/coverage.xml"))
    parser.add_argument(
        "--performance-json",
        type=Path,
        default=Path("reports/performance-metrics.json"),
    )
    parser.add_argument("--output", type=Path, default=Path("reports/ci-report.md"))
    args = parser.parse_args()

    markdown = build_report(
        unit_junit=args.unit_junit,
        perf_junit=args.perf_junit,
        coverage_xml=args.coverage_xml,
        performance_json=args.performance_json,
        output_path=args.output,
    )
    print(markdown)


if __name__ == "__main__":
    main()
