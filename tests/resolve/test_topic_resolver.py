from __future__ import annotations

from pathlib import Path

from researchflow.resolve import LocalRegistry, TopicResolver


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
            },
            {
                "topic": "us nfp april 2026",
                "brief": {
                    "event_id": "us_nfp_2026_04",
                    "event_name": "US NFP — April 2026",
                    "release_time": "2026-05-02T08:30:00+00:00",
                    "report_type": "us_nfp",
                },
            },
        ]
    )


def test_exact_topic_match_returns_brief():
    r = TopicResolver(_registry())
    result = r.resolve("US CPI March 2026")
    assert result.brief is not None
    assert result.brief.event_id == "us_cpi_2026_03"
    assert result.confidence == 1.0
    assert result.source == "local_registry"


def test_whitespace_and_case_normalised():
    r = TopicResolver(_registry())
    result = r.resolve("  us   CPI  March  2026 ")
    assert result.brief is not None


def test_unknown_topic_returns_candidates():
    r = TopicResolver(_registry())
    result = r.resolve("us cpi january 2027")
    assert result.brief is None
    assert "us cpi march 2026" in result.candidates


def test_empty_topic_returns_all_candidates():
    r = TopicResolver(_registry())
    result = r.resolve("")
    assert result.brief is None
    assert set(result.candidates) == {"us cpi march 2026", "us nfp april 2026"}


def test_from_yaml_loads_repo_default(tmp_path):
    yaml_path = tmp_path / "topics.yaml"
    yaml_path.write_text(
        """
- topic: "foo bar"
  brief:
    event_id: e1
    event_name: e1
    release_time: "2026-01-01T00:00:00+00:00"
    report_type: us_cpi
"""
    )
    registry = LocalRegistry.from_yaml(yaml_path)
    r = TopicResolver(registry)
    assert r.resolve("foo bar").brief is not None


def test_from_yaml_missing_file_empty():
    registry = LocalRegistry.from_yaml(Path("/does/not/exist.yaml"))
    r = TopicResolver(registry)
    assert r.resolve("any").brief is None
    assert r.resolve("any").candidates == []
