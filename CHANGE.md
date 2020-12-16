### 1.1 -- in progress

- Add a `--version` option in benchopt and check that the version installed
  in conda subenv match the one in the calling process (#83)
- Change default mode to local run. Can call a run in an environment with
  option `--env` for a dedicated conda env or `--env-name ENV_NAME` to specify
  the env to use. (#94)


### 1.0 - 2020-09-25 - Release highlights

- Provide a command line interface for benchmarking optimisation algorithm
  implementations:
  - `benchopt run` to run the benchmarks
  - `benchopt plot` to display the results
  - `benchopt test` to test that a benchmark folder is correctly structured.

