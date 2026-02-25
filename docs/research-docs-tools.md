# Sphinx / Read the Docs: Configuration & Plugin Research

Research into Sphinx themes, extensions, and Read the Docs configuration for postgast, drawing on current best practices
and real configurations from professional OSS Python projects.

## Current postgast Setup

**Theme:** Furo **Extensions:** autodoc, intersphinx, napoleon, viewcode, sphinx-autodoc-typehints, sphinx-copybutton
**RTD:** Ubuntu 24.04, Python 3.12, uv-based install **Docs deps:** sphinx>=8.0, furo>=2024.8, sphinx-copybutton>=0.5,
sphinx-autodoc-typehints>=2.0

This is already a solid foundation. The recommendations below focus on what to *add* or *consider*.

______________________________________________________________________

## 1. Theme Comparison

### Furo (current) — Recommended, keep it

| Aspect          | Details                                       |
| --------------- | --------------------------------------------- |
| Used by         | attrs, psycopg, pip, Flask, Black, Jinja      |
| Light/dark mode | Built-in toggle, no config needed             |
| Responsive      | Excellent mobile support                      |
| Customization   | CSS variables, custom fonts, light/dark logos |
| Maintenance     | Actively maintained by Pradyun Gedam          |
| Search          | Good built-in search UX                       |

**Verdict:** Furo is the dominant choice for modern Python libraries. No reason to switch.

### Alternatives considered

| Theme                   | Pros                                         | Cons                             | Used by                       |
| ----------------------- | -------------------------------------------- | -------------------------------- | ----------------------------- |
| **pydata-sphinx-theme** | Great for data/science projects, navbar tabs | Heavier, more complex config     | pandas, NumPy, SciPy, Jupyter |
| **sphinx-book-theme**   | Jupyter Book integration, sidebar TOC        | Data-science oriented            | Jupyter Book, MyST docs       |
| **sphinx-rtd-theme**    | Classic, widely recognized                   | Dated look, no dark mode         | Rich, older projects          |
| **Material (MkDocs)**   | Polished, search, versioning                 | Requires leaving Sphinx entirely | pydantic, httpx, FastAPI      |

### Furo Customization Ideas (from attrs, psycopg)

```python
# Custom fonts (attrs uses Inter + BerkeleyMono)
html_theme_options = {
    "light_css_variables": {
        "font-stack": "Inter, sans-serif",
        "font-stack--monospace": "BerkeleyMono, Menlo, monospace",
    },
    "light_logo": "postgast-light.svg",
    "dark_logo": "postgast-dark.svg",
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
}
```

______________________________________________________________________

## 2. Extensions to Consider Adding

### High Priority

#### `myst-parser` — Write docs in Markdown

- Used by: attrs, many modern projects
- Lets you write `.md` files alongside `.rst` in `docs/`
- Supports directives via `{directive}` colon-fence syntax
- postgast's CLAUDE.md and README.md are already Markdown — consistency argument

````python
extensions = [
    # ... existing ...
    "myst_parser",
]
myst_enable_extensions = [
    "colon_fence",  # ```{directive} syntax
    "smartquotes",  # Typographic quotes
    "deflist",  # Definition lists
    "fieldlist",  # :field: syntax
]
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
````

**Dependency:** `myst-parser>=3.0`

**Trade-off:** Adds a dependency and dual-format source. Only worth it if you plan to write new docs in Markdown. The
existing .rst files work fine as-is.

#### `notfound.extension` — Custom 404 page

- Used by: attrs
- Shows a styled 404 page on Read the Docs instead of a generic error
- Zero config needed

```python
extensions = [
    # ... existing ...
    "notfound.extension",
]
```

**Dependency:** `sphinx-notfound-page>=1.0`

#### `sphinx.ext.doctest` — Testable documentation examples

- Used by: attrs, SQLAlchemy
- Runs code examples in docs as tests during CI
- Catches stale examples that no longer work
- postgast's `examples.rst` has 500+ lines of code — keeping them tested is valuable

```python
extensions = [
    # ... existing ...
    "sphinx.ext.doctest",
]
doctest_global_setup = """
import postgast
from postgast import parse, deparse, normalize, fingerprint, split, scan
"""
```

**Dependency:** Built into Sphinx (free). Requires a `make doctest` target.

