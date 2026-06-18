class RunContextMixin:
    """Mixin that provides reproducible seeding and run-artifact helpers."""

    # Set by the runner before any user method is called.
    _run_context = None

    def __init__(self):
        super().__init__()
        # Tracks which components are used for the seed, uses
        # the most restrictive seed parameters for later caching.
        self._seed_params = {
            "use_objective": False,
            "use_dataset": False,
            "use_solver": False,
            "use_repetition": False,
        }
        self._used_seed = None

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

        seed = self._run_context.get_seed(
            class_name=self._base_class_name,
            use_objective=use_objective,
            use_dataset=use_dataset,
            use_solver=use_solver,
            use_repetition=use_repetition,
        )

        # Track the most restrictive seed parameters for later caching
        for key in self._seed_params:
            self._seed_params[key] |= locals()[key]

        self._used_seed = seed

        return seed

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
