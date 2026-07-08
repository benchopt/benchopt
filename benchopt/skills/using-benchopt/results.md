# Exploring benchopt results

Every `benchopt run` writes a self-contained result table. You can analyse it
two ways: load the parquet directly in Python (full control, custom analysis)
or use the CLI helpers (`plot`, `merge`, `publish`). Both read the same files.

## Where results live

A run produces, under `<benchmark>/outputs/`:

```
benchopt_run_<timestamp>.parquet   ← the results table (one row per curve point)
benchopt_run_<timestamp>.html      ← interactive dashboard (unless --no-html)
benchopt_run_<timestamp>/          ← per-solver run artifacts
```

`benchopt merge` writes `merged_results.parquet` and `benchopt plot --all`
writes `all_runs.html`, a table of content that allow navigating to HTML reports
for every parquet in the folder.

## Read a result file in Python

The public entry point is `read_results` — it handles `.parquet` and `.csv`,
and unpacks any objective columns that were pickled at write time (array-api
objects):

```python
from benchopt.results import read_results

df = read_results("outputs/benchopt_run_2026-06-23_11h08m26.parquet")
df.shape        # (n_points, n_columns); one row = one sampled point on a curve for a given (dataset, objective, solver, repetition).
```

`read_results` returns a plain `pandas.DataFrame`, so everything after is
ordinary pandas. (`pd.read_parquet` also works but skips the renaming/unpacking
above — prefer `read_results`.)

## Dataframe schema

Columns fall into four groups:

| Group | Columns | Notes |
|-------|---------|-------|
| Identity | `objective_name`, `solver_name`, `dataset_name` | Parametrized strings, e.g. `Muon[adam_lr=0.0036,...]`. `idx_rep` is the 0-based repetition; `base_seed`, `sampling_strategy`. |
| Curve | `stop_val`, `time`, `objective_value` | One row per `stop_val` (the sampled point). `time` is solver-only seconds (see caveat). `objective_value` is the main metric used for plotting. |
| Extra metrics | `objective_<name>` | One column per key returned by `Objective.evaluate_result()` (e.g. `objective_train_loss`). |
| Parameters | `p_solver_<param>`, `p_dataset_<param>`, `p_objective_<param>` | One column per parameter, split out of the parametrized name. |
| Provenance | `run_date`, `benchmark-git-tag`, `platform*`, `version-*`, `system-*`, `env-*`, `file_*` | Environment/reproducibility metadata. |

The `name` columns are convenient for grouping; the `p_*` columns are better
for filtering on a single parameter.

> **`time` is training-only.** benchopt pauses the solver timer while
> `Objective.evaluate_result()` runs, for both sampling strategies (callback and
> iteration). So `time` measures only the solver/training cost — evaluation and
> validation are *not* included. Don't read it as end-to-end wall-clock when
> comparing solvers whose evaluation costs differ.

## Slicing common questions

```python
# Final point of each curve (largest stop_val per solver/dataset/repetition)
final = (
    df.sort_values("stop_val")
      .groupby(["dataset_name", "solver_name", "idx_rep"], as_index=False)
      .last()
)

# Last objective per solver, averaged over repetitions
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

If `final_points.parquet` already exists, the result will be saved as
`final_points-1.parquet`, except if using `uniquify=False`.

## CLI: plot, merge, publish

Run these from the benchmark directory; with no `--file/-f`, they pick the **latest**
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

### Merging results across machines

Each run is self-contained — the parquet carries its own provenance columns
(`platform*`, `version-*`, `env-*`, `run_date`), so results produced on different
machines combine cleanly. Collect the parquets into one `outputs/` folder (or
pass them with repeated `-f`) and `benchopt merge` them:

- `--keep last` (default) keeps one row per unique configuration — re-runs of the
  same `(objective, dataset, solver)` config collapse to the newest; use
  `--keep all` to retain every machine's rows (e.g. to compare hardware).
- Identity is the parametrized config, **not** the machine, so a solver run with
  identical parameters on two machines is treated as the same config. If you want
  to keep both, add a distinguishing parameter or filter on the provenance
  columns after loading with `read_results`.
- Timings are not comparable across machines (different CPUs/BLAS); merge for
  *coverage* of configs, and compare `time` only within a machine.

## Plot kinds

Plot kinds for `--kind/-k` (static plots only): `objective_curve`,
`bar_chart`, `boxplot`, `Table`. The legacy `suboptimality_curve` and
`relative_suboptimality_curve` map onto `objective_curve`. HTML plots ignore
`--kind` (they expose all kinds interactively).

## Custom views with `plot_configs`

To pin specific plots (kind + axis scale + filters) instead of clicking through
the interactive page each time, define named **views** under `plot_configs:` in
the benchmark's config file (the same `--config config.yml` used by
`benchopt run`). Each view is a name → options:

```yaml
plot_configs:
  Subopt. (log):              # view name shown in the dashboard
    plot_kind: objective_curve
    scale: loglog
  Train score (box):
    plot_kind: boxplot
    boxplot_objective_column: objective_score_train   # kind-specific option, prefixed by kind
  Runtimes:
    plot_kind: bar_chart
```

- Common options for any kind: `plot_kind`, `scale`, `with_quantiles`,
  `suboptimal_curve`, `relative_curve`, `hidden_curves`. Kind-specific options are
  prefixed with the kind name (e.g. `boxplot_objective_column`); unspecified
  values keep the interface default.
- Fastest way to author one: build the plot interactively in the HTML page, hit
  **Save as view**, and download the config snippet — drop it into the
  benchmark's config so the view is embedded in every future plot automatically.

## Custom plots (`BasePlot`)

For visualizations the built-in kinds don't cover, add a Python file under the
benchmark's `plots/` directory with a class inheriting from `benchopt.BasePlot`:
set `name` and `type` (`scatter`/`bar_chart`/`boxplot`/`table`/`image`),
implement `plot(df, **options)` (returns data shaped by `type`) and
`get_metadata` (title/labels/scale), and use `self.get_style(label)` for a
consistent color/marker per solver. The `name` then appears in the HTML menu and
works as a `plot_kind` in `plot_configs` (above). For the per-type return schema
and a full example, see the custom-plot doc:
https://benchopt.github.io/stable/user_guide/add_custom_plot.html

## Doc links

- Managing results (merge / publish / plot): https://benchopt.github.io/stable/benchmark_workflow/manage_benchmark_results.html
- Custom plots: https://benchopt.github.io/stable/user_guide/add_custom_plot.html
- CLI reference: https://benchopt.github.io/stable/user_guide/CLI_ref.html
