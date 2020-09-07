from benchopt.base import BaseDataset

from benchopt.util import safe_import_context


with safe_import_context() as import_ctx:
    from sklearn.datasets import load_boston
    from sklearn.preprocessing import StandardScaler


class Dataset(BaseDataset):

    name = "Boston"

    install_cmd = 'conda'
    requirements = ['scikit-learn']

    # List of parameters to generate the datasets. The benchmark will consider
    # the cross product for each key in the dictionary.
    parameters = {'standardized': [True]}

    def __init__(self, standardized=True):
        # Store the parameters of the dataset
        self.standardized = standardized

    def get_data(self):

        X, y = load_boston(return_X_y=True)
        if self.standardized:
            scaler = StandardScaler().fit(X)
            X = scaler.transform(X)
        data = dict(X=X, y=y)

        return X.shape[1], data
