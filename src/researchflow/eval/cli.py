"""CLI for the eval harness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from researchflow.eval.fixtures import load_all, load_fixture
from researchflow.eval.harness import run_all


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(prog="researchflow.eval")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run fixtures and write artifacts")
    p_run.add_argument("--fixtures", type=Path, default=Path("eval/fixtures"))
    p_run.add_argument("--out", type=Path, default=Path("eval/runs"))
    p_run.add_argument(
        "--fixture",
        type=str,
        default=None,
        help="Run a single fixture id (searches for fixture.yaml with this id)",
    )
    p_run.add_argument("--run-id", type=str, default=None)

    p_list = sub.add_parser("list", help="List available fixtures")
    p_list.add_argument("--fixtures", type=Path, default=Path("eval/fixtures"))

    args = parser.parse_args(argv)

    if args.cmd == "list":
        for fx in load_all(args.fixtures):
            print(f"{fx.id}  [{', '.join(fx.tags) or '-'}]  recipe={fx.recipe}")
        return 0

    if args.cmd == "run":
        all_fx = load_all(args.fixtures)
        if args.fixture:
            all_fx = [f for f in all_fx if f.id == args.fixture]
            if not all_fx:
                print(f"No fixture matching id={args.fixture}", file=sys.stderr)
                return 2
        summary = run_all(all_fx, runs_dir=args.out, run_id=args.run_id)
        print(f"Run {summary.run_id}: {len(summary.fixtures)} fixtures, "
              f"pass_rate={summary.pass_rate:.2%}")
        for fc in summary.fixtures:
            mark = "PASS" if fc.overall_passed else "FAIL"
            per_stage = ", ".join(
                f"{s.stage}={'P' if s.passed else 'F'}" for s in fc.stages
            )
            print(f"  [{mark}] {fc.fixture_id}  ({per_stage})")
        return 0 if all(fc.overall_passed for fc in summary.fixtures) else 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
