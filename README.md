## Benchmark repository for optimization

[![Build Status](https://dev.azure.com/benchopt/benchopt/_apis/build/status/benchopt.benchOpt?branchName=master)](https://dev.azure.com/benchopt/benchopt/_build/latest?definitionId=1&branchName=master)
[![Python 3.6+](https://img.shields.io/badge/python-3.6%2B-blue)](https://www.python.org/downloads/release/python-360/)
[![codecov](https://codecov.io/gh/benchopt/benchOpt/branch/master/graph/badge.svg)](https://codecov.io/gh/benchopt/benchOpt)

The goal of this project is to benchmark implementation of optimization methods on several classical problems.


Install
--------

This package can be install through `pip` using

```
$ pip install -U https://api.github.com/repos/benchopt/benchOpt/zipball/master
```

Usage
-----

The `benchopt` command line tool is based on `click`. To run Lasso benchmarks on all datasets and with all solvers, run:

```
benchopt run lasso
```

Apart from the problem (e.g. Lasso or Logreg), options can be passed to `benchopt run`, to restrict the benchmarks to some solvers or datasets, e.g.:

```
benchopt run lasso -s sklearn -s baseline -d boston --max-samples 10 --repetition 10
```

Use `benchopt run -h` for more details about these options, or visit https://benchopt.github.io/api.html.



List of optimization problems available
---------------------------------------------------

- `lasso`: aka l1-regularized least-squares. This consists in solving the following program:

```min_w (1 / (2 * n_samples)) * ||y - Xw||^2_2 + alpha * ||w||_1```

-`logreg`: aka l1-regularized logistic regression. This consists in solving the following program
```min_w \sum_i (1 + np.exp(-y_i X_{i,:} w)) + alpha * ||w||_1```

-`nnls`: aka non-negative least-squares. This consists in solving the following program:
```min_{w >=0} (1 / (2 * n_samples)) * ||y - Xw||^2_2```
