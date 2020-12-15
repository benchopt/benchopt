from benchopt import BaseDataset
from benchopt import safe_import_context


with safe_import_context() as import_ctx:
    from sklearn.datasets import load_boston


class Dataset(BaseDataset):

    name = "Boston"

    install_cmd = 'conda'
    requirements = ['scikit-learn']

    def get_data(self):

        X, y = load_boston(return_X_y=True)

        data = dict(X=X, y=y)

        return X.shape[1], data
