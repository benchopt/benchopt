import io
import json
import pickle
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

JSON_KEY = b"_meta_json"

# Sentinel prefixes stored as the first bytes of binary parquet columns.
# Two distinct prefixes let unpack() route to the right deserializer.
_ST_PREFIX = b"\x00benchopt-st\x00"    # safetensors-encoded tensor
_PKL_PREFIX = b"\x00benchopt-pkl\x00"  # pickle-encoded fallback

# Types that parquet can store natively — passed through unchanged.
_PARQUET_PRIMITIVES = (bool, int, float, str, bytes, type(None))

# Whitelist of (module, name) pairs that the safe unpickler allows.
# Extend this tuple to support additional types.
_PICKLE_ALLOWLIST = frozenset({
    # Python builtins
    ("builtins", "list"),
    ("builtins", "dict"),
    ("builtins", "tuple"),
    ("builtins", "set"),
    ("builtins", "frozenset"),
    # numpy reconstruction internals
    ("numpy", "ndarray"),
    ("numpy", "dtype"),
    ("numpy.core.multiarray", "_reconstruct"),
    ("numpy.core.multiarray", "scalar"),
    ("numpy._core.multiarray", "_reconstruct"),
    ("numpy._core.multiarray", "scalar"),
    ("numpy._core.numeric", "_frombuffer"),
    # scipy sparse matrices
    ("scipy.sparse._csr", "csr_matrix"),
    ("scipy.sparse._csc", "csc_matrix"),
    ("scipy.sparse._coo", "coo_matrix"),
    ("scipy.sparse.compressed", "_cs_matrix"),
    ("scipy.sparse.base", "spmatrix"),
})


class _SafeUnpickler(pickle.Unpickler):
    """Unpickler restricted to a known-safe allowlist of classes."""

    def find_class(self, module, name):
        if (module, name) not in _PICKLE_ALLOWLIST:
            raise pickle.UnpicklingError(
                f"Blocked unsafe class during unpickling: {module}.{name}. "
                "Add it to _PICKLE_ALLOWLIST in benchopt/results/parquet.py "
                "if it is trusted."
            )
        return super().find_class(module, name)


def pack(value):
    """Serialize *value* for storage in a parquet binary column.

    - Parquet primitives (bool, int, float, str, bytes, None) pass through.
    - Anything safetensors can handle is encoded with it (numpy, torch, jax…).
    - Everything else is pickled.
    """
    if isinstance(value, _PARQUET_PRIMITIVES):
        return value
    try:
        from safetensors import serialize
        return _ST_PREFIX + serialize({"v": value})
    except Exception:
        pass
    return _PKL_PREFIX + pickle.dumps(value)


def unpack(value):
    """Reverse of pack."""
    if not isinstance(value, bytes):
        return value
    if value.startswith(_ST_PREFIX):
        from safetensors import deserialize
        return deserialize(value[len(_ST_PREFIX):])["v"]
    if value.startswith(_PKL_PREFIX):
        return _SafeUnpickler(io.BytesIO(value[len(_PKL_PREFIX):])).load()
    return value


# Public alias for code that checks column sentinels before calling unpack.
PICKLE_PREFIX = _PKL_PREFIX
ST_PREFIX = _ST_PREFIX


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
    # Pack any non-primitive values (numpy arrays, etc.) so pyarrow can
    # store them as binary columns. After packing, columns that contain
    # sentinel bytes must be explicitly typed as binary so pyarrow does not
    # try to infer int64 or another primitive type from the other rows.
    df = df.copy()
    binary_cols = []
    _PREFIXES = (_PKL_PREFIX, _ST_PREFIX)
    # Backwards compatibility: starting with pandas 3.0, not passing 'str'
    # raises a warning.
    incl = ["object", "str"] if pd.__version__ > "3" else ["object"]
    for col in df.select_dtypes(include=incl).columns:
        df[col] = df[col].map(pack)
        non_null = df[col].dropna()
        if not non_null.empty and any(
            isinstance(v, bytes) and v.startswith(_PREFIXES)
            for v in non_null
        ):
            binary_cols.append(col)

    arrays = {}
    for col in binary_cols:
        # NaN sentinel (float) must become None for pa.large_binary
        vals = [None if (v is None or (isinstance(v, float) and v != v)) else v
                for v in df[col]]
        arrays[col] = pa.array(vals, type=pa.large_binary())

    table = pa.Table.from_pandas(df)
    if arrays:
        for col, arr in arrays.items():
            idx = table.schema.get_field_index(col)
            table = table.set_column(idx, col, arr)
    new_metadata = {
        JSON_KEY: json.dumps(metadata or {}).encode("utf-8"),
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
    if path.suffix not in ['.pq', '.parquet']:
        return

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
    # Metadata are only saved in parquet files, skipping.
    if path.suffix not in ['.pq', '.parquet']:
        return {}

    meta = pq.read_metadata(path)
    if JSON_KEY not in meta.metadata:
        # No metadata was saved in the file, skipping.
        return {}

    return json.loads(meta.metadata[JSON_KEY].decode("utf-8"))
