import re
import hashlib
from pathlib import Path
from functools import cached_property
from dataclasses import dataclass, field, replace as dc_replace
from .run_context_mixin import RunContextMixin


class RunContextError(ValueError):
    """Raised when a component requested from the run context is absent from
    it (e.g. the solver while no solver is chosen yet). Carries ``component``
    so callers can tailor the message.
    """

    def __init__(self, component, message):
        super().__init__(message)
        self.component = component


def _sanitize_path_component(name):
    """Replace filesystem-unsafe characters in a component name.

    Solver/dataset/objective names may contain parameter values with
    characters such as '/' that would split a path segment unexpectedly.
    Replace every run of such characters with '_'.
    """
    return re.sub(r'[/\\:*?"<>|]+', '_', name)


@dataclass
class RunContext:
    """Context for one benchmark run (dataset × objective × solver × rep).

    Holds the components of the run and everything needed to compute
    reproducible seeds, locate the per-run artifact directory, and carry
    runtime flags. It is attached to its components only while benchopt calls
    their methods, with ``with run_context:``. Excluded from the joblib cache
    key, which already holds the components, the repetition and the seed.

    Config fields (set once in ``_run_benchmark``):
        run_output_base, pdb, parallel_config

    Per-run fields (filled by ``for_run`` for each dataset × objective ×
    solver × rep):
        base_seed, dataset, objective, solver, repetition

    ``run_parallel_config`` is derived from them on first use.
    """
    # Config fields — set once per benchmark invocation
    run_output_base: Path | None = None
    pdb: bool = False
    # Parallel config of the benchmark, as given by `--parallel-config`.
    parallel_config: dict | None = field(default=None, repr=False)
    # Per-run fields — cloned/updated for each (dataset, obj, solver, rep).
    # A field left as None means the corresponding component is not available
    # in this context (e.g. objective/solver/repetition during prepare) and
    # requesting its seed raises a clear error in get_seed.
    base_seed: int | str = ""
    # A component can be a placeholder name, e.g. to test a dataset alone.
    dataset: RunContextMixin | str | None = field(default=None, repr=False)
    objective: RunContextMixin | str | None = field(default=None, repr=False)
    solver: RunContextMixin | str | None = field(default=None, repr=False)
    repetition: int | None = None
    # Contexts of the components before entering this one, to restore them.
    _previous: list = field(default_factory=list, repr=False, compare=False)

    def get_seed(self, class_name, use_objective=False, use_dataset=False,
                 use_solver=False, use_repetition=False):
        """Compute a deterministic integer seed for a given component."""
        use_flags = {
            "base_seed": (True, str(self.base_seed)),
            "objective": (use_objective, self._name('objective')),
            "dataset": (use_dataset, self._name('dataset')),
            "solver": (use_solver, self._name('solver')),
            "repetition": (use_repetition, self._name('repetition')),
            "class": (True, class_name.lower()),
        }
        for component, (use, value) in use_flags.items():
            if use and value is None:
                raise RunContextError(
                    component,
                    f"get_seed(use_{component}=True) was called but no "
                    f"{component} is defined in the current run context. This "
                    "happens for instance during `benchopt prepare`, where "
                    "only the dataset is available. Make sure the seed only "
                    "depends on components defined where get_seed() is called."
                )
        hash_list = [v if use else "*" for use, v in use_flags.values()]
        digest = hashlib.sha256("_".join(hash_list).encode()).hexdigest()
        return int(digest, 16) % (2**32 - 1)

    def get_run_output_path(self):
        """Return the per-run artifact directory, creating it on first call."""
        if self.run_output_base is None:
            raise RuntimeError(
                "get_run_output_path() is only available when running via "
                "'benchopt run' (not 'benchopt test' or --no-cache)."
            )
        path = (
            self.run_output_base
            / _sanitize_path_component(self._name('dataset'))
            / _sanitize_path_component(self._name('objective'))
            / _sanitize_path_component(self._name('solver'))
            / f"rep_{self.repetition}"
        )
        path.mkdir(parents=True, exist_ok=True)
        return path

    def for_run(self, objective, dataset, solver, repetition, base_seed):
        """Clone the context with the per-run fields.

        Enter the returned context (``with ctx:``) to attach it to the
        components while calling their methods.
        """
        return dc_replace(
            self, objective=objective, dataset=dataset, solver=solver,
            repetition=repetition, base_seed=base_seed, _previous=[],
        )

    def _name(self, name):
        """Return the name of a component or the repetition, None if unset."""
        value = getattr(self, name)
        return None if value is None else str(value)

    def get_component(self, name):
        """Return the component, repetition or run parallel config ``name``.

        Raise if a component or the repetition is absent from the context.
        """
        value = getattr(self, name)
        if value is None and name != 'run_parallel_config':
            raise RunContextError(
                name,
                f"No {name} is defined in the current run context. The "
                f"{name} is not chosen yet, e.g. in the `skip` or "
                "`get_data` of a component before it, or during "
                "`benchopt prepare`."
            )
        return value

    @cached_property
    def run_parallel_config(self):
        """Parallel config of the workers that run this run.

        With ``submitit``, the SLURM config of the jobs merged with the
        ``slurm_params`` of the solver, if it is chosen. None for a local run.

        It sets how the run is dispatched. It is computed once, on first use,
        so a collected run, which is not dispatched, does not need the backend
        installed. It is computed in the run context, as a ``slurm_params``
        property can use the components of the run.
        """
        config = self.parallel_config or {}
        if config.get('backend', 'loky') == 'loky':
            config = None
        elif config['backend'] == 'submitit':
            from ..parallel_backends.slurm_executor import (
                get_solver_slurm_config
            )
            # Keys of the parallel config that do not configure the backend.
            run_keys = ('backend', 'group_by', 'batch_n_jobs')
            slurm_config = {
                k: v for k, v in config.items() if k not in run_keys
            }
            if self.solver is not None:
                with self:
                    slurm_config = get_solver_slurm_config(
                        self.solver, slurm_config
                    )
            config = dict(backend='submitit', **slurm_config)
        return config

    def __enter__(self):
        components = [
            c for c in (self.dataset, self.objective, self.solver)
            if isinstance(c, RunContextMixin)
        ]
        self._previous.append([(c, c._run_context) for c in components])
        for c in components:
            c._run_context = self
        return self

    def __exit__(self, *exc):
        for c, previous in self._previous.pop():
            c._run_context = previous


# Components used by the last run in this process, from the dataset to the
# solver. Each one keeps its state (data, fitted state) while the next runs
# share it, and is released once a run does not.
_IN_USE = []


def use_components(*components):
    """Release the state of the last run's components not shared by this run.

    Called when a run starts in this process, or when the front node sends it
    to another process. The state of a component depends on the ones before
    it: the objective data on the dataset, the solver state on both. Called
    without components, it releases them all.
    """
    global _IN_USE
    for i, previous in enumerate(_IN_USE):
        if previous is not None and (i >= len(components) or any(
            a is not b for a, b in zip(_IN_USE[:i + 1], components)
        )):
            previous._release_state()
    _IN_USE = list(components)
