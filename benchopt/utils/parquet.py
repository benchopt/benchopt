import json
import pyarrow as pa
import pyarrow.parquet as pq

JSON_KEY = b"_meta_json"


def to_parquet(df, path, metadata=None):
    """Write a ``pandas.DataFrame`` in a parquet file, with optional metadata.

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame to write in the parquet file.
    path: str | Path
        Path to write the parquet file.
    metadata: dict or None
        Metadata to store in the parquet file. This metadata should be
        serializable with json.
    """
    table = pa.Table.from_pandas(df)
    new_metadata = {
        JSON_KEY: json.dumps(metadata).encode("utf-8"),
        **table.schema.metadata
    }
    table = table.replace_schema_metadata(new_metadata)
    pq.write_table(table, path)


def update_metadata(path, metadata):
    """Update metadata in an existing parquet file.

    Parameters
    ----------
    path: str | Path
        Path of the parquet file to update.
    metadata: dict or None
        Metadata to store in the parquet file. This metadata should be
        serializable with json.
    """
    table = pq.read_table(path)
    new_metadata = {
        **table.schema.metadata
    }
    metadata_ = json.loads(new_metadata.get(JSON_KEY, b"{}").decode("utf-8"))
    metadata_.update(metadata)
    new_metadata[JSON_KEY] = json.dumps(metadata_).encode("utf-8")
    table = table.replace_schema_metadata(new_metadata)
    pq.write_table(table, path)


def get_metadata(path):
    """Retrieve metadata embedded using the ``to_parquet`` function.

    Parameters
    ----------
    path: str | Path
        Path of the parquet file to read from.
    """
    meta = pq.read_metadata(path)
    return json.loads(meta.metadata[JSON_KEY].decode("utf-8"))
