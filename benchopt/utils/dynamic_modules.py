"""Utilities to load classes and module from filenames and class names.
"""
import sys
import hashlib
import importlib
from pathlib import Path


def _get_module_from_file(module_filename):
    """Load a module from the name of the file"""
    module_filename = Path(module_filename)
    package_name = '.'.join(
        ['benchopt_benchmarks', *module_filename.with_suffix('').parts[-3:]]
    )

    module = sys.modules.get(package_name, None)
    if module is None:
        spec = importlib.util.spec_from_file_location(
            package_name, module_filename
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[package_name] = module
    return module


def _load_class_from_module(module_filename, class_name):
    """Load a class from a module_filename.

    This helper also stores info necessary for DependenciesMixing to check the
    the correct installation and to reload the classes.

    Parameters
    ----------
    module_filename : str or Path
        Path to the file defining the module to load the class from.
    class_name : str
        Name of the class to load

    Returns
    -------
    klass : class
        The klass requested from the given module.
    """
    module_filename = Path(module_filename)
    module = _get_module_from_file(module_filename)
    klass = getattr(module, class_name)

    # Store the info to easily reload the class
    klass._module_filename = module_filename.resolve()
    klass._import_ctx = getattr(module, 'import_ctx', None)
    return klass


def get_file_hash(filename):
    """Compute the MD5 hash of a file.
    """
    hasher = hashlib.md5()
    with open(filename, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def _reconstruct_class(module_filename, class_name, pickled_module_hash=None):
    """Retrieve a class in module defined by its filename.

    Parameters
    ----------
    module_filename : str or Path
        path to the module from which the class should be retrieved.
    class_name : str
        Name of the class to retrieve.
    pickled_module_has : str or None
        MD5 hash of the module file, to ensure the module did not changed.

    Returns
    -------
    class: type
        The class that was requested.
    """
    if pickled_module_hash is not None:
        module_hash = get_file_hash(module_filename)
        assert pickled_module_hash == module_hash, (
            f'{class_name} class changed between pickle and unpickle. This '
            'object should not be stored using pickle for long term storage.'
        )

    return _load_class_from_module(module_filename, class_name)
