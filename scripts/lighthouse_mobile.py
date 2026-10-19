"""Run Lighthouse mobile audit 3 times against production build (Phase C4).

Computes median scores, records environment/CPU specs, and enforces gates:
- Accessibility median >= 95
- Performance median >= 80
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_URL = "http://127.0.0.1:3002"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "audit_output"


def collect_system_env() -> Dict[str, Any]:
    return {
        "os": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "python_version": platform.python_version(),
    }


def run_single_lighthouse(url: str, output_json: Path) -> Dict[str, Any]:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx",
        "--yes",
        "lighthouse",
        url,
        "--output=json",
        f"--output-path={output_json}",
        "--only-categories=performance,accessibility",
        '--chrome-flags="--headless=new --no-sandbox"',
        "--quiet",
    ]

    # Run via shell on Windows so npx is found in PATH
    res = subprocess.run(
        " ".join(cmd),
        shell=True,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Lighthouse failed (exit {res.returncode}):\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")

    if not output_json.is_file():
        raise RuntimeError(f"Lighthouse failed to produce output at {output_json}")

    data = json.loads(output_json.read_text(encoding="utf-8"))
    return data


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Lighthouse 3-run mobile audit")
    parser.add_argument("--url", type=str, default=DEFAULT_URL, help="Target URL (default: http://127.0.0.1:3002)")
    parser.add_argument("--runs", type=int, default=3, help="Number of audit runs (default: 3)")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR), help="Output directory")
    args = parser.parse_args(argv)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    env_info = collect_system_env()

    print("\n" + "=" * 70)
    print("LIGHTHOUSE MOBILE 3-RUN AUDIT (PHASE C4)")
    print("=" * 70)
    print(f"Target URL:    {args.url}")
    print(f"Environment:   {env_info['os']} {env_info['release']} | {env_info['processor']} | {env_info['cpu_count']} Logical Cores")
    print(f"Output Dir:    {out_dir}")
    print("-" * 70)

    perf_scores: List[float] = []
    a11y_scores: List[float] = []
    benchmark_indices: List[float] = []
    run_files: List[str] = []

    for i in range(1, args.runs + 1):
        run_file = out_dir / f"lighthouse_run_{i}.json"
        print(f"  [Run {i}/{args.runs}] Executing Lighthouse mobile audit...")
        t0 = time.time()
        try:
            lhr = run_single_lighthouse(args.url, run_file)
        except Exception as exc:
            print(f"  [Run {i}] FAILED: {exc}", file=sys.stderr)
            return 1
        elapsed = time.time() - t0

        perf = round(lhr["categories"]["performance"]["score"] * 100)
        a11y = round(lhr["categories"]["accessibility"]["score"] * 100)
        bench = lhr.get("environment", {}).get("benchmarkIndex", 0)

        perf_scores.append(perf)
        a11y_scores.append(a11y)
        benchmark_indices.append(bench)
        run_files.append(str(run_file.name))

        print(f"  [Run {i}] Completed in {elapsed:.1f}s -> Performance: {perf}/100 | Accessibility: {a11y}/100 (BenchmarkIndex: {bench})")

    perf_median = statistics.median(perf_scores)
    a11y_median = statistics.median(a11y_scores)
    bench_median = statistics.median(benchmark_indices)

    summary = {
        "url": args.url,
        "runs": args.runs,
        "environment": env_info,
        "scores": {
            "performance": {
                "runs": perf_scores,
                "median": perf_median,
                "gate_passed": perf_median >= 80,
            },
            "accessibility": {
                "runs": a11y_scores,
                "median": a11y_median,
                "gate_passed": a11y_median >= 95,
            },
            "benchmark_index": {
                "runs": benchmark_indices,
                "median": bench_median,
            },
        },
        "run_artifacts": run_files,
    }

    summary_file = out_dir / "lighthouse_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("-" * 70)
    print("MEDIAN RESULTS:")
    print(f"  Accessibility Median: {a11y_median:.0f}/100 (Gate: >= 95) -> {'PASS' if a11y_median >= 95 else 'FAIL'}")
    print(f"  Performance Median:   {perf_median:.0f}/100 (Gate: >= 80) -> {'PASS' if perf_median >= 80 else 'FAIL'}")
    print(f"  CPU Benchmark Index:  {bench_median:.0f} (higher is faster hardware)")
    print(f"Summary written to: {summary_file}")
    print("=" * 70 + "\n")

    if a11y_median < 95:
        print(f"FAIL: Accessibility median {a11y_median} < 95", file=sys.stderr)
        return 1

    if perf_median < 80:
        print(f"WARN: Performance median {perf_median} < 80 (system load or throttling)", file=sys.stderr)
        # Note: allow if caused by heavy system load as stated in spec
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
