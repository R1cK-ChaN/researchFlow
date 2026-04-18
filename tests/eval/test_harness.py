from __future__ import annotations

import json
from pathlib import Path

from researchflow.eval.fixtures import load_all
from researchflow.eval.harness import run_all, run_fixture

REPO_FIXTURES = Path(__file__).resolve().parents[2] / "eval" / "fixtures"


def test_run_fixture_produces_artifacts(tmp_path):
    fx = load_all(REPO_FIXTURES)[0]
    scorecard = run_fixture(fx, out_dir=tmp_path)
    fx_dir = tmp_path / fx.id
    # Every stage should have written at least one artifact dir.
    assert (fx_dir / "01_context" / "output.xml").is_file()
    assert (fx_dir / "01_context" / "trace.json").is_file()
    assert (fx_dir / "02_generation" / "output.md").is_file()
    assert (fx_dir / "03_postprocess" / "output.md").is_file()
    assert (fx_dir / "04_validation" / "report.json").is_file()
    assert (fx_dir / "scorecard.json").is_file()
    assert scorecard.overall_passed, [s.model_dump() for s in scorecard.stages]


def test_run_fixture_context_only_without_client(tmp_path):
    fx = load_all(REPO_FIXTURES)[0]
    fx_no_mock = fx.model_copy(update={"mock_responses": []})
    scorecard = run_fixture(fx_no_mock, out_dir=tmp_path)
    # context should run; generation/postprocess/validation should be marked skipped
    stages = {s.stage: s for s in scorecard.stages}
    assert "skipped" in " ".join(stages["generation"].notes)
    assert stages["context"].passed


def test_run_all_writes_summary_and_manifest(tmp_path):
    fixtures = load_all(REPO_FIXTURES)
    summary = run_all(fixtures, runs_dir=tmp_path)
    run_dir = tmp_path / summary.run_id
    assert (run_dir / "summary.json").is_file()
    assert (run_dir / "manifest.json").is_file()
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["fixture_ids"] == [f.id for f in fixtures]
    assert 0 <= summary.pass_rate <= 1


def test_audit_trail_captures_every_stage_inputs_and_outputs(tmp_path):
    fx = load_all(REPO_FIXTURES)[0]
    run_fixture(fx, out_dir=tmp_path)
    fx_dir = tmp_path / fx.id
    # context stage
    ctx_inputs = json.loads((fx_dir / "01_context" / "inputs.json").read_text())
    assert ctx_inputs["brief"]["event_id"] == "us_cpi_2026_03"
    # generation stage
    gen_trace = json.loads((fx_dir / "02_generation" / "trace.json").read_text())
    assert "model" in gen_trace and "usage" in gen_trace
    # postprocess stage
    pp_input = (fx_dir / "03_postprocess" / "input.md").read_text()
    pp_output = (fx_dir / "03_postprocess" / "output.md").read_text()
    assert "{{DISCLAIMER}}" in pp_input
    assert "{{DISCLAIMER}}" not in pp_output
    # validation stage
    val_report = json.loads((fx_dir / "04_validation" / "report.json").read_text())
    assert "validators_run" in val_report
