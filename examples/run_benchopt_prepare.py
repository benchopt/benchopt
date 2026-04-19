"""Preparing datasets with ``benchopt prepare``
==============================================

Benchopt separates **data preparation** (heavy one-time work: downloads,
extraction, pre-processing) from **data loading** (fast, per-run work done by
``get_data()``).

Preparation is cached by joblib so that invoking::

    $ benchopt prepare path/to/benchmark

is a no-op when the result is already in the cache.
"""

from benchopt.helpers.run_examples import ExampleBenchmark
from benchopt.helpers.run_examples import benchopt_cli

# %%
# Simple case: ``get_data()`` as fallback
# ----------------------------------------
#
# When a dataset does not define a custom ``prepare()`` method, benchopt
# falls back to calling ``get_data()`` during preparation.  This preserves
# backward compatibility with benchmarks written before the prepare step was
# introduced.
#
# We start from the ``minimal_benchmark`` example.  Its dataset only defines
# ``get_data()``, so the prepare step will call that directly.

DATASET_SIMPLE = """
    from benchopt import BaseDataset
    import numpy as np

    class Dataset(BaseDataset):
        name = 'simulated'
        parameters = {'n_samples': [100, 1000]}

        def get_data(self):
            print(f"\\n\\tGetting data for n_samples={self.n_samples}")

            rng = np.random.default_rng(0)
            X = rng.standard_normal((self.n_samples, 10))
            return dict(X=X)
"""

benchmark = ExampleBenchmark(
    base="minimal_benchmark", name="prepare_example",
    ignore=["custom_plot.py", "example_config.yml"],
    datasets={"simulated.py": DATASET_SIMPLE},
)
benchmark

# %%
# Running ``benchopt prepare`` triggers the preparation step for every
# parameter combination.  Because ``prepare()`` is not overridden here,
# ``get_data()`` is called as a fallback. The ``Getting data for
# n_samples=...`` print confirms it runs once for each combination.

benchopt_cli(f"prepare {benchmark.benchmark_dir}")

# %%
# A second call is a no-op: the cache recognises every combination
# and skips all preparation work.  Each status line now reads
# ``Preparing ... done``, with no call to the actual ``get_data``.

benchopt_cli(f"prepare {benchmark.benchmark_dir}")

# %%
# The ``--prepare`` flag of ``benchopt install`` runs the same preparation
# step right after installing the benchmark dependencies, so data is ready
# before the first run::
#
#     $ benchopt install path/to/benchmark --prepare
#
# This is convenient in CI pipelines or when setting up a benchmark for the
# first time.

# %%
# Custom ``prepare()`` method
# ----------------------------
#
# For datasets that require genuine heavy work (downloading an archive,
# extracting files, training a feature extractor, …), define a ``prepare()``
# method.  It is called at most once per unique parameter combination and its
# result is cached.
#
# ``prepare()`` is meant to be *idempotent*: calling it multiple times is
# always safe.  Think of it as a setup step that guarantees data is on disk
# and in the right form before ``get_data()`` ever runs.

DATASET_PREPARE = """
from benchopt import BaseDataset
import numpy as np

class Dataset(BaseDataset):
    name = 'simulated'
    parameters = {'n_samples': [100, 1000]}

    def prepare(self):
        # Heavy one-time work goes here: downloading archives, feature
        # extraction, pre-processing …
        # Here we just simulate it with a print statement.
        print(f"\\n    > Preparing n_samples={self.n_samples}")

    def get_data(self):
        rng = np.random.default_rng(0)
        X = rng.standard_normal((self.n_samples, 10))
        return dict(X=X)
"""

benchmark.update(datasets={"simulated.py": DATASET_PREPARE})

# %%
# After modifying the dataset, the cache is invalidated. Calling
# ``benchopt prepare`` now run the new ``prepare()`` method for every parameter
# combination (here ``n_samples ∈ {100, 1000}``).  The ``> Preparing
# n_samples=...`` print confirms both combinations are executed.

benchopt_cli(f"prepare {benchmark.benchmark_dir}")


# %%
# ``prepare_cache_ignore``: reducing redundant preparation work
# -------------------------------------------------------------
#
# Some parameters influence the *benchmark run* but not the data that
# ``prepare()`` produces.  A typical example is a random seed: the
# preparation step (e.g. downloading a fixed dataset) is identical across all
# seed values.
#
# ``prepare_cache_ignore`` lists those parameters.  Benchopt groups all
# parameter combinations that differ only in ignored dimensions and runs
# ``prepare()`` at most once per group:
#
# - ``prepare_cache_ignore = ('seed',)`` — ignore the ``seed`` parameter;
#   preparation runs once per unique value of the remaining parameters.
# - ``prepare_cache_ignore = 'all'`` — ignore every parameter; ``prepare()``
#   runs at most once per dataset class regardless of parameterization.

DATASET_CACHE_IGNORE = """
from benchopt import BaseDataset
import numpy as np

class Dataset(BaseDataset):
    name = 'simulated'
    parameters = {'n_samples': [100, 1000], 'seed': [0, 1, 2]}

    # The preparation does not depend on the random seed, so we exclude
    # 'seed' from the cache key.  This reduces 6 prepare() calls to 2.
    prepare_cache_ignore = ('seed',)

    def prepare(self):
        print(f"\\n    > Preparing n_samples={self.n_samples}")

    def get_data(self):
        rng = np.random.default_rng(self.seed)
        X = rng.standard_normal((self.n_samples, 10))
        return dict(X=X)
"""

benchmark.update(datasets={"simulated.py": DATASET_CACHE_IGNORE})

# %%
# With 6 parameter combinations (2 × 3) but ``seed`` ignored, benchopt
# deduplicates to 2 effective preparation jobs.  Only the ``seed=0``
# representative of each group appears in the output, and ``prepare()``
# prints exactly twice.

benchopt_cli(f"prepare {benchmark.benchmark_dir}")

# %%
# Setting ``prepare_cache_ignore = 'all'`` is even more aggressive: it runs
# ``prepare()`` at most once per dataset class, regardless of any parameter
# values.  Use this when the dataset is a fixed external file that requires no
# per-parameter processing at all.
