"""Utilities to load classes and module from filenames and class names.
"""
from abc import ABCMeta
import ast
import sys
import hashlib
import warnings
import importlib
from pathlib import Path

from joblib.externals import cloudpickle

from .dependencies_mixin import DependenciesMixin
from .safe_import import safe_import_context
from .class_property import classproperty

SKIP_IMPORT = False


def skip_import():
    """Once called, all dynamic classes are not imported but necessary info is
    retrieved from the file."""
    global SKIP_IMPORT
    SKIP_IMPORT = True


def _unskip_import():
    """Helper to reenable imports in tests."""
    global SKIP_IMPORT
    SKIP_IMPORT = False


class FailedImport(ABCMeta):
    """MetaClass for fake classes mimicking components that cannot be imported.

    This class should be used as a metaclass so that the class type can be
    checked and to have an informative representation.
    """
    def __repr__(cls):
        return f"<FailedImport: {cls.cls_name}({cls.name})|| Exc: [{cls.exc}]>"


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
    correct installation and to reload the classes.

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
    try:
        assert not SKIP_IMPORT  # go directly to except to skip import
        module = _get_module_from_file(module_filename, benchmark_dir)
        klass = getattr(module, class_name)
        klass._import_ctx = _get_import_context(module)
    except Exception as e:
        import traceback
        tb_to_print = traceback.format_exc(chain=False)

        # avoid circular import
        from .parametrized_name_mixin import ParametrizedNameMixin
        from ..base import BaseSolver, BaseDataset, BaseObjective
        from ..plotting.base import BasePlot
        base_cls = dict(
            Solver=BaseSolver, Dataset=BaseDataset,
            Objective=BaseObjective, Plot=BasePlot
        )[class_name]

        class klass(base_cls, ParametrizedNameMixin, DependenciesMixin,
                    metaclass=FailedImport):
            "Object for the class list that raises error if used."

            exc = e
            _error_displayed = False
            _set_cls_attr_from_ast(module_filename, class_name, locals())
            cls_name = class_name

            @classmethod
            def is_installed(cls, env_name=None, raise_on_not_installed=False,
                             quiet=False, **kwargs):
                if env_name is not None:
                    return super().is_installed(
                        env_name=env_name,
                        raise_on_not_installed=raise_on_not_installed,
                        **kwargs
                    )
                if not SKIP_IMPORT:
                    if raise_on_not_installed:
                        raise cls.exc
                    if not cls._error_displayed and not quiet:
                        print(
                            f"Failed to import {class_name} from "
                            f"{module_filename}. Please fix the following "
                            "error to use this file with benchopt:\n"
                            f"{tb_to_print}"
                        )
                        cls._error_displayed = True
                return False

    # Store the info to easily reload the class and check it is installed
    klass._module_filename = module_filename.resolve()
    klass._benchmark_dir = benchmark_dir.resolve()
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


def _set_cls_attr_from_ast(module_file, cls_name, ctx):
    module = ast.parse(module_file.read_text())
    name = f"{module_file.stem}"

    cls_list = [node for node in module.body if isinstance(node, ast.ClassDef)
                and node.name == cls_name]
    if not cls_list:
        exc = ValueError(
            f"Could not find {cls_name} in module {module_file}."
        )
        exc.__cause__ = ctx['exc']
        ctx['exc'] = exc
        ctx['name'] = name
        return
    cls = cls_list[0]

    known_methods = [
        # Dataset methods
        "get_data",
        # Objective methods
        "set_data", "get_objective", "evaluate_result", "get_one_result",
        # Solver methods
        "set_objective", "run", "get_result"
    ]

    ctx['_base_class_name'] = cls_name
    ctx['name'], ctx['install_cmd'], ctx['requirements'] = None, "conda", []
    for node in cls.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if target.id in ["name", "requirements", "install_cmd"]:
                    try:
                        ctx[target.id] = ast.literal_eval(node.value)
                    except Exception:
                        if target.id == "name":
                            exc = ValueError(
                                f"Could not evaluate the name of the class "
                                f"{cls_name} in module {module_file}.\n"
                                f"The name should be a string literal."
                            )
                            exc.__cause__ = ctx['exc']
                            ctx['exc'] = exc
                            ctx['name'] = name
                        else:
                            msg = (
                                f"Could not evaluate statically '{target.id}' "
                                f"of the class {cls_name} in {module_file}.\n"
                                "By default, this should be a string literal. "
                                "If dynamic evaluation is necessary, use "
                                "`safe_import_context`."
                            )
                            def raise_err(self, msg=msg): raise ValueError(msg)
                            ctx[target.id] = classproperty(raise_err)
        if isinstance(node, ast.FunctionDef):
            if node.name in known_methods:
                ctx[node.name] = lambda *args, **kwargs: None

    if ctx['name'] is None:
        warnings.warn(
            f"The class {cls_name} in module {module_file} has no name "
            "attribute. Using the module filename as a fallback.",
            UserWarning
        )
        ctx['name'] = name
