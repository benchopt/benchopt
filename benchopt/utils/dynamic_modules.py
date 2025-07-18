"""Utilities to load classes and module from filenames and class names.
"""
import sys
import hashlib
import warnings
import importlib
from pathlib import Path

from joblib.externals import cloudpickle

from .safe_import import safe_import_context


def _get_module_from_file(module_filename, benchmark_dir=None):
    """Load a module from the name of the file"""
    module_filename = Path(module_filename)
    if benchmark_dir is not None:
        # Use a package name derived from the benchmark root folder.
        module_filename = module_filename.resolve()
        benchmark_dir = Path(benchmark_dir).resolve().parent
        package_name = module_filename.relative_to(benchmark_dir)
        package_name = package_name.with_suffix('').parts
    else:
        package_name = module_filename.with_suffix('').parts[-3:]
    if package_name[-1] == '__init__':
        package_name = package_name[:-1]
    package_name = '.'.join(['benchopt_benchmarks', *package_name])

    module = sys.modules.get(package_name, None)
    if module is None:
        spec = importlib.util.spec_from_file_location(
            package_name, module_filename
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[package_name] = module

        # Make functions define in the dynamic module pickleable
        cloudpickle.register_pickle_by_value(module)

    return module


def _load_class_from_module(benchmark_dir, module_filename, class_name):
    """Load a class from a module_filename.

    This helper also stores info necessary for DependenciesMixing to check the
    the correct installation and to reload the classes.

    Parameters
    ----------
    benchmark_dir : str or Path
        Path to the benchmark_dir. It will be used to set the package
        name relative to it.
    module_filename : str or Path
        Path to the file defining the module to load the class from.
    class_name : str
        Name of the class to load

    Returns
    -------
    klass : class
        The klass requested from the given module.
    """
    benchmark_dir = Path(benchmark_dir)
    module_filename = Path(module_filename)
    module = _get_module_from_file(
        module_filename, benchmark_dir=benchmark_dir
    )
    klass = getattr(module, class_name)

    # Store the info to easily reload the class
    klass._module_filename = module_filename.resolve()
    klass._import_ctx = _get_import_context(module)
    klass._file_hash = get_file_hash(klass._module_filename)

    return klass


def _get_import_context(module):
    """Helper to get the import context from a module.
    In particular, if `import_ctx` is not defined, check that no local objects
    is an instance of safe_import_context.
    """
    import_ctx = getattr(module, 'import_ctx', None)
    if import_ctx is not None:
        return import_ctx

    for var_name in dir(module):
        var = getattr(module, var_name)
        if isinstance(var, safe_import_context):
            import_ctx = var
            warnings.warn(
                "Import contexts should preferably be named import_ctx, "
                f"got {var_name}.",  UserWarning
            )
            break
    else:
        import_ctx = safe_import_context()

    return import_ctx


def get_file_hash(filename):
    """Compute the MD5 hash of a file.
    """
    hasher = hashlib.md5()
    with open(filename, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def _reconstruct_class(
        benchmark_dir, module_filename, class_name, pickled_module_hash
):
    """Retrieve a class in module defined by its filename.

    Parameters
    ----------
    benchmark_dir : str or Path
        Folder containing the benchmark.
    module_filename : str or Path
        Path to the module from which the class should be retrieved.
    class_name : str
        Name of the class to retrieve.
    module_hash : str or None
        MD5 hash of the module file, to ensure the module did not changed.

    Returns
    -------
    class: type
        The class that was requested.
    """
    module_hash = get_file_hash(module_filename)
    assert pickled_module_hash == module_hash, (
        f'{class_name} class changed between pickle and unpickle. This '
        'object should not be stored using pickle for long term storage.'
    )

    return _load_class_from_module(benchmark_dir, module_filename, class_name)
