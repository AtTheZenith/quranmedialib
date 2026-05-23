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
Ensure you have `uv` installed for consistent dependency management.
```bash
uv sync
```

### 2. Baseline Verification
Before starting any work, establish your performance baseline:
```bash
uv run -m pytest
uv run -m pytest -v --b
```

### 3. Implementation
- Create a descriptive feature branch.
- Follow the patterns in `AGENTS.md`.
- Add tests for any new functionality in `tests/`.

### 4. Final Quality Check
Before submitting, run the full suite:
- **Linting**: `uv run -m ruff check .`
- **Formatting**: `uv run -m ruff format .`
- **Refactoring**: `sourcery review`
- **Tests**: `uv run -m pytest -v`
- **Benchmarks**: `uv run -m pytest -v --b`

## 📝 Pull Request Guidelines

- **Atomic Changes**: Keep PRs focused on a single logical change.
- **Rationale**: Explain *why* a change was made, not just *what* was changed.
- **Verification**: Include the output of your benchmarks and tests in the PR description.

## ⚖️ License
By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
