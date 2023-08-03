import json
import tempfile
import pandas as pd

from benchopt.utils.parquet import to_parquet
from benchopt.utils.parquet import get_metadata
from benchopt.utils.parquet import update_metadata


def test_parquet_metadata():
    df = pd.DataFrame({
        'a': range(4),
        'b': list('abcd'),
        'c': [.1, .2, .3, .4],
    })

    with tempfile.NamedTemporaryFile("rb+", suffix=".pq") as f:

        path = f.name
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
        assert (df_new == df).all().all()

        # Check that the metadata has been changed correctly
        assert json.dumps(get_metadata(path)) == json.dumps(metadata)
