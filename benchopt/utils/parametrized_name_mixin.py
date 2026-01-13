import itertools
from abc import abstractmethod


class ParametrizedNameMixin():
    """Mixing for parametric classes representation and naming.
    """
    parameters = {}

    def __init__(self, **parameters):
        """Default init set parameters base on the cls.parameters
        """
        pass

    def save_parameters(self, **parameters):
        _parameters = next(product_param(self.parameters))
        _parameters.update(parameters)
        self._parameters = _parameters
        for k, v in _parameters.items():
            if not hasattr(self, k):
                setattr(self, k, v)

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


def product_param(parameters):
    """Get an iterator that is the product of parameters expanded as a dict.

    Parameters
    ----------
    parameters: dict of list
        A dictionary of type {parameter_names: parameters_value_list}. The
        parameter_names is either a single parameter name or a list of
        parameter names separated with ','. The parameters_value_list should
        be either a list of value if there is only one parameter or a list of
        tuple with the same cardinality as parameter_names.

    Returns
    -------
    parameter_iterator: iterator
        An iterator where each element is a dictionary of parameters expanded
        as the product of every items in parameters.
    """
    parameter_names = parameters.keys()
    return map(expand, itertools.repeat(parameter_names),
               itertools.product(*parameters.values()))


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
