from __future__ import annotations

from pathlib import Path

from researchflow.eval.fixtures import load_all, load_fixture

REPO_FIXTURES = Path(__file__).resolve().parents[2] / "eval" / "fixtures"


def test_load_sample_fixture():
    fx = load_fixture(REPO_FIXTURES / "us_cpi_2026_03" / "fixture.yaml")
    assert fx.id == "us_cpi_2026_03"
    assert fx.recipe == "brief_comment"
    assert fx.expected.context["blocks_rendered"][0] == "brief"
    assert len(fx.mock_responses) == 3


def test_load_all_sorted_by_id():
    fxs = load_all(REPO_FIXTURES)
    assert fxs
    assert [f.id for f in fxs] == sorted(f.id for f in fxs)
