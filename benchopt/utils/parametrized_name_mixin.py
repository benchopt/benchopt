import re
import ast
import warnings
import itertools
from abc import abstractmethod

import click


class ParametrizedNameMixin():
    """Mixing for parametric classes representation and naming.
    """
    parameters = {}

    # Parameter config for testing the class
    test_config = None

    def __init__(self, **parameters):
        """Default init set parameters base on the cls.parameters
        """
        super().__init__()

    def save_parameters(self, **parameters):
        _parameters = next(product_param(self.parameters))
        _parameters.update(parameters)
        self._parameters = _parameters
        for k, v in _parameters.items():
            if not hasattr(self, k):
                setattr(self, k, v)
            elif getattr(self, k) != v:
                v_set = getattr(self, k)
                raise ValueError(
                    f"Parameter {k} set in {self} `__init__` to {v_set}, "
                    f"while the parameter value is {v}."
                )

    @classmethod
    def get_all_parameter_values(cls, name):
        """Return all valid values for parameter `name`, or None when not
        enumerable. Distinct from `cls.parameters[name]`, which only drives
        the default sweep grid."""
        return None  # Default opt-out

    @classmethod
    def get_instance(cls, **parameters):
        """Helper function to instantiate an object and save its parameters.

        Saving the parameters allow for cheap hashing and to compute parametric
        names for the objects.
        """
        try:
            obj = cls(**parameters)
            obj.save_parameters(**parameters)
        except Exception as exception:
            # get type (Dataset, Objective, or Solver) of class and its name
            cls_type = cls.__base__.__name__
            cls_type = cls_type.replace("Base", "")
            cls_name = cls.name

            # Extend exception error message
            # TODO: use `add_note` when requiring python>=3.11
            exception.args = (
                f'Error when initializing {cls_type}: "{cls_name}". '
                f'{". ".join(exception.args)}',
            )
            raise

        return obj

    @property
    @abstractmethod
    def name(self):
        """Each object should expose its name for plotting purposes."""
        ...

    def __repr__(self):
        """Compute the parametrized name of the instance."""
        out = f"{self.name}"
        if len(self._parameters) > 0:
            if not hasattr(self, 'parameter_template'):
                # sort parameters to make sure the representation
                # is deterministic
                param_fmt = ",".join([
                    f"{k}={self._parameters[k]}"
                    for k in sorted(self._parameters)
                ])
            else:
                param_fmt = self.parameter_template.format(**self._parameters)
            out += f"[{param_fmt}]"
        return out

    @classmethod
    def _get_parametrized_name(cls, **parameters):
        """Compute the parametrized name for a given set of parameters."""
        return str(cls.get_instance(**parameters))

    @staticmethod
    def _load_instance(benchmark_dir, cls_info, parameters):
        # Make sure the running benchmark is set before loading the instance.
        from benchopt.benchmark import Benchmark
        Benchmark(benchmark_dir)

        # Load the dynamic class
        from benchopt.utils.dynamic_modules import _reconstruct_class
        klass = _reconstruct_class(benchmark_dir, *cls_info)

        # Set the parameters of the parametrized class.
        obj = klass.get_instance(**parameters)
        return obj

    def _get_mixin_args(self):
        """Get the arguments necessary to reconstruct the instance."""

        cls_info = (
            str(self.__class__._module_filename),
            self.__class__._base_class_name,
            self.__class__._file_hash
        )

        # Send the benchmark folder to the instance so it can access the config
        from benchopt.benchmark import get_running_benchmark
        benchmark_dir = get_running_benchmark().benchmark_dir

        return str(benchmark_dir), cls_info, self._parameters

    def __setstate__(self, state):
        """Default setstate method to reconstruct the instance.

        If `_get_state` is defined, this function should be overridden.
        """
        assert len(state) == 0, (
            "If `_get_state` is defined, this function should be overridden."
        )

    def _get_state(self):
        return {}

    def __reduce__(self):
        """Control pickling for inter-workers communication and hashing.

        Instances are reconstructed via ``_load_instance(*_get_mixin_args())``
        and then ``__setstate__(_get_state())`` is called.  Only what
        ``_get_mixin_args`` and ``_get_state`` return survives the round-trip;
        any instance attribute not included there is silently dropped.

        To persist extra attributes across pickling, override ``_get_state``
        (and the matching ``__setstate__``) in the subclass. `.
        """
        return self._load_instance, self._get_mixin_args(), self._get_state()


