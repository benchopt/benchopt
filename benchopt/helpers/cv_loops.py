
from abc import abstractmethod
from benchopt import BaseSolver, BaseObjective, safe_import_context

with safe_import_context() as import_ctx:
    import os
    from sklearn.base import clone
    from sklearn.model_selection import GridSearchCV
    from sklearn.model_selection import ShuffleSplit
    from sklearn.dummy import DummyClassifier
    from sklearn.metrics import get_scorer


class NestedCVObjective(BaseObjective):
    """Nested CV objective to run an inner CV per solver and return CV scores."""

    requirements = [
        'scikit-learn'
    ]

    # Public API

    def get_scoring(self):
        return None

    def get_inner_cv(self):
        return ShuffleSplit(n_splits=10, test_size=0.2, random_state=0)

    def get_outer_cv(self):
        return ShuffleSplit(n_splits=10, test_size=0.2, random_state=1)

    # Internal helpers

    def set_data(self, X, y):
        self.X, self.y = X, y

        self.cv = self.get_outer_cv()
        self.scoring = self.get_scoring()
        self.scorer = get_scorer(self.scoring)

    def get_objective(self):

        (
            self.X_train, self.X_test,
            self.y_train, self.y_test
        ) = self.get_split(self.X, self.y)

        return dict(
            X=self.X_train,
            y=self.y_train,
            sample_weight=self.sample_weight,
            cv=self.get_inner_cv(),
            scoring=self.scoring,
        )

    def evaluate_result(self, best_score, best_params, best_estimator, cv_results):
        "Only return cv scores, best_score, best_params, best_estimator and results"

        test_scores = self.scorer(best_estimator, self.X_test, self.y_test)
        train_scores = self.scorer(best_estimator, self.X_train, self.y_train)
        if not isinstance(test_scores, dict):
            test_scores = {'score': test_scores}
            train_scores = {'score': train_scores}
        res = {
            'cv_score': best_score,
            'best_params': best_params,
            'cv_results': cv_results,
            **{f"test_{k}": v for k, v in test_scores.items()},
            **{f"train_{k}": v for k, v in train_scores.items()},
        }

        return res

    def get_one_result(self, solver, n_iter):
        "Run the cross-validation search for a given solver."

        res = {
            'value': 0,
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

    @abstractmethod
    def get_estimator(self):
        """Return an estimator compatible with the `sklearn.GridSearchCV`."""
        pass

    def set_objective(self, X, y, sample_weight, cv, scoring):
        """Set the objective to run the cross-validation search."""

        self.X, self.y, self.sample_weight = X, y, sample_weight
        self.cv, self.scoring = cv, scoring

        self.estimator = clone(self.get_estimator())

        if 'SLURM_CPUS_PER_TASK' in os.environ:
            n_jobs = int(os.environ['SLURM_CPUS_PER_TASK'])
        else:
            n_jobs = 1

        # create grid search
        self.clf = GridSearchCV(
            self.estimator, self.param_grid, cv=self.cv, scoring=self.scoring,
            n_jobs=n_jobs
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

        return {
            'best_score': self.best_score,
            'best_params': self.best_params,
            'best_estimator': self.best_estimator,
            'cv_results': self.cv_results,
        }
