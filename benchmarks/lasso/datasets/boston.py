from sklearn.datasets import load_boston

from benchopt.base import BaseDataset


class Dataset(BaseDataset):

    name = "Boston"

    def get_data(self):

        X, y = load_boston(return_X_y=True)

        data = dict(X=X, y=y)

        return X.shape[1], data