def expand(keys, values):
    """Expand the multiple parameters for itertools product"""
    args = []
    for k, v in zip(keys, values):
        if ',' in k:
            params_name = [p.strip() for p in k.split(',')]
            assert len(params_name) == len(v)
            args.extend(list(zip(params_name, v)))
        else:
            args.append((k, v))
    return dict(args)


def _get_used_parameters(klass, params, ignore=()):
    """Get the list of parameters to use in the class.

    Parameters
    ----------
    klass : class
        Class with a ``parameters`` attribute defining the full parameter grid.
    params : dict
        User-provided parameter filter (subset of values per key).
    ignore : tuple of str, optional
        Parameter names to exclude from the product.  Keys listed here are
        dropped before computing the cartesian product, so combinations that
        only differ on ignored dimensions are collapsed into one.

    Yields
    ------
    parameters : dict
        Deduplicated parameter dictionaries to use for instantiation.
    """
    # Make sure that all parameters are passed as iterables.
    params = {
        key: (val if isinstance(val, (list, tuple)) else [val])
        for key, val in params.items()
    }

    # Use product_param to get all combinations of parameters.
    # Then, update the default parameters (klass.parameters) with the
    # parameters extracted from filter names.
    used_parameters = []
    for update in product_param(params, ignore=ignore):
        for default in product_param(klass.parameters, ignore=ignore):
            default = default.copy()  # avoid modifying the original

            # check that all parameters are defined in klass.parameters
            keys_unknown = set(update) - set(default)
            if keys_unknown:
                raise ValueError(
                    f"Unknown parameters {list(keys_unknown)}, parameters "
                    f"must be in {list(default.keys())}"
                )

            default.update(update)
            if default not in used_parameters:  # avoid duplicates
                used_parameters.append(default)
                yield default


def product_param(parameters, ignore=None):
    """Get an iterator that is the product of parameters expanded as a dict.

    Parameters
    ----------
    parameters: dict of list
        A dictionary of type {parameter_names: parameters_value_list}. The
        parameter_names is either a single parameter name or a list of
        parameter names separated with ','. The parameters_value_list should
        be either a list of value if there is only one parameter or a list of
        tuple with the same cardinality as parameter_names.
    ignore: list of str, optional
        A list of parameter names to ignore.  If a parameter name is in this
        list, it is not included in the output dictionaries.

    Returns
    -------
    parameter_iterator: iterator
        An iterator where each element is a dictionary of parameters expanded
        as the product of every items in parameters.
    """
    ignore = set(ignore or [])
    parameters = {
        k: (v if isinstance(v, (list, tuple)) else [v])
        for k, v in parameters.items() if k not in ignore
    }
    parameter_names = parameters.keys()
    return map(expand, itertools.repeat(parameter_names),
               itertools.product(*parameters.values()))


def get_configs(dataset_class, obj_class=None, solver_class=None):
    """Merge configuration for dataset, objective and solver with priority.

    Returns
    -------
    configs: list[dict]
        A list of fully-resolved test config, expanded with variants from the
        ``Dataset.test_parameters``. Each entry has keys ``dataset``,
        ``objective`` and ``solver``.
    """

    # Get the test_config for each class, and resolve the dataset overrides.
    # Handle the case where objective/solver are None with getattr
    objective_config = (getattr(obj_class, 'test_config', None) or {}).copy()
    obj_ds = objective_config.pop('dataset', {})
    solver_config = (getattr(solver_class, 'test_config', None) or {}).copy()
    solver_ds = solver_config.pop('dataset', {})

    # Pop the name from the dataset overrides
    obj_ds.pop('name', None)
    solver_ds.pop('name', None)

    dataset_overrides = (dataset_class.test_config or {}).copy()
    dataset_overrides.update(**obj_ds)
    dataset_overrides.update(**solver_ds)
    objective_config.update(**solver_config.pop('objective', {}))

    test_parameters = getattr(dataset_class, 'test_parameters', {}).copy()
    test_parameters.update(**dataset_overrides)

    return [
        {
            'dataset': {**variant, **dataset_overrides},
            'objective': objective_config,
            'solver': solver_config,
        }
        for variant in product_param(test_parameters)
    ]


SUBSTITUTIONS = {"*": ".*"}


