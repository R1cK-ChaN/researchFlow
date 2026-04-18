"""Eval harness: run fixtures through the flow, write artifacts, score each stage."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from researchflow.eval.contracts import (
    Fixture,
    FixtureScorecard,
    RunSummary,
    StageScore,
)
from researchflow.eval.mock_client import QueueClient
from researchflow.eval.runners import (
    run_context,
    run_generation,
    run_postprocess,
    run_validation,
)
from researchflow.eval.scorers import (
    score_context,
    score_generation,
    score_postprocess,
    score_validation,
)
from researchflow.generation.contracts import GeneratorParams


def run_fixture(
    fixture: Fixture,
    *,
    out_dir: Path,
    client: Any | None = None,
    judge_client: Any | None = None,
    generator_params: GeneratorParams | None = None,
) -> FixtureScorecard:
    """Execute every pipeline stage on a fixture, write artifacts, score.

    If `client` is None and `fixture.mock_responses` is non-empty, a
    `QueueClient` is built and used for both generation and judges. If
    both are None and `mock_responses` is empty, generation+judges are
    skipped — the harness still scores context + any declared stages.
    """
    fx_dir = out_dir / fixture.id
    fx_dir.mkdir(parents=True, exist_ok=True)

    stages: list[StageScore] = []

    # Stage 1: context
    context, ctx_artifacts = run_context(fixture)
    _write_artifacts(fx_dir / "01_context", ctx_artifacts)
    stages.append(score_context(context, fixture.expected.context))

    # Set up mock client if needed
    active_client = client
    active_judge = judge_client
    if active_client is None and fixture.mock_responses:
        queue = QueueClient(fixture.mock_responses)
        active_client = queue
        if active_judge is None:
            active_judge = queue

    # Stage 2: generation (skip if no client)
    report = None
    if active_client is not None:
        report, gen_artifacts = run_generation(
            context, client=active_client, params=generator_params
        )
        _write_artifacts(fx_dir / "02_generation", gen_artifacts)
        stages.append(score_generation(report, fixture.expected.report))

        # Stage 3: postprocess
        finalized, pp_artifacts = run_postprocess(report)
        _write_artifacts(fx_dir / "03_postprocess", pp_artifacts)
        stages.append(score_postprocess(finalized, fixture.expected.postprocess))

        # Stage 4: validation
        vr, val_artifacts = run_validation(finalized, context, judge_client=active_judge)
        _write_artifacts(fx_dir / "04_validation", val_artifacts)
        stages.append(score_validation(vr, fixture.expected.validation))
    else:
        stages.append(
            StageScore(stage="generation", passed=True, notes=["skipped — no client"])
        )
        stages.append(
            StageScore(stage="postprocess", passed=True, notes=["skipped — generation not run"])
        )
        stages.append(
            StageScore(stage="validation", passed=True, notes=["skipped — generation not run"])
        )

    scorecard = FixtureScorecard(
        fixture_id=fixture.id,
        overall_passed=all(s.passed for s in stages),
        stages=stages,
    )
    (fx_dir / "scorecard.json").write_text(scorecard.model_dump_json(indent=2))
    return scorecard


def run_all(
    fixtures: list[Fixture],
    *,
    runs_dir: Path,
    run_id: str | None = None,
    client: Any | None = None,
    judge_client: Any | None = None,
    generator_params: GeneratorParams | None = None,
) -> RunSummary:
    """Run a set of fixtures in order, producing one artifact tree + summary."""
    started = datetime.now(timezone.utc)
    run_id = run_id or _default_run_id(started)
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    scorecards: list[FixtureScorecard] = []
    for fx in fixtures:
        scorecards.append(
            run_fixture(
                fx,
                out_dir=run_dir,
                client=client,
                judge_client=judge_client,
                generator_params=generator_params,
            )
        )

    finished = datetime.now(timezone.utc)
    summary = RunSummary(
        run_id=run_id,
        started_at=started,
        finished_at=finished,
        git_commit=_git_commit(),
        fixtures=scorecards,
    )
    (run_dir / "summary.json").write_text(summary.model_dump_json(indent=2))
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "started_at": started.isoformat(),
                "git_commit": summary.git_commit,
                "fixture_ids": [fx.id for fx in fixtures],
                "pass_rate": summary.pass_rate,
            },
            indent=2,
        )
    )
    return summary


def _write_artifacts(dir_path: Path, artifacts: dict[str, str]) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts.items():
        (dir_path / name).write_text(content)


def _default_run_id(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H-%M-%S_") + uuid4().hex[:6]


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None