### Medium Priority

#### `sphinx-design` — Tabs, cards, grids, badges

- Modern UI components for docs (tabbed code examples, feature cards)
- Good for showing Python version differences or alternative approaches

```python
extensions = [
    # ... existing ...
    "sphinx_design",
]
```

**Dependency:** `sphinx-design>=0.6`

#### `sphinxcontrib-towncrier` — Automated changelog

- Used by: attrs
- Generates changelog from fragment files in `changes/` directory
- Each PR adds a small text file; towncrier assembles them at release time
- Prevents merge conflicts in CHANGELOG.md

**Dependency:** `sphinxcontrib-towncrier>=0.4`, plus `towncrier` as a dev dep.

**Trade-off:** Only valuable once there are regular contributors. Overkill for solo/small-team projects.

#### `sphinx_paramlinks` — Deep-linkable parameters

- Used by: SQLAlchemy
- Makes each function parameter a clickable anchor (`#parse-params-source`)
- Useful for linking to specific parameters from issues/discussions

**Dependency:** `sphinx-paramlinks>=0.6`

### Lower Priority / Niche

| Extension                     | What it does                                    | Used by       | Worth it?                                      |
| ----------------------------- | ----------------------------------------------- | ------------- | ---------------------------------------------- |
| `sphinx.ext.todo`             | `.. todo::` directives for WIP docs             | attrs         | Maybe — lightweight                            |
| `sphinx.ext.autosectionlabel` | Auto-generate labels for all sections           | Rich          | Convenient but can cause label collisions      |
| `sphinx-autoapi`              | Alternative to autodoc, no import needed        | Read the Docs | Not needed — autodoc + mock imports works fine |
| `sphinxcontrib.mermaid`       | Mermaid diagrams in docs                        | Various       | Nice for architecture diagrams                 |
| `sphinx-tabs`                 | Tabbed content (superseded by sphinx-design)    | Various       | Use sphinx-design instead                      |
| `sphinx-prompt`               | Non-copyable `$` prompts in shell examples      | Various       | sphinx-copybutton handles this                 |
| `linkcode`                    | Link to source on GitHub (vs viewcode's inline) | Various       | viewcode is simpler                            |

______________________________________________________________________

## 3. Read the Docs Configuration

### Current config is good. Possible improvements:

#### Add fail_on_warning for stricter builds

```yaml
sphinx:
  configuration: docs/conf.py
  fail_on_warning: true   # Catch broken cross-references, etc.
```

#### Pin uv version for reproducibility

```yaml
jobs:
  pre_create_environment:
    - asdf plugin add uv
    - asdf install uv 0.6.3    # pin instead of 'latest'
    - asdf global uv 0.6.3
```

#### Add search ranking (RTD feature)

Read the Docs supports `search.ranking` in conf.py to boost/demote pages:

```python
html_context = {
    "display_github": True,
    "github_user": "eddieland",
    "github_repo": "postgast",
    "github_version": "main",
    "conf_py_path": "/docs/",
}
```

#### Build docs in CI too

Add a CI step that builds docs and checks for warnings (many projects do this):

```yaml
# In .github/workflows/ci.yml
- name: Build docs
  run: uv run --group docs sphinx-build -W -b html docs docs/_build/html
```

The `-W` flag turns warnings into errors — catches broken references before merge.

______________________________________________________________________

## 4. Professional OSS Project Configurations

### attrs (closest model for postgast)

**Why it's a good model:** Small-to-medium Python library, Furo theme, similar scope.

| Setting    | Value                                                                           |
| ---------- | ------------------------------------------------------------------------------- |
| Theme      | Furo with custom fonts (Inter, BerkeleyMono)                                    |
| Extensions | myst_parser, napoleon, autodoc, doctest, intersphinx, todo, notfound, towncrier |
| RTD        | Ubuntu LTS, Python 3.13, uv via asdf                                            |
| Special    | Towncrier changelog, custom light/dark logos, link checking config              |

**Takeaways:**

- myst_parser with colon_fence, smartquotes, deflist extensions
- notfound.extension for 404 pages
- Link checking with ignored patterns (PyPI, GitHub rate limits)
- `nitpick_ignore` for known false-positive cross-reference warnings

### psycopg (closest domain match)

**Why it's relevant:** PostgreSQL Python library, similar audience.

| Setting    | Value                                                                                    |
| ---------- | ---------------------------------------------------------------------------------------- |
| Theme      | Furo with custom CSS and SVG logo                                                        |
| Extensions | autodoc, intersphinx, custom roles (sql_role, ticket_role, libpq_docs)                   |
| RTD        | Standard config                                                                          |
| Special    | Custom Sphinx extensions for SQL syntax highlighting and PostgreSQL doc cross-references |

**Takeaways:**

- Custom Sphinx roles for SQL syntax (`:sql:`) — could be useful for postgast examples
- Intersphinx mapping to PostgreSQL docs
- `default_role = "obj"` for cleaner inline markup
- Source-order member display (postgast already does this)

### SQLAlchemy (gold standard for API docs)

| Setting    | Value                                                                  |
| ---------- | ---------------------------------------------------------------------- |
| Theme      | Custom zzzeeksphinx (purpose-built)                                    |
| Extensions | autodoc, zzzeeksphinx, changelog, sphinx_paramlinks, sphinx_copybutton |
| Special    | Module name mapping for clean public API display                       |

**Takeaways:**

- `sphinx_paramlinks` for deep-linkable function parameters
- Extensive `autodocmods_convert_modname` to present `sqlalchemy.Column` even when the real module is
  `sqlalchemy.sql.schema`
- Changelog integration directly in docs

### Rich (simple but effective)

| Setting    | Value                                                                         |
| ---------- | ----------------------------------------------------------------------------- |
| Theme      | sphinx_rtd_theme (older choice)                                               |
| Extensions | autodoc, viewcode, napoleon, intersphinx, autosectionlabel, sphinx_copybutton |

**Takeaways:**

- Minimal setup that works well
- Custom CSS for Fira Code font in code blocks
- autosectionlabel for easy cross-referencing

### pydantic & httpx (MkDocs comparison)

Both use **MkDocs Material** instead of Sphinx. Key features they get:

- Instant navigation with prefetch
- Algolia search integration
- mike for multi-version docs
- Social media card generation
- Stricter validation (broken link detection)

**Verdict for postgast:** Sphinx + Furo is the right choice. MkDocs Material is more polished visually but requires
abandoning the Sphinx ecosystem (autodoc, intersphinx, napoleon). The migration cost isn't justified for postgast's
current size.

______________________________________________________________________

## 5. Recommended Action Plan

### Immediate (low effort, high value)

1. **Add `notfound.extension`** — 1 line in conf.py, 1 dep
1. **Add `sphinx.ext.doctest`** — free, keeps examples tested
1. **Add `fail_on_warning: true`** in `.readthedocs.yaml`
1. **Add `html_context`** for GitHub edit links in Furo
1. **Add docs build to CI** with `-W` flag

### Short-term (moderate effort)

6. **Add `myst-parser`** if planning to write new docs in Markdown
1. **Add `sphinx-design`** for tabbed examples (e.g., show sync vs async patterns)
1. **Add custom light/dark logos** to Furo theme options
1. **Configure link checking** with `linkcheck_ignore` patterns

### Long-term (if/when needed)

10. **Add `towncrier`** once there are multiple contributors
01. **Add custom Sphinx roles** for SQL syntax highlighting (like psycopg)
01. **Add `sphinx_paramlinks`** for deep-linkable API parameters
01. **Consider versioned docs** via RTD's built-in versioning

______________________________________________________________________

## 6. Recommended conf.py Additions

If all "immediate" items are adopted, the extensions block would look like:

```python
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "notfound.extension",
]

# Doctest
doctest_global_setup = """
import postgast
from postgast import parse, deparse, normalize, fingerprint, split, scan
"""

# GitHub context for Furo "Edit on GitHub" links
html_context = {
    "display_github": True,
    "github_user": "eddieland",
    "github_repo": "postgast",
    "github_version": "main",
    "conf_py_path": "/docs/",
}
```

Updated docs deps in `pyproject.toml`:

```toml
docs = [
    "sphinx>=8.0",
    "furo>=2024.8",
    "sphinx-copybutton>=0.5",
    "sphinx-autodoc-typehints>=2.0",
    "sphinx-notfound-page>=1.0",
]
```