def _extract_parameters(string):
    """Extract parameters from a string.

    If the string contains a "=", returns a dict, otherwise returns a list.

    Examples
    --------
    >>> _extract_parameters("foo")  # ["foo"]
    >>> _extract_parameters("foo, 42, True")  # ["foo", 42, True]
    >>> _extract_parameters("foo=bar")  # {"foo": "bar"}
    >>> _extract_parameters("foo=[bar, baz]")  # {"foo": ["bar", "baz"]}
    >>> _extract_parameters("foo=1, baz=True")  # {"foo": 1, "baz": True}
    >>> _extract_parameters("'foo, bar'=[(0, 1),(1, 0)]")
    >>> # {"foo, bar": [(0, 1),(1, 0)]}
    """
    original = string

    # First, replace some expressions with their hashes, to avoid modification:
    # - quoted names
    all_matches = re.findall(r"'[^'\"]*'", string)
    all_matches += re.findall(r'"[^\'"]*"', string)
    # - numbers of the form "1e-3" (but not names like "foo1e3")
    all_matches += re.findall(
        r"(?<![a-zA-Z0-9_])[+-]?[0-9]+[.]?[0-9]*[eE][-+]?[0-9]+", string)
    for match in all_matches:
        string = string.replace(match, str(hash(match)))

    # Second, add quotes to all variable names (foo -> 'foo').
    # Accepts dots, dashes and slashes within names.
    string = re.sub(r"[a-zA-Z/\\][a-zA-Z0-9._\-/\\]*", r"'\g<0>'", string)

    # double all backslashes for ast eval
    string = re.sub(r"\\", r"\\\\", string)

    # Third, change back the hashes to their original names.
    for match in all_matches:
        string = string.replace(str(hash(match)), match)

    # Prepare the sequence for AST parsing.
    # Sequences with "=" are made into a dict expression {'foo': 'bar'}.
    # Sequences without "=" are made into a list expression ['foo', 'bar'].
    if "=" in string:
        string = "{" + string.replace("=", ":") + "}"
    else:
        string = "[" + string + "]"

    # Remove quotes for python language tokens
    for token in ["True", "False", "None"]:
        string = string.replace(f'"{token}"', token)
        string = string.replace(f"'{token}'", token)

    # Evaluate the string.
    try:
        return ast.literal_eval(string)
    except (ValueError, SyntaxError):
        raise ValueError(f"Invalid name '{original}', evaluated as {string}.")


def _extract_options(name):
    """Remove options indicated within '[]' from a name.

    Parameters
    ----------
    name : str
        Input name.

    Returns
    -------
    basename : str
        Name without options.
    args : list
        List of unnamed options.
    kwargs : dict()
        Dictionary with options.

    Examples
    --------
    >>> _extract_options("foo")  # "foo", [], dict()
    >>> _extract_options("foo[bar=2]")  # "foo", [], dict(bar=2)
    >>> _extract_options("foo[baz]")  # "foo", ["baz"], dict()
    """
    if name.count("[") != name.count("]"):
        raise ValueError(f"Invalid name (missing bracket): {name}")

    basename = "".join(re.split(r"\[.*\]", name))
    matches = re.findall(r"\[.*\]", name)

    if len(matches) == 0:
        return basename, [], {}
    elif len(matches) > 1:
        raise ValueError(f"Invalid name (multiple brackets): {name}")
    else:
        match = matches[0]
        match = match[1:-1]  # remove brackets

        result = _extract_parameters(match)
        if isinstance(result, dict):
            return basename, [], result
        elif isinstance(result, list):
            return basename, result, {}
        else:
            raise ValueError(
                f"Impossible. Please report this bug.\n"
                f"_extract_parameters returned '{result}'"
            )


def is_matched(name, include_patterns=None, default=True):
    """Check if a certain name is matched by any pattern in include_patterns.

    When include_patterns is None or [], always return `default`.
    """
    if include_patterns is None or len(include_patterns) == 0:
        return default
    name = str(name)
    name = _extract_options(name)[0]
    for p in include_patterns:
        p = _extract_options(p)[0]
        for old, new in SUBSTITUTIONS.items():
            p = p.replace(old, new)
        if re.match(f"^{p}$", name, flags=re.IGNORECASE) is not None:
            return True
    return False


def _contains_all(value):
    """Return True if the literal ``'all'`` appears anywhere in ``value``.

    Recurses into lists and tuples so that ``'all'`` nested inside the value
    of a coupled parameter (e.g. ``[(0, 1), (1, 'all')]``) is detected.
    """
    if isinstance(value, (list, tuple)):
        return any(_contains_all(v) for v in value)
    return value == 'all'


