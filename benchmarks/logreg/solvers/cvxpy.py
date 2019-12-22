import cvxpy as cp

from benchopt.base import BaseSolver

# Hack cvxpy to allow for non-error on reaching max_iter
cp.reductions.solvers.conic_solvers.ECOS.STATUS_MAP[-1] = 'optimal_inaccurate'


class Solver(BaseSolver):
    name = 'cvxpy'

    def set_loss(self, loss_parameters):

        self.X, self.y, self.lmbd = loss_parameters

        n_features = self.X.shape[1]
        self.beta = cp.Variable(n_features)

        loss = cp.sum(cp.logistic(-cp.multiply(self.y, self.X*self.beta)))
        self.problem = cp.Problem(cp.Minimize(
            loss + self.lmbd * cp.norm(self.beta, 1)))

        # log_likelihood = cp.sum(
        #     cp.multiply(y, X @ self.beta) - cp.logistic(X @ self.beta)
        # )
        # self.problem = cp.Problem(cp.Maximize(
        #     log_likelihood / n_features - self.lmbd * cp.norm(self.beta, 1)))

    def run(self, n_iter):
        self.problem.solve(max_iters=n_iter, verbose=False)

    def get_result(self):
        return self.beta.value
