from benchopt.base import BaseDataset

from benchopt.util import safe_import


with safe_import():
    from sklearn.datasets import load_boston


class Dataset(BaseDataset):

    name = "Boston"

    install_cmd = 'conda'
    requirements = ['scikit-learn']
    requirements_import = ['sklearn']

    def get_data(self):

        X, y = load_boston(return_X_y=True)

        data = dict(X=X, y=y)

        return X.shape[1], data
