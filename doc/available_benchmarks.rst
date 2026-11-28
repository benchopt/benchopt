.. _available_benchmarks:

Available benchmarks
====================

.. _featured_benchmarks:

Featured benchmarks
-------------------

Reproducing an existing benchmark should be as easy as running the following commands:

.. tab-set::

   .. tab-item:: NanoGPT

      A benchmark comparing various optimizers on training ``NanoGPT`` models.

      .. prompt:: bash $

         git clone https://github.com/benchopt/benchmark_nanogpt.git
         benchopt run benchmark_nanogpt

      which will produce an interactive HTML report to visualize the results.

      .. raw:: html

         <iframe class="benchmark_result"
               src="https://benchopt.github.io/results/benchmark_nanogpt_benchmark_nanogpt_benchopt_run_2025-10-31_13h48m48.html"
            frameBorder='0' style="position: relative; width: 100%;">
         </iframe>

   .. tab-item:: Unsupervised Domain Adaptation

      A benchmark comparing various methods for unsupervised domain adaptation.

      .. prompt:: bash $

         git clone https://github.com/scikit-adaptation/skada-bench.git
         benchopt run skada-bench --config configs/Simulated.yml --no-plot

      which will produce a parquet file with the results that can be visualized
      using instruction on the ``README.md`` of the https://github.com/scikit-adaptation/skada-bench.

   .. tab-item:: Minimal benchmark

      A minimal benchmark comparing various solvers on a toy problem.

      .. prompt:: bash $

         benchopt run examples/minimal_benchmark

      which will produce an interactive HTML report to visualize the results.

      .. raw:: html

         <iframe class="benchmark_result"
               src="auto_examples/html_results/sphx_glr_run_minimal_benchmark_002.html"
            frameBorder='0' style="position: relative; width: 100%;">
         </iframe>


These different tabs illustrate the diversity of benchmarks that can be built
with benchopt, from deep learning optimization to more classical machine
learning tasks.


More benchmarks
---------------

.. note::
    Some benchmarks are briefly described in the list below. For a complete
    list of benchmarks, see GitHub repositories of the form `benchopt/benchmark_*
    <https://github.com/orgs/benchopt/repositories?q=benchmark_&type=all&language=&sort=stargazers/>`_.

**Notation:**  In what follows, :math:`n` (or ``n_samples``) stands for the number of samples and :math:`p` (or ``n_features``) stands for the number of features.

.. math::

 y \in \mathbb{R}^n, X = [x_1^\top, \dots, x_n^\top]^\top \in \mathbb{R}^{n \times p}

- `Ordinary Least Squares (OLS) <https://github.com/benchopt/benchmark_ols>`_: |Build Status OLS|

.. math::

    \min_w \frac{1}{2} \|y - Xw\|^2_2

- `Non-Negative Least Squares (NNLS) <https://github.com/benchopt/benchmark_nnls>`_: |Build Status NNLS|

.. math::

    \min_{w \geq 0} \frac{1}{2} \|y - Xw\|^2_2

- `LASSO: L1-regularized least squares <https://github.com/benchopt/benchmark_lasso>`_: |Build Status Lasso|

.. math::

    \min_w \frac{1}{2} \|y - Xw\|^2_2 + \lambda \|w\|_1

- `L2-regularized logistic regression <https://github.com/benchopt/benchmark_logreg_l2>`_: |Build Status LogRegL2|

.. math::

    \min_w \sum_{i=1}^{n} \log(1 + \exp(-y_i x_i^\top w)) + \frac{\lambda}{2} \|w\|_2^2

- `L1-regularized logistic regression <https://github.com/benchopt/benchmark_logreg_l1>`_: |Build Status LogRegL1|

.. math::

    \min_w \sum_{i=1}^{n} \log(1 + \exp(-y_i x_i^\top w)) + \lambda \|w\|_1

- `L2-regularized Huber regression <https://github.com/benchopt/benchmark_huber_l2>`_: |Build Status HuberL2|

.. math::

  \min_{w, \sigma} {\sum_{i=1}^n \left(\sigma + H_{\epsilon}\left(\frac{X_{i}w - y_{i}}{\sigma}\right)\sigma\right) + \lambda \|w\|_2^2}

where

.. math::

  H_{\epsilon}(z) = \begin{cases}
         z^2, & \text {if } |z| < \epsilon, \\
         2\epsilon|z| - \epsilon^2, & \text{otherwise}
  \end{cases}

- `L1-regularized quantile regression <https://github.com/benchopt/benchmark_quantile_regression>`_: |Build Status QuantileRegL1|

.. math::
    \min_{w} \frac{1}{n} \sum_{i=1}^{n} PB_q(y_i - X_i w) + \lambda ||w||_1

where :math:`PB_q` is the pinball loss:

.. math::
    PB_q(t) = q \max(t, 0) + (1 - q) \max(-t, 0) =
    \begin{cases}
        q t, & t > 0, \\
        0,    & t = 0, \\
        (q - 1) t, & t < 0
    \end{cases}

- `Linear ICA <https://github.com/benchopt/benchmark_linear_ica>`_: |Build Status LinearICA|

Given some data :math:`X  \in \mathbb{R}^{d \times n}` assumed to be linearly
related to unknown independent sources :math:`S  \in \mathbb{R}^{d \times n}` with

.. math::
    X = A S

where :math:`A  \in \mathbb{R}^{d \times d}` is also unknown, the objective of
linear ICA is to recover :math:`A` up to permutation and scaling of its columns.
The objective in this benchmark is related to some estimation on :math:`A`
quantified with the so-called AMARI distance.

- `Approximate Joint Diagonalization (AJD) <https://github.com/benchopt/benchmark_jointdiag>`_: |Build Status JointDiag|

Given n square symmetric positive matrices :math:`C^i`, it consists of solving
the following problem:

.. math::
    \min_B \frac{1}{2n} \sum_{i=1}^n \log |\textrm{diag} (B C^i B^{\top}) | - \log | B C^i B^{\top} |

where :math:`|\cdot|` stands for the matrix determinant and :math:`\textrm{diag}` stands
for the operator that keeps only the diagonal elements of a matrix. Optionally, the
matrix :math:`B` can be enforced to be orthogonal.

See `benchmark_* repositories on GitHub <https://github.com/orgs/benchopt/repositories?q=benchmark_+sort%3Aname-asc>`_ for more.


.. |Build Status OLS| image:: https://github.com/benchopt/benchmark_ols/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_ols/actions
.. |Build Status NNLS| image:: https://github.com/benchopt/benchmark_nnls/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_nnls/actions
.. |Build Status Lasso| image:: https://github.com/benchopt/benchmark_lasso/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_lasso/actions
.. |Build Status LogRegL2| image:: https://github.com/benchopt/benchmark_logreg_l2/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_logreg_l2/actions
.. |Build Status LogRegL1| image:: https://github.com/benchopt/benchmark_logreg_l1/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_logreg_l1/actions
.. |Build Status HuberL2| image:: https://github.com/benchopt/benchmark_huber_l2/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_huber_l2/actions
.. |Build Status QuantileRegL1| image:: https://github.com/benchopt/benchmark_quantile_regression/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_quantile_regression/actions
.. |Build Status LinearSVM| image:: https://github.com/benchopt/benchmark_linear_svm_binary_classif_no_intercept/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_linear_svm_binary_classif_no_intercept/actions
.. |Build Status LinearICA| image:: https://github.com/benchopt/benchmark_linear_ica/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_linear_ica/actions
.. |Build Status JointDiag| image:: https://github.com/benchopt/benchmark_jointdiag/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_jointdiag/actions
