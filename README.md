## Benchmark repo for optimization

[![Build Status](https://dev.azure.com/benchopt/benchopt/_apis/build/status/benchopt.benchOpt?branchName=master)](https://dev.azure.com/benchopt/benchopt/_build/latest?definitionId=1&branchName=master)
[![Python 3.6+](https://img.shields.io/badge/python-3.6%2B-blue)](https://www.python.org/downloads/release/python-360/)

The goal of this project is to benchmark implementation of optimization methods on several classical problems.


Install
--------

This package can be install through `pip` using

```
$ pip install https://github.com/benchopt/benchopt
```

Usage
-----

The `benchopt` command line tool is based on `click`. To run benchmarks on all problems, all datasets and with all solvers, run:

```
benchopt run
```

Options can also be passed to `benchopt run`, to restrict the benchmarks to some objectives, solvers or datasets, e.g.:

```
benchopt run lasso -s sklearn -s baseline -d boston --max-samples 10 --repetition 10
```

Use `benchopt run -h` for more details about options.
