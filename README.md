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

The main entry point to run benchmark with benchOpt is the `benchopt` command line tool, based on `click`.
To run a benchmark to options are possible.

When the solvers are installed directly on the system, it is possible to use the `run` command:

```
benchopt run lasso -s sklearn -s baseline --max-samples 10 --repetition 10
```

It is also possible to run the benchmark in a separate environment with the `bench` command. The solver will be installed in a virtual environment.The usage is:

```
benchopt bench lasso -s sklearn -s baseline --max-samples 10 --repetition 10
```
