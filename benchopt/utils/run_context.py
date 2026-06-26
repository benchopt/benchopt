import re
import hashlib
from pathlib import Path
from dataclasses import dataclass, replace as dc_replace
from .run_context_mixin import RunContextMixin


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

    Holds everything needed to compute reproducible seeds, locate the
    per-run artifact directory, and carry runtime flags.  Set on each
    component (dataset, objective, solver) by the runner before any user
    method is called.  Excluded from the joblib cache key via
    ``__getstate__``; the cache is keyed on ``meta`` instead.

    Config fields (set once in ``_run_benchmark``):
        run_output_base, pdb

    Per-run fields (filled via ``dataclasses.replace`` in
    ``get_solver_kwargs`` for each dataset × objective × solver × rep):
        base_seed, objective_name, dataset_name, solver_name, repetition
    """
    # Config fields — set once per benchmark invocation
    run_output_base: Path | None = None
    pdb: bool = False
    # Per-run fields — cloned/updated for each (dataset, obj, solver, rep).
    # A field left as None means the corresponding component is not available
    # in this context (e.g. objective/solver/repetition during prepare) and
    # requesting its seed raises a clear error in get_seed.
    base_seed: str = ""
    objective_name: str | None = None
    dataset_name: str | None = None
    solver_name: str | None = None
    repetition: int | None = None

    def get_seed(self, class_name, use_objective=False, use_dataset=False,
                 use_solver=False, use_repetition=False):
        """Compute a deterministic integer seed for a given component."""
        repetition = None if self.repetition is None else str(self.repetition)
        use_flags = {
            "base_seed": (True, self.base_seed),
            "objective": (use_objective, self.objective_name),
            "dataset": (use_dataset, self.dataset_name),
            "solver": (use_solver, self.solver_name),
            "repetition": (use_repetition, repetition),
            "class": (True, class_name.lower()),
        }
        for component, (use, value) in use_flags.items():
            if use and value is None:
                raise ValueError(
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
            / _sanitize_path_component(self.dataset_name)
            / _sanitize_path_component(self.objective_name)
            / _sanitize_path_component(self.solver_name)
            / f"rep_{self.repetition}"
        )
        path.mkdir(parents=True, exist_ok=True)
        return path

    def set_run_context(self, objective, dataset, solver, repetition,
                        base_seed):
        """Clone base_ctx with per-run fields and assign to each component."""
        ctx = dc_replace(
            self,
            base_seed=str(base_seed),
            objective_name=str(objective),
            dataset_name=str(dataset),
            solver_name=str(solver),
            repetition=repetition,
        )
        ctx.attach(objective, dataset, solver)
        return ctx

    def attach(self, objective, dataset, solver):
        """Assign ctx to each run component."""
        for klass in [objective, dataset, solver]:
            if isinstance(klass, RunContextMixin):
                klass._run_context = self
