"""Utilities to load classes and module from filenames and class names.
"""
import ast
import sys
import hashlib
import warnings
import importlib
from pathlib import Path

from joblib.externals import cloudpickle

from .safe_import import safe_import_context
from .dependencies_mixin import DependenciesMixin


SKIP_IMPORT = False


def skip_import():
    """Once called, all the safe_import_context is skipped."""
    global SKIP_IMPORT
    SKIP_IMPORT = True


def _unskip_import():
    """Helper to reenable imports in tests."""
    global SKIP_IMPORT
    SKIP_IMPORT = False


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


def _load_class_from_module(module_filename, class_name, benchmark_dir):
    """Load a class from a module_filename.

    This helper also stores info necessary for DependenciesMixing to check the
    correct installation and to reload the classes.

    Parameters
    ----------
    module_filename : str or Path
        Path to the file defining the module to load the class from.
    class_name : str
        Name of the class to load
    benchmark_dir : str or Path
        Path to the benchmark_dir. It will be used to set the package
        name relative to it.

    Returns
    -------
    klass : class
        The klass requested from the given module.
    """
    global SKIP_IMPORT
    benchmark_dir = Path(benchmark_dir)
    module_filename = Path(module_filename)
    try:
        assert not SKIP_IMPORT  # go directly to except to skip import
        module = _get_module_from_file(module_filename, benchmark_dir)
        klass = getattr(module, class_name)
    except Exception:
            import traceback
            tb_to_print = traceback.format_exc(chain=False)

            # avoid circular import
            from .parametrized_name_mixin import ParametrizedNameMixin
            class FailedImport(ParametrizedNameMixin, DependenciesMixin):
                "Object for the class list that raises error if used."

                name, install_cmd, requirements = _get_cls_attributes(
                    module_filename, class_name
                )

                @classmethod
                def is_installed(cls, **kwargs):
                    print(
                        f"Failed to import {class_name} from "
                        f"{module_filename}. Please fix the following "
                        "error to use this file with benchopt:\n"
                        f"{tb_to_print}"
                    )
                    return False

            klass = FailedImport

    # Store the info to easily reload the class
    klass._module_filename = module_filename.resolve()
    klass._benchmark_dir = benchmark_dir.resolve()
    return klass


def get_file_hash(filename):
    """Compute the MD5 hash of a file.
    """
    hasher = hashlib.md5()
    with open(filename, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def _reconstruct_class(module_filename, class_name, benchmark_dir,
                       pickled_module_hash=None):
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

    return _load_class_from_module(module_filename, class_name, benchmark_dir)


def _get_cls_attributes(module_file, cls_name):
    module = ast.parse(module_file.read_text())

    cls_list = [node for node in module.body if isinstance(node, ast.ClassDef)
                                           and node.name == cls_name]
    if not cls_list:
        raise ValueError(f"Could not find {cls_name} in module {module_file}.")
    cls = cls_list[0]

    name, install_cmd, requirements = None, "conda", []
    for node in cls.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if target.id == "requirements":
                    requirements = ast.literal_eval(node.value)
                elif target.id == "name":
                    name = ast.literal_eval(node.value)
                elif target.id == "install_cmd":
                    install_cmd = ast.literal_eval(node.value)
    return name, install_cmd, requirements

# def _get_failed_import_object_name(module_file, cls_name):
#     # Parse the module file to find the name of the failing object

#     import ast
#     module_ast = ast.parse(Path(module_file).read_text())
#     classdef = [
#         c for c in module_ast.body
#         if isinstance(c, ast.ClassDef) and c.name == cls_name
#     ]
#     if len(classdef) == 0:
#         raise ValueError(f"Could not find {cls_name} in module {module_file}.")
#     c = classdef[-1]
#     name_assign = [
#         a for a in c.body
#         if (isinstance(a, ast.Assign) and any(list(
#             (isinstance(t, ast.Name) and t.id == "name") for t in a.targets
#         )))
#     ]
#     if len(name_assign) == 0:
#         raise ValueError(
#             f"Could not find {cls_name} name in module {module_file}"
#         )
#     return name_assign[-1].value.value
