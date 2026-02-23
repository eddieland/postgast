"""Smoke tests for recipebook notebooks — run each recipe via app.run()."""

from __future__ import annotations

import pytest

marimo = pytest.importorskip("marimo")


@pytest.mark.parametrize(
    "module_name",
    [
        "recipes.ast_walker",
        "recipes.batch_processing",
        "recipes.sql_transforms",
    ],
)
def test_recipe_runs(module_name: str) -> None:
    """Each recipe's marimo App runs all cells without error."""
    import importlib

    mod = importlib.import_module(module_name)
    mod.app.run()
