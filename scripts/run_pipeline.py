"""CLI script to execute FrontierAtlas Intelligence Pipeline.

Usage:
  python scripts/run_pipeline.py [--startups N] [--products N] [--papers N]
"""

import asyncio
import argparse
import sys
import os

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.pipelines.runner import pipeline_runner


async def main():
    parser = argparse.ArgumentParser(description="Run FrontierAtlas Ingestion Pipeline")
    parser.add_argument("--startups", type=int, default=1000, help="Target startup count (default: 1000)")
    parser.add_argument("--products", type=int, default=1000, help="Target product count (default: 1000)")
    parser.add_argument("--papers", type=int, default=1000, help="Target research paper count (default: 1000)")
    args = parser.parse_args()

    print(f"Starting pipeline execution: Startups={args.startups}, Products={args.products}, Papers={args.papers}")
    summary = await pipeline_runner.execute_full_pipeline(
        startup_target=args.startups,
        product_target=args.products,
        paper_target=args.papers,
    )
    print("\n--- Pipeline Execution Summary ---")
    print(f"Status: {summary['status']}")
    print(f"Elapsed Time: {summary['elapsed_seconds']}s")
    print("Record Counts:")
    for k, v in summary["counts"].items():
        print(f"  {k}: {v}")
    print("\nExports:")
    for k, v in summary["exports"]["csv_files"].items():
        print(f"  {k}: {v}")
    print(f"  Master Excel: {summary['exports']['master_excel']}")


if __name__ == "__main__":
    asyncio.run(main())
