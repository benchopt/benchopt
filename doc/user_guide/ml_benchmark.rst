.. _ml_benchmark:

Setting up an ML benchmark
==========================

Benchopt can be used to run benchmarks on machine learning problems. This page
explains the specificities of setting up a benchmark in this context.

To easily get started with a new ML benchmark, we recommend using the dedicated
``benchopt``'s `ML template <https://github.com/benchopt/template_benchmark_ml>`_ from github.
This template provides a simple structure, with the different benchopt's options set to accommodate ML workflows.


Disabling performance curves
----------------------------

Unlike optimization benchmarks where you track convergence over iterations,
ML benchmarks typically evaluate each solver once to completion. To disable
performance curve sampling, set ``sampling_strategy = "run_once"`` in your
``Objective`` class:

.. code-block:: python

    class Objective(BaseObjective):
        sampling_strategy = "run_once"

        # ...rest of your objective definition

With this setting, each solver's ``run`` method is called exactly once, and
the ``stop_val`` argument can be ignored. This is the recommended setup for
benchmarks comparing methods where only the final performance matters.

.. note::
   You can also set ``sampling_strategy = "run_once"`` on individual ``Solver``
   classes if only some solvers should run once while others need iterative
   evaluation.

Note that when using ``sampling_strategy = "run_once"``, ``evaluate_result``
will be called only once per solver run, and the resulting metrics will be
stored directly in the benchmark results. It is also possible to different
evaluation as different lines in the benchmark results by returning multiple
dictionaries from ``evaluate_result`` as a list. See :ref:`multiple_evaluation`
for more details.


Cross-validation
----------------

In order to evaluate the generalization performance of a method, a common
practice is to use cross-validation. In this context, the data is split
several times, and the model is trained on a subset of the data and evaluated
on another independent subset. This process is repeated several times, and
the average performance is reported.

In benchopt, cross-validation is handled as separate runs of the ``Solver``,
where the data is split into folds in ``Objective.get_objective``, by calling
``Objective.get_split``. This method takes in the data to split (typically
``numpy`` arrays or ``pandas`` dataframes) and returns the split data.
The way the splits are defined depends on the ``Objective.cv`` attribute, which
must be defined by the user. A typical workflow is the following:

.. code-block:: python

    class Objective(BaseObjective):
        ...
        def set_data(self, X, y):
            self.X, self.y = X, y
            # Specify a cross-validation splitter as the `cv` attribute.
            # This will be automatically used in `self.get_split` to split
            # the arrays provided.
            self.cv = GroupKFold(n_splits=5, random_state=self.seed)

            # If the cross-validation requires some metadata, it can be
            # provided in the `cv_metadata` attribute. This will be passed
            # to `self.cv.split` and `self.cv.get_n_splits`.
            self.cv_metadata = {"groups": self.X[:, 0]}

        def get_objective(self):
            # Call `self.get_split` with the arrays to split.
            # This method's default behavior is similar to sklearn's
            # `train_test_split`, splitting the input arrays using
            # the indexes returned by `self.cv.split`.
            self.X_train, self.X_test, self.y_train, self.y_test = \
                    self.get_split(self.X, self.y)
            return dict(X=self.X_train, y=self.y_train)

Note that by default, when ``Objective`` has a ``cv`` attribute, the number of
repetitions is set to ``cv.get_n_splits()`` instead of ``1``.
When fewer repetitions are requested, only the first splits are evaluated.
On the contrary, requesting more repetitions than splits will loop over
the splits, repeating them to get the right number of runs.
Note that depending on the number of repetitions requested, some folds may be
overrepresented in the final results.

The default workflow works for arrays that can be split based on indexing.
When the objects to split are more complex -- typically with deep learning
datasets-- it is also possible to implement a custom ``split(cv_fold, *obj)``
method in ``Objective`` to specify how to construct the split data:


.. code-block:: python

    class Objective(BaseObjective):
        ...
        def split(self, cv_fold, dataset, y):
            # Split all the arrays according to cv_fold and return them.
            train_index, test_index = cv_fold
            train_dataset = Subset(dataset, train_index)
            test_dataset = Subset(dataset, test_index)
            return train_dataset, test_dataset, y[train_index], y[test_index]

The ``cv_fold`` argument correspond to the current iterate from ``cv.split``,
while ``dataset, y`` corresponds to objects passed in ``Objective.get_split``.
