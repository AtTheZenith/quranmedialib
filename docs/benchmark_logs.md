# Benchmark Logs

Cross-version log of the `quranmedialib.check` benchmark suite. Per-version tables live in each `changelog/vX.Y.Z.md` under `## Benchmark History`; this file is the cross-version summary.

## Method

- **Capture**: `uv run -m quranmedialib.check benchmark --json` in a worktree checked out at the release tag. Best-of-5 raw runs saved to `output/bench_vX.Y.Z_rN.json` (gitignored).
- **Aggregation**: best-of-N collapses each run's per-scenario elapsed times into one `output/bench_vX.Y.Z_best.json`. Tooling: `output/aggregate_bench.py`, `output/gen_changelog_sections.py`.
- **Headline metric**: best run total = the minimum of full-suite run totals (a real run), never the sum of per-scenario bests.
- **Comparability**: metrics are only meaningful across versions measured on the same host, same user, same date window. Do not read cross-version deltas below ~10% as regressions.

## Results

Single host, single user, single date window (2026-08-13, best-of-5).

| Version | Suite size | Best total (s) | Run totals (s) | Peak RSS (MB) | Headline Al-Baqarah (s) |
| :------ | :--------- | -------------: | :------------- | ------------: | ----------------------: |
| v4.1.0  | 21         | 7.61           | [8.18, 8.00, 8.11, 7.61, 8.58] | 42.0          | **6.971** (473 pages)   |
| v4.1.1  | 35         | 8.17           | [8.17, 8.33, 8.19, 8.25, 8.36] | 43.1          | **7.418** (473 pages)   |
| v4.2.0  | 35         | 6.88           | [6.99, 6.89, 6.88, 7.00, 8.54] | 43.6          | **5.945** (473 pages)   |

No version is measurably faster than another at this sample size. A best-of-3 capture ranked v4.1.0 fastest (6.50s) and v4.2.0 slowest (11.07s); the best-of-5 re-run reversed it (v4.2.0 6.88s, v4.1.0 7.61s). The ordering is noise, not signal.

## Notes

- The suite is dominated by the Al-Baqarah full-surah render (~473 pages, roughly 90% of total time); every other scenario is sub-100ms.
- Peak RSS is consistently ~42–43MB across all versions — the memory surface is stable.
- SHA-256 hashes are only computed during `check update` from saved files, never inside the measured benchmark loop.
