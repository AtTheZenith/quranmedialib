# Contributing to QuranMediaLib

Thank you for your interest in contributing to QuranMediaLib! We aim to maintain a professional, high-performance library. To ensure the longevity and stability of the codebase, we adhere to a strict set of engineering standards.

## Technical Bar

Before you submit a Pull Request, please familiarize yourself with our **Repository Style Guide** in [`AGENTS.md`](AGENTS.md).

We treat our code as a professional asset. We prioritize:
- **Correctness First**: All tests must pass.
- **Performance Baselines**: No regressions in benchmark speed.
- **Zero Astonishment**: Obvious, boring code is preferred over clever hacks.
- **Type Safety**: Strict use of Python 3.13 type hints and `Final` for constants.

## Contribution Workflow

### 1. Setup Your Environment
Ensure you have `uv` installed for consistent dependency management. `uv sync` installs the project plus the dev toolchain (`ruff`, `pytest`, `psutil`).
```bash
uv sync
```

### 2. Install Git Hooks (recommended)
The repo ships quality-gate hooks in `.githooks/`. Enable them once:
```bash
git config core.hooksPath .githooks
```
- `commit-msg` — enforces Conventional Commits (see `AGENTS.md` section 21).
- `pre-commit` — runs `ruff check` on staged Python files.
- `pre-push` — runs `ruff check` on the full tree, markdown lint (`pymarkdownlnt`), plus `quranmedialib.check test --unit` (unit tests only; pixel validation and benchmarks are excluded).

Bypass on demand with `--no-verify` or `SKIP_QC=1`. On Windows (git-bash), ensure `uv` is on the PATH the hooks inherit.

> **Pixel validation is developer-local.** Golden reference images are not tracked (see `.gitignore`), so CI and the pre-push hook do not gate on them. Run `uv run -m quranmedialib.check test` locally, and regenerate refs with `uv run -m quranmedialib.check update` whenever an intentional rendering change lands.

### 3. Baseline Verification
Before starting any work, establish your performance baseline:
```bash
uv run -m pytest
uv run -m pytest -v --b
```

### 4. Implementation
- Create a descriptive feature branch.
- Follow the patterns in `AGENTS.md`.
- Add tests for any new functionality in `tests/`.

### 5. Final Quality Check
Before submitting, run the full suite:
- **Linting**: `uv run ruff check src/ tests/ demo.py`
- **Formatting**: `uv run ruff format src/ tests/ demo.py`
- **Refactoring**: `uvx sourcery review .`
- **Tests**: `uv run -m quranmedialib.check test --unit`
- **Benchmarks**: `uv run -m pytest -v --b`

## 📝 Pull Request Guidelines

- **Atomic Changes**: Keep PRs focused on a single logical change.
- **Rationale**: Explain *why* a change was made, not just *what* was changed.
- **Verification**: Include the output of your benchmarks and tests in the PR description.

## ⚖️ License
By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
