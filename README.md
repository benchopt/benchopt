## Benchmark repo for optimization

[![Build Status](https://dev.azure.com/benchopt/benchopt/_apis/build/status/benchopt.benchOpt?branchName=master)](https://dev.azure.com/benchopt/benchopt/_build/latest?definitionId=1&branchName=master)
[![Python 3.6+](https://img.shields.io/badge/python-3.6%2B-blue)](https://www.python.org/downloads/release/python-360/)
[![codecov](https://codecov.io/gh/benchopt/benchOpt/branch/master/graph/badge.svg)](https://codecov.io/gh/benchopt/benchOpt)

The goal of this project is to benchmark implementation of optimization methods on several classical problems.


Install
--------

This package can be install through `pip` using

```
$ pip install git+https://github.com/benchopt/benchopt
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