def _expand_all(cls, kwargs, name_type):
    """Expand ``'all'`` parameter values using ``get_all_parameter_values``.

    For each parameter whose selected value(s) contain the literal
    ``'all'``, replace ``'all'`` with the full set of valid values declared
    by ``cls.get_all_parameter_values(name)``. Any explicit values passed
    alongside ``'all'`` (e.g. ``[v1, 'all', v2]``) are preserved and
    de-duplicated against the declared choices, keeping a stable order
    (explicit values first, then declared choices not already listed).

    A class can instead declare that ``'all'`` is a legitimate literal value
    for a parameter (rather than the expansion token) by returning ``'all'``
    from ``get_all_parameter_values(name)``. In that case ``'all'`` is kept
    as-is, without expansion or warning.

    Parameters
    ----------
    cls : ParametrizedNameMixin
        The class whose parameters are being expanded. Its
        ``get_all_parameter_values`` classmethod declares the valid universe.
    kwargs : dict
        Mapping of parameter name to selected value(s), as extracted from a
        CLI pattern. Values may be a single value or a list.
    name_type : str
        Type of the class (``'dataset'``, ``'solver'``, ...), used only to
        build a sensible error message.

    Returns
    -------
    expanded : dict
        Copy of ``kwargs`` with every ``'all'`` replaced by the declared
        choices. Parameters that do not contain ``'all'`` are passed through
        unchanged.

    Warns
    -----
    UserWarning
        If a parameter requests ``'all'`` but ``cls.get_all_parameter_values``
        returns ``None`` for it (i.e. the class did not opt in by declaring an
        enumerable value set). In that case ``'all'`` is kept as a literal
        value. Implementing the hook to return the values (or ``'all'``)
        disables the warning.

    Raises
    ------
    click.BadParameter
        If ``'all'`` appears anywhere in the values of a coupled
        (comma-joined) parameter, for which expansion is not possible.
    """
    expanded = {}
    for key, val in kwargs.items():
        # For coupled (comma-joined) parameters, values must stay fixed tuples
        # that vary together, so 'all' cannot be expanded. Reject it wherever
        # it appears -- including nested inside the value tuples -- rather than
        # silently treating it as the literal value 'all'.
        if ',' in key:
            if _contains_all(val):
                raise click.BadParameter(
                    f"'all' is not supported for coupled parameters "
                    f"'{key}' of {name_type} '{cls.name}'."
                )
            expanded[key] = val
            continue
        vals = val if isinstance(val, list) else [val]
        if 'all' not in vals:
            expanded[key] = val
            continue
        choices = cls.get_all_parameter_values(key)
        if choices == 'all':
            # The class declares that 'all' is a legitimate literal value for
            # this parameter (rather than the expansion token). Keep it as-is,
            # without expanding or warning.
            expanded[key] = val
            continue
        if choices is None:
            # The class did not opt in by declaring an enumerable value set,
            # so 'all' cannot be expanded. Warn instead of failing, and keep
            # 'all' as a literal value. Implementing get_all_parameter_values
            # to return the values enables expansion; returning 'all' marks it
            # as a literal value and silences this warning.
            warnings.warn(
                f"Parameter '{key}' of {name_type} '{cls.name}' does not "
                f"declare an enumerable value set, so '{key}=all' is used as "
                f"a literal value. Override "
                f"{cls.__name__}.get_all_parameter_values('{key}') to return "
                f"the valid values (to enable '{key}=all') or 'all' (to keep "
                f"'all' as a literal value and silence this warning).",
                UserWarning,
            )
            expanded[key] = val
            continue
        # merge explicit values with the full set, de-duplicated, order-stable
        merged = [v for v in vals if v != 'all'] + [
            c for c in choices if c not in vals
        ]
        expanded[key] = merged
    return expanded


