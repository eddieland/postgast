"""Expected output for format_sql — the "if I give A, I get B" reference.

Test cases live in YAML files under ``format_cases/``.  Each file is a list of
entries with ``label``, ``inputs`` (list of SQL strings that must all produce
the same formatted output), and ``pretty`` (the canonical formatted string).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from postgast import format_sql

from .conftest import load_yaml_cases

_CASES_DIR = Path(__file__).parent / "format_cases"


def _load_format_cases() -> list[tuple[str, str, str]]:
    """Flatten YAML entries into (label, input_sql, expected) triples.

    One triple per input string so that each variant shows up as its own test id.
    """
    cases: list[tuple[str, str, str]] = []
    for entry in load_yaml_cases(_CASES_DIR):
        label: str = entry["label"]
        pretty: str = entry["pretty"]
        inputs: list[str] = entry["inputs"]
        if len(inputs) == 1:
            cases.append((label, inputs[0], pretty))
        else:
            for idx, sql in enumerate(inputs):
                cases.append((f"{label}[{idx}]", sql, pretty))
    return cases


FORMAT_CASES = _load_format_cases()


@pytest.mark.parametrize(
    ("label", "input_sql", "expected"),
    FORMAT_CASES,
    ids=[c[0] for c in FORMAT_CASES],
)
def test_format_output(label: str, input_sql: str, expected: str) -> None:  # pyright: ignore[reportUnusedParameter]
    """format_sql(input_sql) produces exactly the expected output."""
    assert format_sql(input_sql) == expected
