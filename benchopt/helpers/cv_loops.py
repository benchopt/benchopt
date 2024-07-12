
from benchopt import BaseSolver, BaseObjective, safe_import_context

with safe_import_context() as import_ctx:
    import os
    from sklearn.base import clone
    from sklearn.model_selection import GridSearchCV
    from sklearn.model_selection import KFold
    from sklearn.dummy import DummyClassifier


class SimpleCVObjective(BaseObjective):
    """Simple CV objective to run an inner CV per solver and return CV scores."""

    requirements = [
        'pip:scikit-learn'
    ]

    # default parameters for the cross-validation
    cv_class = Kfold
    cv_params = {
        'n_splits': 5,
        'shuffle': False
    }
    scoring = None

    def set_data(self, X, y, sample_weight=None):
        self.X, self.y, self.sample_weight = X, y, sample_weight

    def get_objective(self):

        return dict(
            X=self.X,
            y=self.y,
            sample_weight=self.sample_weight,
            cv=self.cv_class,
            cv_params=self.cv_params,
            scoring=self.scoring
        )

    def evaluate_result(best_score, best_params, best_estimator, cv_results):
        "Only return cv scores, best_score, best_params, best_estimator and results"

        res = {'value': best_score,
               'best_score': best_score,
               'best_params': best_params,
               'best_estimator': best_estimator,
               'cv_results': cv_results,
               }

        return res

    def get_one_result(self, solver, n_iter):
        "Run the cross-validation search for a given solver."

        res = {'value': 0,
               'best_score': 0,
               'best_params': {},
               'best_estimator': DummyClassifier(),
               'cv_results': {},
               }

        return res


class CVSolver(BaseSolver):

    # ML task so run once
    sampling_strategy = "run_once"

    # param_grid to search over
    param_grid = {}

    if 'SLURM_CPUS_PER_TASK' in os.environ:
        n_jobs = int(os.environ['SLURM_CPUS_PER_TASK'])
    else:
        n_jobs = 1

    @abstractmethod
    def get_estimator(self):
        """Return an estimator compatible with the `sklearn.GridSearchCV`."""
        pass

    def set_objective(self, X, y, sample_weight, cv, cv_params, scoring):
        """Set the objective to run the cross-validation search."""

        self.X, self.y, self.sample_weight = X, y, sample_weight
        self.cv, self.cv_params, self.scoring = cv, cv_params, scoring

        self.estimator = clone(self.get_estimator())

        # create splitter
        self.cv = self.cv_class(**self.cv_params)

        # create grid search
        self.clf = GridSearchCV(
            self.estimator, self.param_grid, cv=self.cv, scoring=self.scoring,
            n_jobs=self.n_jobs
        )

    def run(self, n_iter):
        "returns all the results of the cross-validation search."

        self.clf.fit(
            self.X,
            self.y,
            sample_weight=self.sample_weight
        )

        self.best_params = self.clf.best_params_
        self.best_score = self.clf.best_score_
        self.cv_results = self.clf.cv_results_
        self.best_estimator = self.clf.best_estimator_

        res = {
            'best_score': self.best_score,
            'best_params': self.best_params,
            'best_estimator': self.best_estimator,
            'cv_results': self.cv_results,
        }

        return res
