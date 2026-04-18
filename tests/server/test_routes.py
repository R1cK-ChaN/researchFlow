from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from researchflow.clients.house_view import HouseViewLoader
from researchflow.context.contracts import Brief
from researchflow.eval.mock_client import QueueClient
from researchflow.resolve import LocalRegistry, TopicResolver
from researchflow.server.config import Settings
from researchflow.server.main import Dependencies, create_app


def _registry() -> LocalRegistry:
    return LocalRegistry(
        [
            {
                "topic": "us cpi march 2026",
                "brief": {
                    "event_id": "us_cpi_2026_03",
                    "event_name": "US CPI — March 2026",
                    "release_time": "2026-04-10T08:30:00+00:00",
                    "report_type": "us_cpi",
                },
            }
        ]
    )


def _fake_data_client() -> MagicMock:
    m = MagicMock()
    m.fetch_data_pack.return_value = _datapack()
    return m


def _fake_rag_client() -> MagicMock:
    m = MagicMock()
    m.fetch_material_pack.return_value = _materialpack()
    return m


def _datapack():
    from researchflow.context.contracts import DataPack

    return DataPack(
        event_id="us_cpi_2026_03",
        payload={
            "facts": [
                {
                    "id": "F-CPI-HEAD-YOY",
                    "label": "Headline CPI YoY",
                    "unit": "%",
                    "actual": 3.1,
                    "consensus": 3.2,
                    "prior": 3.0,
                    "tier": 1,
                }
            ]
        },
    )


def _materialpack():
    from researchflow.context.contracts import MaterialPack

    return MaterialPack(event_id="us_cpi_2026_03", payload={"evidence": []})


def _generator_output() -> str:
    body = "word " * 70
    return (
        "## Bottom line\nHeadline slipped to 3.1% [F-CPI-HEAD-YOY]. " + body + "\n\n"
        "## What happened\n" + body + "\n\n"
        "## What it means\n" + body + "\n\n"
        "{{DISCLAIMER}}"
    )


def _build_client(
    tmp_path: Path,
    *,
    api_token: str | None = None,
    topic_resolver: TopicResolver | None = None,
    data_client=None,
    rag_client=None,
    llm_responses: list[str] | None = None,
):
    (tmp_path / "runs").mkdir()
    (tmp_path / "house_view.yaml").write_text(
        'version: "v1"\nas_of: "2026-04-15T00:00:00+00:00"\n'
        'content:\n  base_case: "x"\n  tone_lean: dovish\n'
    )
    settings = Settings(
        _env_file=None,
        RESEARCHFLOW_API_TOKEN=api_token,
        RESEARCHFLOW_RUNS_DIR=str(tmp_path / "runs"),
        HOUSE_VIEW_PATH=str(tmp_path / "house_view.yaml"),
        FRAMEWORK_DIR=str(tmp_path / "frameworks"),
        EXEMPLAR_DIR=str(tmp_path / "exemplars"),
    )
    queue = QueueClient(llm_responses or [])
    deps = Dependencies(
        settings=settings,
        topic_resolver=topic_resolver or TopicResolver(_registry()),
        data_client=data_client,
        rag_client=rag_client,
        house_view_loader=HouseViewLoader(settings.house_view_path),
        generator_client=queue,
        judge_client=queue,
        runs_dir=Path(settings.runs_dir),
        disclaimer="TEST_DISCLAIMER",
    )
    app = create_app(settings=settings, deps=deps)
    return TestClient(app), deps


def test_health(tmp_path):
    client, _ = _build_client(tmp_path)
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "openrouter" in body["dependencies"]


def test_recipes_lists_packaged(tmp_path):
    client, _ = _build_client(tmp_path)
    r = client.get("/v1/recipes")
    assert r.status_code == 200
    assert set(r.json()["recipes"]) >= {"brief_comment", "deep_research", "trading_daily"}


def test_resolve_endpoint_match(tmp_path):
    client, _ = _build_client(tmp_path)
    r = client.post("/v1/topics/resolve", json={"topic": "US CPI March 2026"})
    assert r.status_code == 200
    body = r.json()
    assert body["brief"]["event_id"] == "us_cpi_2026_03"
    assert body["confidence"] == 1.0


def test_resolve_endpoint_unknown_returns_candidates(tmp_path):
    client, _ = _build_client(tmp_path)
    r = client.post("/v1/topics/resolve", json={"topic": "unknown topic"})
    assert r.status_code == 200
    body = r.json()
    assert body["brief"] is None


