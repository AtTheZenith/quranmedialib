# Benchmark Logs

Cross-version log of the `quranmedialib.check` benchmark suite. Per-version tables live in each `changelog/vX.Y.Z.md` under `## Benchmark History`; this file is the cross-version summary.

## Benchmark Procedure

- Run `uv run -m quranmedialib.check benchmark --json` in a worktree at each release tag.
- Capture best-of-5 raw runs to `output/bench_vX.Y.Z_rN.json` (gitignored).
- Headline metric is the fastest full-suite run (min of run totals), not the sum of per-scenario bests.
- Al-Baqarah is the perf-regression scenario (~473 pages, ~90% of suite time).
- Rows are comparable only across the same host, user, and date window; deltas below ~10% carry no signal.
- Tooling: `output/aggregate_bench.py`, `output/gen_changelog_sections.py`.

## User Benchmarks

### zenith

| Version | Total runtime (s) | Al-Baqarah (s) |
| :------ | ----------------: | -------------: |
| v5.0.0  | 7.20              | 6.148          |
| v4.2.0  | 6.88              | 5.945          |
| v4.1.1  | 8.17              | 7.418          |
| v4.1.0  | 7.61              | 6.971          |

> v5.0.0 adds two sidecar scenarios (`surah_kawthar_sidecar`, `range_kawthar_sidecar`), so its 37-scenario suite is not directly comparable to the 35-scenario v4.2.0 total; the Al-Baqarah headline (unchanged 473 pages) is the apples-to-apples metric.
