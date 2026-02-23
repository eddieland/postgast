## 1. Fix recipe bugs

- [ ] 1.1 Fix `find_nodes` calls in `recipes/ast_walker.py` — pass protobuf message types instead of strings
- [ ] 1.2 Fix `find_nodes` calls in `recipes/batch_processing.py` — same fix
- [ ] 1.3 Fix `find_nodes` calls in `recipes/sql_transforms.py` — same fix
- [ ] 1.4 Verify all three recipes run successfully via `app.run()`

## 2. Add recipe smoke test

- [ ] 2.1 Create `tests/postgast/test_recipes.py` with `pytest.importorskip("marimo")` and parametrized test over recipe
  modules
- [ ] 2.2 Run `uv run --extra recipes pytest tests/postgast/test_recipes.py -v` — all three pass

## 3. Update CI

- [ ] 3.1 Update `.github/workflows/ci.yml` test job to install with `--extra recipes`
- [ ] 3.2 Verify `make lint` passes (no type errors or lint issues)
- [ ] 3.3 Verify `make test` passes (recipe tests skipped without marimo, rest pass)
