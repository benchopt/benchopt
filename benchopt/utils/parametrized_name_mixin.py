import itertools
from abc import abstractmethod

import cloudpickle

from .dynamic_modules import get_file_hash
from .dynamic_modules import _reconstruct_class


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
        if not hasattr(self, 'parameter_template'):
            # sort parameters to make sure the representation is deterministic
            self.parameter_template = ",".join([
                f"{k}={_parameters[k]}" for k in sorted(_parameters)
            ])
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
            out += f"[{self.parameter_template}]".format(**self._parameters)
        return out

    @classmethod
    def _get_parametrized_name(cls, **parameters):
        """Compute the parametrized name for a given set of parameters."""
        return str(cls.get_instance(**parameters))

    @staticmethod
    def _load_instance(class_value, parameters):
        klass = cloudpickle.loads(class_value)
        obj = klass.get_instance(**parameters)
        return obj

    def _get_reduce_args(self):
        """Get the arguments necessary to reconstruct the instance."""
        class_value = cloudpickle.dumps(self.__class__)
        class_value = cloudpickle.dumps(cloudpickle.loads(class_value))
        if self.name == "Simulated":
            print(self.__class__.__dict__)
        return class_value, self._parameters

    def __reduce__(self):
        return self._load_instance, self._get_reduce_args()


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


def _list_all_parametrized_names(*parametrized_classes):
    """List all names for parametrized classes."""
    all_names = []
    for cls in parametrized_classes:
        for dataset_parameters in product_param(cls.parameters):
            all_names.append(
                cls._get_parametrized_name(**dataset_parameters)
            )
    return all_names
