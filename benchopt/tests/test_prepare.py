import pytest

from benchopt.base import BaseDataset
from benchopt.cli.main import prepare as prepare_cmd
from benchopt.utils.temp_benchmark import temp_benchmark


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dataset_src(body="", *, name="test-prepare", params=None,
                 cache_ignore=None):
    """Build dataset source code.

    Parameters
    ----------
    body : str
        Extra method source to insert verbatim inside the class.
        Each line must already be indented with 8 spaces.
    name : str
        Dataset name.
    params : str or None
        If given, inserted as ``parameters = <params>`` class attribute.
    cache_ignore : str or None
        If given, inserted as ``prepare_cache_ignore = <cache_ignore>``.
    """
    extras = ""
    if params is not None:
        extras += f"\n        parameters = {params}"
    if cache_ignore is not None:
        extras += f"\n        prepare_cache_ignore = {cache_ignore}"
    return (
        "from benchopt import BaseDataset\n"
        "class Dataset(BaseDataset):\n"
        f'    name = "{name}"\n'
        + (f"    parameters = {params}\n" if params is not None else "")
        + (
            f"    prepare_cache_ignore = {cache_ignore}\n"
            if cache_ignore is not None else ""
        )
        + body
        + "\n    def get_data(self):\n"
        "        return dict(X=None, y=None)\n"
    )


# ---------------------------------------------------------------------------
# Unit tests: BaseDataset._prepare staticmethod
# ---------------------------------------------------------------------------

class TestBaseDatasetPrepare:

    def test_default_prepare_is_noop(self):
        """Without a custom prepare(), the class uses BaseDataset's no-op."""
        with temp_benchmark() as bench:
            cls = bench.get_datasets()[0]
        assert cls.prepare is BaseDataset.prepare

    def test_prepare_fallback_calls_get_data(self, tmp_path):
        """_prepare() calls get_data() when prepare() is not overridden."""
        sentinel = tmp_path / "get_data_called.txt"
        src = (
            "from benchopt import BaseDataset\n"
            "class Dataset(BaseDataset):\n"
            "    name = 'fallback-dataset'\n"
            f"    def get_data(self):\n"
            f"        open(r'{sentinel}', 'w').close()\n"
            f"        return dict(X=None, y=None)\n"
        )
        with temp_benchmark(datasets=src) as bench:
            datasets = bench.get_datasets()
            bench.prepare_all_data(datasets)
        assert sentinel.exists()

    def test_custom_prepare_called_not_get_data(self, tmp_path):
        """_prepare() calls prepare() and NOT get_data() when overridden."""
        prepare_sentinel = tmp_path / "prepare_called.txt"
        get_data_sentinel = tmp_path / "get_data_called.txt"
        src = (
            "from benchopt import BaseDataset\n"
            "class Dataset(BaseDataset):\n"
            "    name = 'custom-prepare-dataset'\n"
            f"    def prepare(self):\n"
            f"        open(r'{prepare_sentinel}', 'w').close()\n"
            f"    def get_data(self):\n"
            f"        open(r'{get_data_sentinel}', 'w').close()\n"
            f"        return dict(X=None, y=None)\n"
        )
        with temp_benchmark(datasets=src) as bench:
            datasets = bench.get_datasets()
            bench.prepare_all_data(datasets)
        assert prepare_sentinel.exists()
        assert not get_data_sentinel.exists()


# ---------------------------------------------------------------------------
# Unit tests: get_prepare_params()
# ---------------------------------------------------------------------------

class TestGetPrepareParams:

    def test_no_params_yields_one_empty(self):
        """Dataset with no parameters yields exactly one empty dict."""
        with temp_benchmark() as bench:
            cls = bench.get_datasets()[0]
            result = list(cls.get_prepare_params())
        assert result == [{}]

    def test_params_no_ignore_yields_all(self):
        """Without cache_ignore, all parameter combos are independent."""
        src = _dataset_src(
            params="{'a': [0, 1], 'b': [10, 20]}",
        )
        with temp_benchmark(datasets=src) as bench:
            cls = bench.get_datasets()[0]
            result = list(cls.get_prepare_params())
        # 2 x 2 = 4 combinations, all effective
        assert len(result) == 4
        for effective in result:
            assert set(effective.keys()) == {"a", "b"}

    def test_cache_ignore_deduplicates(self):
        """Params in prepare_cache_ignore collapse duplicates."""
        src = _dataset_src(
            params="{'n': [1000, 10000], 'seed': [0, 1, 2]}",
            cache_ignore="('seed',)",
        )
        with temp_benchmark(datasets=src) as bench:
            cls = bench.get_datasets()[0]
            result = list(cls.get_prepare_params())
        # Only 2 unique effective combos (one per value of 'n')
        assert len(result) == 2
        for effective in result:
            assert "seed" not in effective
            assert "n" in effective

    def test_cache_ignore_all_yields_one(self):
        """prepare_cache_ignore='all' yields exactly one job per class."""
        src = _dataset_src(
            params="{'n': [1000, 10000], 'seed': [0, 1, 2]}",
            cache_ignore='"all"',
        )
        with temp_benchmark(datasets=src) as bench:
            cls = bench.get_datasets()[0]
            result = list(cls.get_prepare_params())
        assert len(result) == 1
        effective = result[0]
        assert effective == {}


