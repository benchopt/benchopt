from sklearn.datasets import load_boston

from benchopt.base import BaseDataset


class Dataset(BaseDataset):

    name = "Boston"

    parameters = {
        'reg': [.01, .1, .5]
    }

    def __init__(self, reg=.1):
        self.reg = reg

        super().__init__(reg=reg)

    def get_loss_parameters(self):

        X, y = load_boston(return_X_y=True)

        lmbd = self.reg * self._get_lmbd_max(X, y)

        loss_parameters = dict(X=X, y=y, lmbd=lmbd)

        return X.shape[1], loss_parameters

    def _get_lmbd_max(self, X, y):
        return abs(X.T.dot(y)).max()
