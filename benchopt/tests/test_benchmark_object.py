import click
import pytest

from benchopt.utils.temp_benchmark import temp_benchmark


def test_dataset_name_default():
    # When test_dataset_name is None (the default), get_test_dataset_names
    # picks the sole dataset for single-dataset benchmarks, and falls back
    # to 'simulated' when multiple datasets are available.
    only_data = """from benchopt import BaseDataset
    class Dataset(BaseDataset):
        name = "only-data"
    """
    # For a benchmark with a single dataset, test_datset_name is this dataset
    with temp_benchmark(datasets=only_data) as bench:
        assert len(bench.get_dataset_names()) == 1
        assert bench.get_test_dataset_names() == ['only-data']

    # For a benchmark with multiple datasets, default is 'simulated'.
    # temp_benchmark add a simulated dataset by default when passed a dict.
    with temp_benchmark(datasets={'only-data': only_data}) as bench:
        assert len(bench.get_dataset_names()) > 1
        assert bench.get_test_dataset_names() == ['simulated']


def test_component_tag_filters():
    solvers = [
        """from benchopt import BaseSolver
        class Solver(BaseSolver):
            name = "cpu-solver"
            tags = ["easy", "cpu"]
        """,
        """from benchopt import BaseSolver
        class Solver(BaseSolver):
            name = "gpu-solver"
            tags = ["easy", "gpu"]
        """,
        """from benchopt import BaseSolver
        class Solver(BaseSolver):
            name = "untagged-solver"
        """,
    ]
    datasets = [
        """from benchopt import BaseDataset
        class Dataset(BaseDataset):
            name = "small-data"
            tags = ["easy", "small"]
        """,
        """from benchopt import BaseDataset
        class Dataset(BaseDataset):
            name = "large-data"
            tags = ["hard", "large"]
        """,
    ]

    with temp_benchmark(solvers=solvers, datasets=datasets) as bench:
        selected = bench.check_solver_patterns(
            [], tags=["cpu", "gpu"]
        )
        assert {solver.name for solver, _ in selected} == {
            "cpu-solver", "gpu-solver"
        }

        selected = bench.check_solver_patterns(
            ["gpu-solver"], tags=["gpu"]
        )
        assert [solver.name for solver, _ in selected] == ["gpu-solver"]

        selected = bench.check_dataset_patterns(
            [], tags=["easy"]
        )
        assert [dataset.name for dataset, _ in selected] == ["small-data"]

        assert len(bench.check_solver_patterns([])) == 3
        assert len(bench.check_dataset_patterns([])) == 2

        with pytest.raises(click.BadParameter, match="No solver matches"):
            bench.check_solver_patterns(
                ["cpu-solver"], tags=["gpu"]
            )


@pytest.mark.parametrize("component", ["solver", "dataset"])
def test_invalid_component_tag(component):
    with temp_benchmark() as bench:
        check_patterns = getattr(bench, f"check_{component}_patterns")
        with pytest.raises(
                click.BadParameter,
                match=f"Tags .*missing.* did not match any {component}"):
            check_patterns([], tags=["missing"])


@pytest.mark.parametrize(
    "tags", ["None", "('easy',)", "['easy', 1]", "['easy,gpu']"]
)
def test_invalid_component_tags(tags):
    solver = f"""from benchopt import BaseSolver
    class Solver(BaseSolver):
        name = "invalid-tags"
        tags = {tags}
    """
    with temp_benchmark(solvers=solver) as bench:
        with pytest.raises(
                ValueError, match="literal list of strings"):
            bench.check_solver_patterns([], tags=["easy"])


def test_tags_must_be_statically_readable():
    solvers = [
        """from benchopt import BaseSolver
        class Solver(BaseSolver):
            name = "valid-tags"
            tags = ["easy"]
        """,
        """from benchopt import BaseSolver
        failure
        class Solver(BaseSolver):
            name = "computed-tags"
            tags = make_tags()
        """,
    ]
    with temp_benchmark(solvers=solvers) as bench:
        with pytest.raises(ValueError, match="Could not read tags"):
            bench.check_solver_patterns([], tags=["easy"])