def _check_patterns(all_classes, patterns, name_type='dataset',
                    class_only=False):
    """Check the patterns and return a list of selected classes and params.

    Raise an error if a pattern does not match any dataset name,
    or if a parameter does not appear as a class parameter.

    Parameters
    ----------
    all_classes: list of ParametrizedNameMixin
        The possible classes to select from.
    patterns: list of str | dict
        List of patterns to select the classes. These patterns can be either:
            - str with the class name and parameters values:
                "cls_name[params1=[...],params2=...]"
            - dict with keys as cls_name and a dictionary of parameter values.
                {'cls_name': dict(params1=[...], params2=[])}
    name_type: str
        Used to raise sensible error depending on the type of classes which
        are selected.
    class_only: bool
        Only return the classes that are matched, without a list of parameters.

    Returns
    -------
    selected_classes: list of (ParametrizedNameMixin, parameters dict)
        A list with 2-tuple containing the selected class and a dictionary
        with selected parameters for this class.
    """
    from .dynamic_modules import FailedImport

    if patterns is not None and not isinstance(patterns, (list, tuple)):
        patterns = [patterns]

    # If no patterns is provided or all is provided, return all the classes.
    if (patterns is None or len(patterns) == 0
            or any(p == 'all' for p in patterns)):
        all_valid_patterns = [(cls, cls.parameters) for cls in all_classes]
        if not class_only:
            return all_valid_patterns
        return set(cls for cls, _ in all_valid_patterns)

    # Patterns can be either str or dict. Convert everything to 3-tuple with
    # (cls_name, args, kwargs). cls_name and kwargs correspond to class and
    # parameters selector. args is used to allow passing directly a list when
    # the class have only one parameter.
    def preprocess_patterns(pattern):
        if isinstance(pattern, str):
            return [_extract_options(pattern)]
        if isinstance(pattern, dict):
            return [
                (name, options, {}) if isinstance(options, list)
                else (name, [], options)
                for name, options in pattern.items()]
        raise TypeError()
    patterns = [p for q in patterns for p in preprocess_patterns(q)]

    # Check that each provided pattern matches at least one dataset and pair
    # the matching class with the selector.
    matched, invalid_patterns = [], []
    for p, args, kwargs in patterns:
        matched_cls = [
            (cls, (args, kwargs))
            for cls in all_classes
            if is_matched(cls.name, [p])
        ]
        if len(matched_cls) == 0:
            invalid_patterns.append(p)
        matched.extend([
            (cls, p) if not isinstance(cls, FailedImport) else (cls, ([], {}))
            for cls, p in matched_cls
        ])

    # If some patterns did not matched any class, raise an error
    if len(invalid_patterns) > 0:
        all_names = '- ' + '\n- '.join(cls.name for cls in all_classes)
        raise click.BadParameter(
            f"Patterns {invalid_patterns} did not match any {name_type}.\n"
            f"Available {name_type}s are:\n{all_names}"
        )

    # Check that the parameters are well formated:
    # - not ambiguous nor duplicated
    # - parameters correspond to existing one for a given class.
    all_valid_patterns = []
    for cls, (args, kwargs) in matched:
        param_names = [p.strip() for k in cls.parameters for p in k.split(',')]
        if len(args) != 0:
            if len(param_names) > 1:
                raise ValueError(
                    f"Ambiguous positional parameter for {cls.name}."
                )
            elif len(kwargs) > 0:
                raise ValueError(
                    f"Both positional and keyword parameters for {cls.name}."
                )
            elif len(param_names) == 0:
                raise ValueError(
                    f"Positional parameter provided for {cls.name} which has"
                    " no parameter."
                )
            # Use the single parameter name for this class.
            kwargs = {param_names[0]: args}
        else:
            bad_params = [
                p.strip() for k in kwargs for p in k.split(',')
                if p.strip() not in param_names
            ]
            if len(bad_params) > 0:
                msg = "Possible parameters are:\n- " + "\n- ".join(param_names)
                if len(param_names) == 0:
                    msg = f"This {name_type} has no parameters."
                bad_params = ', '.join(f"'{p}'" for p in bad_params)
                raise ValueError(
                    f"Unknown parameter {bad_params} for {name_type} "
                    f"{cls.name}.\n{msg}"
                )
        params = cls.parameters.copy()
        params.update(kwargs)
        params = _expand_all(cls, params, name_type)
        all_valid_patterns.append((cls, params))

    if not class_only:
        return all_valid_patterns

    return set(cls for cls, _ in all_valid_patterns)


def sanitize(name):
    """Sanitize a name to be used as an identifier.

    Replace spaces and dashes by underscores and convert to lower case.

    Parameters
    ----------
    name: str
        The name to sanitize

    Returns
    -------
    sanitized_str: str
        The sanitized str.
    """
    return name.replace(" ", "_").replace("-", "_").lower()
