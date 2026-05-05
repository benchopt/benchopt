import io
import json
import pickle

import numpy as np
import pandas as pd
import pytest
import yaml
from pathlib import Path

from benchopt.results.parquet import (
    JSON_KEY,
    _PKL_PREFIX,
    _SafeUnpickler,
    get_metadata,
    pack,
    to_parquet,
    unpack,
    update_metadata,
)
from benchopt.cli.main import run
from benchopt.cli.process_results import plot
from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureCmdOutput


# ---------------------------------------------------------------------------
# pack / unpack unit tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [True, 42, 3.14, "hello", b"raw", None])
def test_pack_primitives_passthrough(value):
    """Parquet primitives must pass through pack() unchanged."""
    assert pack(value) is value


def test_pack_unpack_numpy_array():
    """A numpy array survives a pack/unpack round-trip."""
    arr = np.array([[1.0, 2.0], [3.0, 4.0]])
    packed = pack(arr)
    assert isinstance(packed, bytes)
    result = unpack(packed)
    np.testing.assert_array_equal(result, arr)


def test_pack_unpack_numpy_array_int():
    """Integer dtype arrays also survive the round-trip."""
    arr = np.arange(6).reshape(2, 3)
    np.testing.assert_array_equal(unpack(pack(arr)), arr)


def test_pack_unpack_builtin_list():
    """A plain list of primitives round-trips via the pickle fallback."""
    value = [1, 2.0, "three"]
    assert unpack(pack(value)) == value


def test_pack_unpack_builtin_dict():
    """A plain dict of primitives round-trips via the pickle fallback."""
    value = {"a": 1, "b": 2.5, "c": "x"}
    assert unpack(pack(value)) == value


def test_unpack_non_bytes_passthrough():
    """unpack() must return non-bytes or bytes with no prefix unchanged."""
    for v in [42, 3.14, "hello", None, b"no-prefix"]:
        assert unpack(v) == v


# ---------------------------------------------------------------------------
# Safety: _SafeUnpickler allowlist
# ---------------------------------------------------------------------------

class _Danger:
    """A class that is intentionally NOT in the allowlist."""
    pass


def test_safe_unpickler_blocks_unlisted_class():
    """Unpickling a class outside the allowlist must raise UnpicklingError."""
    raw = pickle.dumps(_Danger())
    payload = _PKL_PREFIX + raw
    with pytest.raises(pickle.UnpicklingError, match="Blocked unsafe class"):
        unpack(payload)


def test_safe_unpickler_allows_numpy():
    """A numpy array pickled manually is accepted by the safe unpickler."""
    arr = np.array([1.0, 2.0])
    raw = pickle.dumps(arr)
    result = _SafeUnpickler(io.BytesIO(raw)).load()
    np.testing.assert_array_equal(result, arr)


# ---------------------------------------------------------------------------
# to_parquet / read_results integration
# ---------------------------------------------------------------------------

def test_to_parquet_roundtrip_with_numpy(tmp_path):
    """A DataFrame with a numpy-array column round-trips through parquet."""
    from benchopt.results import read_results

    arr = np.arange(9).reshape(3, 3).astype(float)
    df = pd.DataFrame({
        "solver_name": ["s1"],
        "objective_value": [1.0],
        "result": [arr],
    })
    path = tmp_path / "results.parquet"
    to_parquet(df, path, metadata={"key": "val"})

    df2 = read_results(path)
    np.testing.assert_array_equal(df2["result"].iloc[0], arr)


def test_to_parquet_roundtrip_mixed_column(tmp_path):
    """A column with both primitives and numpy arrays round-trips correctly."""
    from benchopt.results import read_results

    arr = np.zeros((2, 2))
    df = pd.DataFrame({
        "solver_name": ["s1", "s2"],
        "objective_value": [1.0, 2.0],
        "result": [arr, None],
    })
    path = tmp_path / "results.parquet"
    to_parquet(df, path)

    df2 = read_results(path)
    np.testing.assert_array_equal(df2["result"].iloc[0], arr)
    assert df2["result"].iloc[1] is None or (
        isinstance(df2["result"].iloc[1], float)
        and np.isnan(df2["result"].iloc[1])
    )


def test_to_parquet_metadata_roundtrip(tmp_path):
    """Metadata dict is preserved through to_parquet."""
    import pyarrow.parquet as pq

    df = pd.DataFrame({"x": [1]})
    meta = {"benchmark": "test", "version": 2}
    path = tmp_path / "results.parquet"
    to_parquet(df, path, metadata=meta)

    schema = pq.read_schema(path)
    stored = json.loads(schema.metadata[JSON_KEY])
    assert stored == meta


def test_parquet_metadata(tmp_path):
    df = pd.DataFrame({
        'a': range(4),
        'b': list('abcd'),
        'c': [.1, .2, .3, .4],
    })

    path = tmp_path / "results.parquet"
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
                'plot_kind': 'objective_curve',
                'objective_curve_objective_column': 'objective_value',
                'scale': 'loglog',
                'objective_curve_X_axis': 'Iteration',
            },
            'View 2': {
                'plot_kind': 'bar_chart',
                'bar_chart_objective_column': 'objective_mse',
                'scale': 'semilog-x',
            }
        }, 'plots': [
            'objective_curve',
            'bar_chart'
        ]
    }

    with temp_benchmark() as bench:
        # Check that the computation caching is working properly.
        run_cmd = (
            f"{bench.benchmark_dir} -d test-dataset -n 1 -r 1 --no-display"
        ).split()

        with CaptureCmdOutput(delete_result_files=False) as out:
            run(run_cmd, 'benchopt', standalone_mode=False)

        config = get_metadata(Path(out.result_files[0]))
        assert config == {'plot_configs': {}}

        config_file = bench.get_config_file()
        with config_file.open('w') as f:
            yaml.safe_dump(dummy_config, f)

        # Make sure that plot update the metadata of existing files.
        with CaptureCmdOutput(delete_result_files=False):
            plot(
                [str(bench.benchmark_dir), '--no-display'],
                'benchopt', standalone_mode=False
            )

        assert get_metadata(Path(out.result_files[0])) == dummy_config

        # Make sure that run store the metadata when creating a file.
        with CaptureCmdOutput(delete_result_files=False) as out:
            run(run_cmd, 'benchopt', standalone_mode=False)

        assert get_metadata(Path(out.result_files[0])) == dummy_config
