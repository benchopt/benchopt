.. _ml_benchmark:

Setting up an ML benchmark
==========================

Benchopt can be used to run benchmarks on machine learning problems. This page
explains the specificities of setting up a benchmark in this context.

Cross-validation
----------------

In order to evaluate the generalization performance of an estimator, a common
practice is to use cross-validation. In this context, the data is split into
several folds, and the estimator is trained on a subset of the folds, and
evaluated on the remaining fold. This process is repeated several times, and
the average performance is reported.

In benchopt, the cross-validation is handled as repeated run of the ``Solver``,
where the data is splitted into folds in ``Objective.get_objective``.
A typically workflow is the following:

.. code::python

    class Objective(BaseObjective):
        ...
        def set_data(self, X, y):
            self.X, self.y = X, y
            # Specify a cross-validation splitter as the ``cv`` attribute.
            # This will be automatically used in ``self.get_split`` to split
            # the arrays provided.
            self.cv = KFold(n_splits=5, shuffle=True, random_state=self.seed)

        def get_objective(self):
            # Call ``self.get_split`` with the arrays to split. This will be
            # called
            self.X_train, self.X_test, self.y_train, self.y_test = (
                self.get_split(self.X, self.y)
            )
            return dict(X=self.X_train, y=self.y_train)

Note that this workflow can fail for complex splitting strategies. In order to
cope with this, the ``Objective`` class can also implement a
``split(*array, *indexes)`` method that is used to split the array provided with
the indices output by the splitter:


.. code::python

    class Objective(BaseObjective):
        ...
        def split(self, *array, split_indexes=None):
            # Split all the arrays according to split_indexes and return them.
            train_index, test_index = split_indexes
            res = ()
            for x in arrays:
                res = (*res, x[train_index], x[test_index])
            return res


Note that by default, when ``Objective`` has a ``cv`` atribute, the number of
repetitions is set to ``cv.get_n_splits()`` instead of ``1``. When fewer number of repetitions is requested, only the first split are evaluted, while requesting more repetitions will loop over the split, repeating them to get the rigth number of repetitions. Note that depending on the number of repetitions,
some folds might be over represented in the final results.