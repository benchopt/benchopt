import yaml
import json
import tempfile
import pandas as pd
from pathlib import Path

from benchopt.utils.parquet import to_parquet
from benchopt.utils.parquet import get_metadata
from benchopt.utils.parquet import update_metadata

from benchopt.cli.main import run
from benchopt.cli.process_results import plot
from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.config import DEFAULT_BENCHMARK_CONFIG

from benchopt.tests import SELECT_ONE_PGD
from benchopt.tests import SELECT_ONE_SIMULATED
from benchopt.tests import SELECT_ONE_OBJECTIVE
from benchopt.tests.utils import CaptureRunOutput


def test_parquet_metadata():
    df = pd.DataFrame({
        'a': range(4),
        'b': list('abcd'),
        'c': [.1, .2, .3, .4],
    })

    with tempfile.NamedTemporaryFile("rb+", suffix=".pq") as f:

        path = Path(f.name)
        metadata = {'test': 'info', 'plot_configs': [{}, {}, {}]}
        to_parquet(df, path, metadata)

        # Make sure the data is readable
        df_new = pd.read_parquet(path)
        assert (df_new == df).all().all()

        # Check that the metadata can be retrieved
        assert json.dumps(get_metadata(path)) == json.dumps(metadata)

        meta_update = {'test': 'ofni', 'a': 'b'}
        metadata.update(meta_update)
        update_metadata(path, meta_update)

        # Make sure the data did not change
        df_new = pd.read_parquet(path)
        assert df.equals(df_new)

        # Check that the metadata has been changed correctly
        assert json.dumps(get_metadata(path)) == json.dumps(metadata)


def test_metadata_saving():

    dummy_config = {
        'plot_configs': {
            'Init': {
                'kind': 'suboptimality_curve',
                'objective_column': 'objective_value',
                'scale': 'loglog',
                'ylim': ['5e-11', 100]
            },
            'View 2': {
                'kind': 'objective_curve',
                'objective_column': 'objective_mse',
                'scale': 'semilog-x',
                'xaxis_type': 'Iteration',
                'xlim': [1, 120],
                'ylim': ['5e1', '3.8e2']
            }
        }, 'plots': [
            'objective_curve',
           'suboptimality_curve',
           'relative_suboptimality_curve',
           'bar_chart'
        ]
    }

    with temp_benchmark() as benchmark:
        # Check that the computation caching is working properly.
        run_cmd = [
            str(benchmark.benchmark_dir), '-d', SELECT_ONE_SIMULATED,
            '-s', SELECT_ONE_PGD, '-n', '1', '-r', str(1),
            '-o', SELECT_ONE_OBJECTIVE, '--no-display',
        ]

        with CaptureRunOutput(delete_result_files=False) as out:
            run(run_cmd, 'benchopt', standalone_mode=False)

        config = get_metadata(Path(out.result_files[0]))
        expected_config = {
            k: v for k, v in DEFAULT_BENCHMARK_CONFIG.items()
            if k in ['plots', 'plot_configs']
        }
        assert config == expected_config

        config_file = benchmark.get_config_file()
        with config_file.open('w') as f:
            yaml.safe_dump(dummy_config, f)

        # Make sure that plot update the metadata of existing files.
        with CaptureRunOutput(delete_result_files=False):
            plot(
                [str(benchmark.benchmark_dir), '--no-display'],
                'benchopt', standalone_mode=False
            )

        assert get_metadata(Path(out.result_files[0])) == dummy_config

        # Make sure that run store the metadata when creating a file.
        with CaptureRunOutput(delete_result_files=False) as out:
            run(run_cmd, 'benchopt', standalone_mode=False)

        assert get_metadata(Path(out.result_files[0])) == dummy_config
