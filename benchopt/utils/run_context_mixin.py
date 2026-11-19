import inspect
import warnings


class _CurrentRun:
    """Attribute of the current run, read with ``get_current``."""

    def __init__(self, doc):
        self.__doc__ = f"{doc} Only set while a run context is attached."

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        return obj.get_current(self.name[:-1])

    def __set__(self, obj, value):
        warnings.warn(
            f"`{self.name}` is set by benchopt to describe the current run. "
            f"Setting it on {obj} hides the run's value from this "
            "component. Use another name.", UserWarning, stacklevel=2
        )
        obj.__dict__[self.name] = value


class RunContextMixin:
    """Mixin that provides reproducible seeding and run-artifact helpers.

    Attributes ending with ``_`` give the current run. They are only set
    while a run context is attached, i.e. in the methods that benchopt calls.
    See :ref:`current_run`.
    """

    dataset_ = _CurrentRun("Dataset of the current run.")
    objective_ = _CurrentRun("Objective of the current run.")
    solver_ = _CurrentRun("Solver of the current run.")
    repetition_ = _CurrentRun("Repetition index of the current run.")
    parallel_config_ = _CurrentRun("Parallel config of the benchmark run.")
    run_parallel_config_ = _CurrentRun("Workers' parallel config, or None.")

    # Set by the runner before any user method is called.
    _run_context = None
    # Seed given by the last call to get_seed.
    _used_seed = None

    def get_seed(
        self, use_objective=False, use_dataset=False,
        use_solver=False, use_repetition=False,
    ):
        """Get the random seed for this component instance.

        Setting use_objective, use_dataset, use_solver or use_repetition to
        False returns a seed that is not affected by the corresponding
        component. The seed is in the range [0, 2**32 - 1].
        """
        if self._run_context is None:
            from benchopt import BaseDataset, BaseObjective, BaseSolver
            if isinstance(self, BaseDataset):
                hint = "Make sure to call get_seed from the get_data method."
            elif isinstance(self, BaseObjective):
                hint = (
                    "Make sure to call get_seed from the get_objective or "
                    "set_data methods."
                )
            elif isinstance(self, BaseSolver):
                hint = (
                    "Make sure to call get_seed from the set_objective method."
                )
            else:
                hint = ""
            raise ValueError(
                f"run_context was not initialized for {self}. {hint}"
            )

        params = dict(
            use_objective=use_objective, use_dataset=use_dataset,
            use_solver=use_solver, use_repetition=use_repetition,
        )
        seed = self._run_context.get_seed(
            class_name=self._base_class_name, **params
        )

        # Track the most restrictive seed parameters for later caching.
        # Reassign instead of mutating, as `_init_state` holds a shallow copy.
        seed_params = getattr(self, '_seed_params', {})
        self._seed_params = {
            k: v or seed_params.get(k, False) for k, v in params.items()
        }

        self._used_seed = seed

        return seed

    def _seed_changed(self):
        """Whether the seed of the current run differs from the used one."""
        return (
            self._used_seed is not None
            and self._used_seed != self._compute_used_seed()
        )

    def _compute_used_seed(self):
        """Recompute the stored seed with the current context and params.

        Returns self._used_seed when _run_context is not set so that the
        caller's ``x != _compute_used_seed()`` comparison stays False and
        does not trigger a spurious recomputation.
        """
        if self._run_context is None:
            return self._used_seed
        return self._run_context.get_seed(
            class_name=self._base_class_name,
            **self._seed_params,
        )

    def _skip_reason(self):
        """Return the reason to skip from ``self.skip()``, or None to run."""
        name = f"{type(self)!r}.skip"
        legacy = len(inspect.signature(self.skip).parameters) > 0
        if not legacy:
            output = self.skip()
        else:
            # XXX: remove in benchopt 1.12, with the skip receiving the data.
            warnings.warn(
                f"`{name}` receives the data as keyword arguments, which is "
                "deprecated and will be removed in benchopt 1.12. Define "
                "`skip(self)` instead, and use `self.dataset_` or "
                "`self.objective_` to access the other components without "
                "loading the data.",
                FutureWarning,
            )
            is_solver = self._base_class_name == 'Solver'
            upstream = self.get_current(
                'objective' if is_solver else 'dataset'
            )
            data = (
                upstream.get_objective() if is_solver else upstream.get_data()
            )
            output = self.skip(**data)

        # XXX: remove in benchopt 1.12, with the tuple output.
        if isinstance(output, tuple):
            if not legacy:
                warnings.warn(
                    f"`{name}` returns a `(skip, reason)` tuple, which is "
                    "deprecated and will be removed in benchopt 1.12. Return "
                    "the reason to skip, or None to run.",
                    FutureWarning,
                )
            skip, reason = output
            return (reason or "no reason given") if skip else None
        if output is None or output is False:
            return None
        if isinstance(output, str) and output:
            return output
        raise ValueError(
            f"`{name}` should return None to run, or a non-empty string "
            f"giving the reason to skip. Got {output!r}."
        )

    def get_current(self, name):
        """Return ``name`` of the current run, e.g. ``self.dataset_``."""
        names = (
            'dataset', 'objective', 'solver', 'repetition',
            'parallel_config', 'run_parallel_config',
        )
        if name not in names:
            raise ValueError(f"name should be one of {names}. Got {name!r}.")
        if self._run_context is None:
            raise RuntimeError(
                f"No run context is attached to {self}. The current run is "
                "only available in the methods that benchopt calls on it, or "
                "in a `with RunContext(...)` block."
            )
        return self._run_context.get_component(name)

    def get_run_output_path(self):
        """Return a directory for saving artifacts from the current run.

        The path is unique to the current (solver, dataset, objective,
        repetition) combination and is created on first call.

        Returns
        -------
        output_path : pathlib.Path
            A directory under ``<benchmark>/outputs/<run_name>/``.
        """
        if self._run_context is None:
            raise RuntimeError(
                "get_run_output_path() can only be called during run()."
            )
        return self._run_context.get_run_output_path()