# ---------------------------------------------------------------------------
# Unit tests: Benchmark.prepare_all_data()
# ---------------------------------------------------------------------------

class TestPrepareAllData:

    def test_empty_datasets_returns_zero(self):
        with temp_benchmark() as bench:
            assert bench.prepare_all_data([]) == 0

    def test_default_prepare_runs_get_data(self, capsys):
        """Default (no prepare override) runs get_data() and exits 0."""
        with temp_benchmark() as bench:
            datasets = bench.get_datasets()
            exit_code = bench.prepare_all_data(datasets)
        assert exit_code == 0

    def test_custom_prepare_is_called(self, capsys, tmp_path):
        """Custom prepare() is called and result is cached."""
        sentinel = tmp_path / "prepared.txt"
        src = _dataset_src(
            f"    def prepare(self):\n"
            f"        open(r'{sentinel}', 'w').close()\n",
        )
        with temp_benchmark(datasets=src) as bench:
            datasets = bench.get_datasets()
            exit_code = bench.prepare_all_data(datasets)
        assert exit_code == 0
        assert sentinel.exists()

    def test_caching_skips_second_call(self, tmp_path):
        """Second prepare_all_data() call hits cache; prepare() not re-run."""
        counter_file = tmp_path / "count.txt"
        counter_file.write_text("0")
        src = _dataset_src(
            f"    def prepare(self):\n"
            f"        n = int(open(r'{counter_file}').read())\n"
            f"        open(r'{counter_file}', 'w').write(str(n + 1))\n",
        )
        with temp_benchmark(datasets=src) as bench:
            datasets = bench.get_datasets()
            bench.prepare_all_data(datasets)
            bench.prepare_all_data(datasets)

        assert counter_file.read_text() == "1"

    def test_force_bypasses_cache(self, tmp_path):
        """force=True forces prepare() to re-run even if cached."""
        counter_file = tmp_path / "count.txt"
        counter_file.write_text("0")
        src = _dataset_src(
            f"    def prepare(self):\n"
            f"        n = int(open(r'{counter_file}').read())\n"
            f"        open(r'{counter_file}', 'w').write(str(n + 1))\n",
        )
        with temp_benchmark(datasets=src) as bench:
            datasets = bench.get_datasets()
            bench.prepare_all_data(datasets)
            bench.prepare_all_data(datasets, force=True)

        assert counter_file.read_text() == "2"

    def test_failure_returns_nonzero_and_warns(self):
        """Failed prepare() gives exit code 1 and emits a warning."""
        src = _dataset_src(
            "    def prepare(self):\n"
            "        raise RuntimeError('preparation failed')\n",
        )
        with temp_benchmark(datasets=src) as bench:
            datasets = bench.get_datasets()
            with pytest.warns(UserWarning, match="preparation failed"):
                exit_code = bench.prepare_all_data(datasets)
        assert exit_code == 1


# ---------------------------------------------------------------------------
# Integration test: benchopt prepare CLI
# ---------------------------------------------------------------------------

class TestPrepareCLI:

    def test_invalid_benchmark(self):
        import click
        with pytest.raises((click.BadParameter, SystemExit)):
            prepare_cmd(
                ["invalid_path"], 'benchopt', standalone_mode=False
            )

    def test_basic_invocation(self, capsys):
        """benchopt prepare runs without error on a default benchmark."""
        with temp_benchmark() as bench:
            exit_code = prepare_cmd(
                [str(bench.benchmark_dir)],
                'benchopt', standalone_mode=False
            )
        assert exit_code is None  # click standalone_mode=False returns None

    def test_dataset_filter(self, tmp_path, capsys):
        """Only the selected dataset is prepared when -d is used."""
        prepared = tmp_path / "prepared.txt"
        skipped = tmp_path / "skipped.txt"

        ds_a = _dataset_src(
            f"    def prepare(self):\n"
            f"        open(r'{prepared}', 'w').close()\n",
            name="dataset-a",
        )
        ds_b = _dataset_src(
            f"    def prepare(self):\n"
            f"        open(r'{skipped}', 'w').close()\n",
            name="dataset-b",
        )
        with temp_benchmark(datasets=[ds_a, ds_b]) as bench:
            prepare_cmd(
                [str(bench.benchmark_dir), "-d", "dataset-a"],
                'benchopt', standalone_mode=False
            )
        assert prepared.exists()
        assert not skipped.exists()

    def test_force_flag(self, tmp_path):
        """--force re-runs preparation even when cached."""
        counter_file = tmp_path / "count.txt"
        counter_file.write_text("0")
        src = _dataset_src(
            f"    def prepare(self):\n"
            f"        n = int(open(r'{counter_file}').read())\n"
            f"        open(r'{counter_file}', 'w').write(str(n + 1))\n",
        )
        with temp_benchmark(datasets=src) as bench:
            prepare_cmd(
                [str(bench.benchmark_dir)],
                'benchopt', standalone_mode=False
            )
            prepare_cmd(
                [str(bench.benchmark_dir), "--force"],
                'benchopt', standalone_mode=False
            )
        assert counter_file.read_text() == "2"
