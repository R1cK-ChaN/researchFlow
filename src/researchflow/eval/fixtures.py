"""Fixture loader."""

from __future__ import annotations

from pathlib import Path

import yaml

from researchflow.eval.contracts import Fixture


def load_fixture(path: Path) -> Fixture:
    """Load a fixture from a YAML file.

    If `gold_report_path` is set, resolve it relative to the fixture's
    directory and inline the text into `gold_report_inline` for
    downstream scoring convenience.
    """
    raw = yaml.safe_load(path.read_text())
    fixture = Fixture(**raw)
    if fixture.gold_report_path and not fixture.gold_report_inline:
        gold_path = path.parent / fixture.gold_report_path
        if gold_path.is_file():
            fixture.gold_report_inline = gold_path.read_text()
    return fixture


def load_all(fixtures_dir: Path) -> list[Fixture]:
    """Load every `fixture.yaml` under `fixtures_dir`, sorted by fixture id."""
    fixtures: list[Fixture] = []
    for yaml_path in sorted(fixtures_dir.rglob("fixture.yaml")):
        fixtures.append(load_fixture(yaml_path))
    fixtures.sort(key=lambda f: f.id)
    return fixtures
