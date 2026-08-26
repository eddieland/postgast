# Contributing to postgast

Thanks for your interest in contributing. This guide describes how to build postgast, how to run its checks, and how to
open a pull request.

## Getting Started

1. **Fork** the repository on GitHub and clone your fork:

   ```bash
   git clone https://github.com/<your-username>/postgast.git
   cd postgast
   git remote add upstream https://github.com/eddieland/postgast.git
   ```

1. **Install dependencies** ([uv](https://docs.astral.sh/uv/) is required):

   ```bash
   make install
   ```

1. **Build the native library** (compiles the vendored `libpg_query` shared library):

   ```bash
   make build-native
   ```

1. **Run the tests** to confirm that the build works:

   ```bash
   make test-unit
   ```

## Development Workflow

Create a branch for your change:

```bash
git checkout -b my-feature upstream/main
```

### Running Checks

```bash
make fmt          # Autoformat (mdformat, codespell, ruff)
make lint         # Format + type-check (basedpyright)
make test-unit    # Unit tests (no Docker)
make test         # All tests including integration (requires Docker)
make all          # install + lint + test
```

Run a single test:

```bash
uv run pytest tests/test_foo.py::test_bar -v
```

### Code Style

- **Formatter/Linter**: [Ruff](https://docs.astral.sh/ruff/) (line-length 120, Google-style docstrings)
- **Type checker**: [BasedPyright](https://docs.basedpyright.com/)
- **Spell checker**: [codespell](https://github.com/codespell-project/codespell)
- **Markdown formatter**: [mdformat](https://github.com/executablebooks/mdformat)
- Minimum Python version: 3.10

`make fmt` fixes most formatting problems. CI runs the same checks. Run `make lint` on your machine before you push to
find problems early.

## Submitting a Pull Request

1. Confirm that `make lint` and `make test-unit` pass on your machine.
1. Keep each commit focused on one logical change.
1. Push your branch and open a pull request against `main`.
1. Describe **what** your change does and **why** in the pull request description.

CI runs the formatter, the linter, the type checker, and the tests on your pull request.

## Reporting Issues

Open an issue on [GitHub Issues](https://github.com/eddieland/postgast/issues). Include:

- What you expected to happen
- What actually happened
- A minimal SQL snippet or code example to reproduce the issue
- Your Python version and OS

## License

If you contribute, you license your contribution under the [BSD 2-Clause License](LICENSE).
