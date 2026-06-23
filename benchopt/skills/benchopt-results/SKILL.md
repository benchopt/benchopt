---
name: benchopt-results
description: "Explore and manage benchopt result files: read run parquets in Python (benchopt.results.read_results), understand the dataframe schema, and use the CLI (plot/merge/publish) plus the outputs/ layout. Use when analysing, slicing, comparing, or sharing benchmark results."
---

# Exploring benchopt results

Every `benchopt run` writes a self-contained result table. You can analyse it
two ways: load the parquet directly in Python (full control, custom analysis)
or use the CLI helpers (`plot`, `merge`, `publish`). Both read the same files.

## Where results live

A run produces, under `<benchmark>/outputs/`:

```
benchopt_run_<timestamp>.parquet   ← the results table (one row per curve point)
benchopt_run_<timestamp>.html      ← interactive dashboard (unless --no-html)
benchopt_run_<timestamp>/          ← per-solver run artifacts (see general.md)
```

`benchopt merge` writes `merged_results.parquet` and `benchopt plot --all`
writes `all_runs.html` covering every parquet in the folder.

## Read a result file in Python

The public entry point is `read_results` — it handles `.parquet` and `.csv`,
renames the legacy `data_name` column to `dataset_name`, and unpacks any
objective columns that were pickled at write time:

```python
from benchopt.results import read_results

df = read_results("outputs/benchopt_run_2026-06-23_11h08m26.parquet")
df.shape        # (n_points, n_columns); one row = one sampled point on a curve
```

`read_results` returns a plain `pandas.DataFrame`, so everything after is
ordinary pandas. (`pd.read_parquet` also works but skips the renaming/unpacking
above — prefer `read_results`.)

## Dataframe schema

Columns fall into four groups:

| Group | Columns | Notes |
|-------|---------|-------|
| Identity | `objective_name`, `solver_name`, `dataset_name` | Parametrized strings, e.g. `Muon[adam_lr=0.0036,...]`. `idx_rep` is the 0-based repetition; `base_seed`, `sampling_strategy`. |
| Curve | `stop_val`, `time`, `objective_value` | One row per `stop_val` (the sampled point). `time` is wall-clock seconds. `objective_value` is the main metric used for plotting. |
| Extra metrics | `objective_<name>` | One column per key returned by `Objective.evaluate_result()` (e.g. `objective_train_loss`). |
| Parameters | `p_solver_<param>`, `p_dataset_<param>`, `p_objective_<param>` | One column per parameter, split out of the parametrized name. |
| Provenance | `run_date`, `benchmark-git-tag`, `platform*`, `version-*`, `system-*`, `env-*`, `file_*` | Environment/reproducibility metadata. |

The `name` columns are convenient for grouping; the `p_*` columns are better
for filtering on a single parameter.

## Slicing common questions

```python
# Final point of each curve (largest stop_val per solver/dataset/repetition)
final = (
    df.sort_values("stop_val")
      .groupby(["dataset_name", "solver_name", "idx_rep"], as_index=False)
      .last()
)

# Best objective per solver, averaged over repetitions
final.groupby("solver_name")["objective_value"].agg(["mean", "std"])

# Filter on a single parameter instead of the full name
df[df["p_solver_adam_lr"] == 0.0036]
```

To write a (possibly filtered/merged) dataframe back out, use `save_results`,
which defaults to parquet and avoids clobbering by uniquifying the filename:

```python
from benchopt.results import save_results
save_results(final, "outputs/final_points.parquet")
```

## CLI: plot, merge, publish

Run these from the benchmark directory; with no `-f`, they pick the **latest**
result file automatically.

```bash
# Plot — interactive HTML dashboard by default
benchopt plot                      # latest run -> HTML
benchopt plot -f outputs/run.parquet
benchopt plot --all                # one HTML for all runs in outputs/
benchopt plot --no-html -k objective_curve   # static PNGs instead

# Merge several runs into one file (e.g. after adding a solver)
benchopt merge                     # all files in outputs/ -> merged_results.parquet
benchopt merge -f a.parquet -f b.parquet -o combined
#   --keep last (default) keeps one row per unique config; --keep all keeps every row

# Publish a result file to a sharing hub
benchopt publish --hub github      # needs a token (-t / BENCHOPT_GITHUB_TOKEN)
benchopt publish --hub huggingface -R user/repo
```

Plot kinds for `--kind/-k` (static plots only): `objective_curve`,
`bar_chart`, `boxplot`, `Table`. The legacy `suboptimality_curve` and
`relative_suboptimality_curve` map onto `objective_curve`. HTML plots ignore
`--kind` (they expose all kinds interactively).

## Doc links

- Managing results (merge / publish / plot): https://benchopt.github.io/benchmark_workflow/manage_benchmark_results.html
- Custom plots: https://benchopt.github.io/user_guide/add_custom_plot.html
- CLI reference: https://benchopt.github.io/user_guide/CLI_ref.html
