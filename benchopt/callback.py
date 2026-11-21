import os
import time
import pickle
import warnings

from .utils.sys_info import get_sys_info


def _dump(obj, path):
    """Pickle ``obj`` in ``path``, which is never left half written."""
    tmp_path = path.with_suffix(f".tmp{os.getpid()}")
    with open(tmp_path, 'wb') as f:
        pickle.dump(obj, f)
    os.replace(tmp_path, path)


def _load(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


class _Callback:
    """Callback class to monitor convergence.

    Parameters
    ----------
    objective : instance of BaseObjective
        The objective to minimize.
    solver : instance of BaseSolver
        The solver that is currently run. This allows to retrieve the results
        with :method:`benchopt.base.Solver.get_result` in the callback.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective and data names, problem dimension, etc.
    stopping_criterion : instance of StoppingCriterion
        Object to check if we need to stop a solver.
    run_context : RunContext | None
        Context of the run, to store and restore the checkpoints given to the
        callback. If None, the checkpoints are ignored.

    Attributes
    ----------
    objective : instance of BaseObjective
        The objective to minimize.
    stopping_criterion : StoppingCriterion
        Object to check if we need to stop a solver.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective and data names, problem dimension, etc.
    info : dict
        A dictionary with info from the current system.
    curve : list
        The convergence curve stored as a list of dict.
    status : 'running' | 'done' | 'diverged' | 'timeout' | 'max_runs'
        The status on which the solver is or was stopped.
    time_iter : float
        Computation time to reach the current iteration.
        Excluding the times to evaluate objective.
    it : int
        The number of times the callback has been called. It's
        initialized with 0.
    next_stopval : int
        The next iteration for which the curve should be
        updated.
    time_callback : float
        The time when exiting the callback call.
    """

    def __init__(self, objective, solver, meta, stopping_criterion,
                 run_context=None):
        self.objective = objective
        self.solver = solver
        self.meta = meta
        self.stopping_criterion = stopping_criterion
        self.run_context = run_context
        self._last_result = None

        # Folder of the checkpoints, None to ignore them.
        self._folder = None
        if run_context is not None and run_context.checkpoint_mode != 'off':
            self._folder = run_context.checkpoint_path / 'callback'
        # Whether the callback is only called to evaluate a checkpoint.
        self._scoring = False
        self._last_save = time.perf_counter()

        # Initialize local variables
        self.info = get_sys_info()
        self.curve = []
        self.status = 'running'
        self.it = 0
        self.time_iter = 0.
        self.next_stopval = self.stopping_criterion.init_stop_val()

    def start(self):
        self.time_callback = time.perf_counter()

    def __call__(self, checkpoint=None):
        """Evaluate the solver if needed and return False to stop it.

        Parameters
        ----------
        checkpoint : object | callable | None
            What the solver needs to restart from this call, or a function
            without argument that returns it. It is stored when the solver is
            evaluated and every ``checkpoint_interval`` seconds, and given
            back in ``solver.checkpoint_`` when the run is restarted.
        """
        if self._scoring:
            self.log_value()
            return False

        # Stop time and update computation time since the beginning
        t0 = time.perf_counter()

        self.time_iter += t0 - self.time_callback

        # Evaluate the iteration if necessary.
        evaluated = self.it == self.next_stopval
        stop = evaluated and self.log_value()
        if checkpoint is not None and self._folder is not None:
            self._save(checkpoint, evaluated)
        if stop:
            return False

        # Update iteration number and restart time measurement.
        self.it += 1
        self.time_callback = time.perf_counter()
        return True

    def _save(self, checkpoint, evaluated):
        """Store the checkpoint, with the state of the callback.

        An evaluated checkpoint is a point of the curve, kept in its own file
        with the curve of the run. Between two of them, the last checkpoint is
        stored from time to time to restart from it.
        """
        interval = time.perf_counter() - self._last_save
        if not evaluated and interval < self._setting('interval', 600):
            return
        self._folder.mkdir(parents=True, exist_ok=True)
        if callable(checkpoint):
            checkpoint = checkpoint()
        state = dict(
            checkpoint=checkpoint, it=self.it, time_iter=self.time_iter
        )
        name = f"point_{self.it}.pkl" if evaluated else "last.pkl"
        _dump(state, self._folder / name)
        if evaluated:
            self._save_curve()
            keep = self._setting('keep', 'all')
            if keep != 'all':
                for it in self._stored_points()[:-keep]:
                    (self._folder / f"point_{it}.pkl").unlink()
        self._last_save = time.perf_counter()

    def _setting(self, name, default):
        """Return ``checkpoint_<name>`` of the solver, then of the objective.
        """
        value = None
        for component in (self.objective, self.solver):
            value = getattr(component, f'checkpoint_{name}', value)
        return default if value is None else value

    def _save_curve(self):
        """Store the curve of the run, with the hash of what evaluated it."""
        _dump(
            dict(curve=self.curve,
                 objective_hash=type(self.objective)._file_hash),
            self._folder / f"curve_{self.run_context.run_id}.pkl"
        )

    def _stored_points(self):
        """Sorted iterations of the evaluated checkpoints that are stored."""
        return sorted(
            int(f.stem[len("point_"):])
            for f in self._folder.glob("point_*.pkl")
        )

    def restore(self):
        """Restore the run from its checkpoints; return False if it is done.

        The points of the curve are taken from the curve stored for this run,
        or evaluated from their checkpoint when they are not in it. With
        ``--checkpoint rescore``, the stored curve is ignored. The last point
        is always evaluated, to get the result of the solver. The solver then
        restarts from the last checkpoint.
        """
        points = [] if self._folder is None else self._stored_points()
        if not points:
            return True

        rescore = self.run_context.checkpoint_mode == 'rescore'
        curve_file = self._folder / f"curve_{self.run_context.run_id}.pkl"
        stored = {}
        if curve_file.exists():
            curve = _load(curve_file)
            for row in curve['curve']:
                stored.setdefault(row['stop_val'], []).append(row)
            new_hash = type(self.objective)._file_hash
            if not rescore and curve['objective_hash'] != new_hash:
                warnings.warn(
                    f"The objective changed since {self.solver} was "
                    "evaluated on its checkpoints. The stored evaluations "
                    "are kept. Use `--checkpoint rescore` to compute them "
                    "again.", UserWarning
                )
        n_points = len(set(stored) | set(points))
        if rescore:
            stored = {}

        n_scored, stop = 0, False
        for it in sorted(set(stored) | set(points)):
            if it in stored and it != points[-1]:
                self.curve.extend(stored[it])
                stop, self.status, self.next_stopval = (
                    self.stopping_criterion.should_stop(it, self.curve)
                )
                continue
            state = _load(self._folder / f"point_{it}.pkl")
            self.it, self.time_iter = it, state['time_iter']
            self.next_stopval = it
            self.run_context.checkpoint = state['checkpoint']
            self._scoring = True
            self.solver.run(self)
            self._scoring = False
            stop = self.status != 'running'
            n_scored += 1
        self._save_curve()

        # Restart from the last checkpoint if it is after the last point.
        last_file = self._folder / "last.pkl"
        if not stop and last_file.exists():
            last = _load(last_file)
            if last['it'] > self.it:
                self.it, self.time_iter = last['it'], last['time_iter']
                self.run_context.checkpoint = last['checkpoint']
        action = "done at" if stop else "resumed from"
        print(
            f"{self.solver}: {action} iteration {self.it}, with {n_scored} "
            f"of {n_points} points evaluated from the checkpoints."
        )
        return not stop

    def log_value(self):
        """Store the objective value with running time and stop if needed.

        Return True if the solver should be stopped.
        """
        self._last_it_log = self.it
        result = self.solver.get_result()
        self._last_result = result
        objective_list = self.objective(result)
        self.curve.extend(dict(
            **self.meta, stop_val=self.it,
            time=self.time_iter,
            **objective_dict, **self.info
        ) for objective_dict in objective_list)

        # Check the stopping criterion
        should_stop_res = self.stopping_criterion.should_stop(
            self.next_stopval, self.curve
        )
        stop, self.status, self.next_stopval = should_stop_res
        return stop

    def get_results(self):
        """Get the results stored by the callback

        Returns
        -------
        curve : list
            Details on the run and the objective value obtained.
        status : 'done' | 'diverged' | 'timeout' | 'max_runs'
            The status on which the solver was stopped.
        """
        if self.status == 'running':
            # If we reach this point, this means that the solver has returned
            # before the stopping criterion was met. Evaluate the results one
            # last time before returning if the last log was not the previous
            # iteration.
            # Stop time and update computation time since the beginning
            t0 = time.perf_counter()
            self.time_iter += t0 - self.time_callback
            if self._last_it_log != self.it - 1:
                self.log_value()
            # Update the status to done
            self.status = 'done'
        return self.curve, self.status, self._last_result
