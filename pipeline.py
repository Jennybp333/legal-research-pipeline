"""Legal research pipeline — top-level orchestrator.

Usage:
    python pipeline.py cases/<case-id>
    python pipeline.py cases/<case-id> --skip stage1   # skip already-done stages
    python pipeline.py cases/<case-id> --only stage3   # run a single stage

Each stage reads from / writes to files under the case directory, so partial
runs are safe — Stage 2 expects `research_notes.md`, Stage 3 expects
`verified_claims.md`, etc.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from stages import stage1_research, stage2_verify, stage3_write


def _validate_case_dir(case_dir: Path) -> None:
    if not case_dir.exists():
        sys.exit(f"error: case directory does not exist: {case_dir}")
    input_md = case_dir / "input.md"
    if not input_md.exists():
        sys.exit(f"error: {input_md} not found. Copy cases/_template/input.md and fill it in.")


async def run_pipeline(case_dir: Path, skip: set[str], only: str | None) -> None:
    _validate_case_dir(case_dir)

    def should_run(stage: str) -> bool:
        if only is not None:
            return stage == only
        return stage not in skip

    if should_run("stage1"):
        await stage1_research.run(case_dir)
    else:
        print("[stage1] skipped")

    if should_run("stage2"):
        await stage2_verify.run(case_dir)
    else:
        print("[stage2] skipped")

    if should_run("stage3"):
        await stage3_write.run(case_dir)
    else:
        print("[stage3] skipped")

    print("\nPipeline complete.")
    print(f"  Outputs in: {case_dir / 'output'}/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the legal research pipeline for one case.")
    parser.add_argument("case_dir", type=Path, help="Case directory under cases/, e.g. cases/2026-05-foo")
    parser.add_argument("--skip", action="append", default=[], choices=["stage1", "stage2", "stage3"],
                        help="Skip a stage (can be passed multiple times).")
    parser.add_argument("--only", choices=["stage1", "stage2", "stage3"],
                        help="Run only the specified stage. Overrides --skip.")
    args = parser.parse_args()

    asyncio.run(run_pipeline(args.case_dir.resolve(), set(args.skip), args.only))


if __name__ == "__main__":
    main()