def test_research_with_topic_full_flow(tmp_path):
    client, deps = _build_client(
        tmp_path,
        data_client=_fake_data_client(),
        rag_client=_fake_rag_client(),
        llm_responses=[_generator_output(), '{"violations": []}'],
    )
    r = client.post(
        "/v1/research",
        json={
            "topic": "US CPI March 2026",
            "recipe": "brief_comment",
            "params": {"language": "en", "reader_tier": "pm"},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["resolved_brief"]["event_id"] == "us_cpi_2026_03"
    assert body["validation"]["passed"] is True
    run_id = body["run_id"]
    # Artifacts written to disk.
    run_dir = deps.runs_dir / run_id
    assert (run_dir / "01_context" / "output.xml").is_file()
    assert (run_dir / "02_generation" / "output.md").is_file()
    assert (run_dir / "04_validation" / "report.json").is_file()
    assert (run_dir / "flow_summary.json").is_file()


def test_research_unknown_topic_400(tmp_path):
    client, _ = _build_client(
        tmp_path,
        data_client=_fake_data_client(),
        rag_client=_fake_rag_client(),
    )
    r = client.post(
        "/v1/research",
        json={"topic": "complete nonsense", "recipe": "brief_comment"},
    )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["message"] == "topic not recognised"
    assert "candidates" in detail


def test_research_with_inputs_override_skips_resolution(tmp_path):
    client, deps = _build_client(
        tmp_path,
        llm_responses=[_generator_output(), '{"violations": []}'],
    )
    inputs = {
        "brief": {
            "event_id": "e1",
            "event_name": "e1",
            "release_time": "2026-04-10T08:30:00+00:00",
            "report_type": "us_cpi",
        },
        "data_pack": {
            "event_id": "e1",
            "payload": {
                "facts": [
                    {
                        "id": "F-CPI-HEAD-YOY",
                        "actual": 3.1,
                        "consensus": 3.2,
                        "prior": 3.0,
                        "tier": 1,
                    }
                ]
            },
        },
        "house_view": {
            "version": "v",
            "as_of": "2026-04-15T00:00:00+00:00",
            "content": {"base_case": "x"},
        },
        "extras": {"framework": {}, "exemplar_pool": []},
    }
    r = client.post(
        "/v1/research",
        json={
            "topic": "n/a",
            "recipe": "brief_comment",
            "inputs_override": inputs,
        },
    )
    assert r.status_code == 200, r.text
    # Data + RAG clients weren't configured but the route skipped them.
    assert r.json()["resolved_brief"]["event_id"] == "e1"


def test_research_503_when_no_llm_client(tmp_path):
    # Build with no LLM responses — generator_client is a QueueClient but we
    # simulate "no client" via manual override.
    client, deps = _build_client(tmp_path)
    deps.generator_client = None
    r = client.post(
        "/v1/research",
        json={"topic": "US CPI March 2026", "recipe": "brief_comment"},
    )
    assert r.status_code == 503


def test_auth_required_when_token_configured(tmp_path):
    client, _ = _build_client(tmp_path, api_token="secret")
    r = client.get("/v1/recipes")
    assert r.status_code == 401
    r = client.get("/v1/recipes", headers={"Authorization": "Bearer secret"})
    assert r.status_code == 200


def test_get_run_artifact_reads_back(tmp_path):
    client, deps = _build_client(
        tmp_path,
        data_client=_fake_data_client(),
        rag_client=_fake_rag_client(),
        llm_responses=[_generator_output(), '{"violations": []}'],
    )
    create = client.post(
        "/v1/research",
        json={"topic": "US CPI March 2026", "recipe": "brief_comment"},
    )
    run_id = create.json()["run_id"]
    r = client.get(f"/v1/research/runs/{run_id}")
    assert r.status_code == 200
    assert r.json()["run_id"] == run_id

    r = client.get(f"/v1/research/runs/{run_id}/02_generation/output.md")
    assert r.status_code == 200
    assert "Bottom line" in r.text


def test_artifact_path_traversal_rejected(tmp_path):
    client, _ = _build_client(tmp_path)
    r = client.get("/v1/research/runs/xyz/01_context/../../../etc/passwd")
    # FastAPI / Starlette collapses the path; the resulting filename fails
    # whitelist checks regardless of how it's parsed.
    assert r.status_code in (404, 400)


def test_artifact_unknown_stage_rejected(tmp_path):
    client, deps = _build_client(
        tmp_path,
        data_client=_fake_data_client(),
        rag_client=_fake_rag_client(),
        llm_responses=[_generator_output(), '{"violations": []}'],
    )
    create = client.post(
        "/v1/research",
        json={"topic": "US CPI March 2026", "recipe": "brief_comment"},
    )
    run_id = create.json()["run_id"]
    r = client.get(f"/v1/research/runs/{run_id}/99_evil/output.md")
    assert r.status_code == 404
