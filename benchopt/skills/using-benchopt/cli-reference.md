# Benchopt CLI reference

Run `benchopt <command> --help` for full option details. All commands that take
a `[BENCHMARK]` argument default to `.` (the current directory).

## Commands

### `benchopt run`
Run a benchmark. See [run.md](./run.md) for full usage.

```bash
benchopt run . -s my-solver -d Simulated -n 5 -r 3 --timeout 60
benchopt run . --config config.yml
```

Key flags: `-s/--solver`, `-d/--dataset`, `-o/--objective`, `-n/--max-runs`,
`-r/--n-repetitions`, `--timeout`, `-j/--n-jobs`, `-f/--force-solver`,
`--no-cache`, `-e/--env`, `--config`, `--pdb`, `--profile`, `--seed`.

`--collect` re-reads the cache and writes the parquet for finished cells without
running anything — use it to preview a config's run matrix or consolidate partial
results from a long run (see [run.md](./run.md)).

---

### `benchopt install`
Install solver/dataset requirements into a dedicated conda env.

```bash
benchopt install .                          # all requirements
benchopt install . -s my-solver             # one solver only
benchopt install . --env-name myenv --recreate
```

Key flags: `-s/--solver`, `-d/--dataset`, `--env-name`, `--recreate`, `--gpu`,
`--minimal` (benchopt + objective only).

---

### `benchopt test`
Run the built-in benchmark test suite (exercises `test_parameters` /
`test_config`, validates `get_data` → `set_data` → `evaluate_result` chain).

```bash
benchopt test .                         # full suite in a temp env
benchopt test . -k my-solver            # pytest -k filter
benchopt test . --skip-install          # skip conda env creation
benchopt test . --env-name bench_test_env -vl
```

---

### `benchopt prepare`
Run `Dataset.prepare()` for all (or selected) datasets — downloads, extraction,
heavy preprocessing. Idempotent; safe to re-run.

```bash
benchopt prepare .
benchopt prepare . -d my-dataset
```

---

### `benchopt info`
List solvers and datasets in a benchmark and their install requirements.
Add `-v` for parameters and availability checks; `-e` to check against the
benchmark's dedicated conda env.

```bash
benchopt info .                     # summary table
benchopt info . -s my-solver -v     # verbose solver info
benchopt info . -d "simulated" -v   # verbose dataset info (regexp supported)
benchopt info . -e                  # check availability in conda env
```

---

### `benchopt plot`
Regenerate the interactive HTML dashboard (or static figures) from a result
file. See [results.md](./results.md) for custom plots and `plot_configs`.

```bash
benchopt plot                              # latest result -> HTML
benchopt plot -f outputs/run.parquet
benchopt plot --all                        # HTML index for all runs
benchopt plot --no-html -k objective_curve # static PNGs
```

---

### `benchopt merge`
Combine multiple result parquets (e.g. from different machines or runs).
See [results.md](./results.md).

```bash
benchopt merge                             # all parquets in outputs/
benchopt merge -f a.parquet -f b.parquet -o combined
```

`--keep last` (default) keeps the newest row per unique config; `--keep all`
retains every row (e.g. to compare hardware).

---

### `benchopt publish`
Publish a result file to a sharing hub.

```bash
benchopt publish --hub github -t $BENCHOPT_GITHUB_TOKEN
benchopt publish --hub huggingface -R user/repo
```

---

### `benchopt clean`
Remove cached results and/or output files from a benchmark.

```bash
benchopt clean .                        # remove all cache + outputs
benchopt clean . -f outputs/run.parquet # remove one specific output file
```

---

### `benchopt archive`
Package a benchmark into a shareable archive (`.tar.gz`).

```bash
benchopt archive .                  # benchmark code only
benchopt archive . --with-outputs   # include outputs/ as well
```

---

### `benchopt config`
Get or set benchopt configuration values (data paths, defaults, etc.).
See the [config reference](https://benchopt.github.io/stable/user_guide/config_benchopt.html).

```bash
benchopt config get data_path
benchopt config set data_path /data/benchopt
benchopt config -b . get data_path   # benchmark-local config
```

---

### `benchopt sync-skills`
Sync benchopt's packaged agent skills into a benchmark or globally.

```bash
benchopt sync-skills --global           # install into ~/.agents/skills
benchopt sync-skills .                  # install into <benchmark>/.agents/skills
benchopt sync-skills --global --no-claude  # skip .claude/skills mirror
```

---

### `benchopt sys-info`
Print system information (CPU, RAM, OS, Python, key package versions) — useful
to attach to bug reports.

```bash
benchopt sys-info
```

---

## Doc links

- CLI reference: https://benchopt.github.io/stable/user_guide/CLI_ref.html
