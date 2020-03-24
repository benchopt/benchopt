from benchopt.base import BaseDataset

from benchopt.util import safe_import


with safe_import():
    from sklearn.datasets import load_boston
    from sklearn.preprocessing import StandardScaler


class Dataset(BaseDataset):

    name = "Boston"

    install_cmd = "pip"
    requirements = ['scikit-learn']
    requirements_import = ['sklearn']

    # List of parameters to generate the datasets. The benchmark will consider
    # the cross product for each key in the dictionary.
    parameters = {'standardized': [True]}

    def __init__(self, standardized=True):
        # Store the parameters of the dataset
        self.standardized = standardized

        # Pass parameters that will be used in Dataset name
        super().__init__(standardized=standardized)

    def get_data(self):

        X, y = load_boston(return_X_y=True)
        if self.standardized:
            scaler = StandardScaler().fit(X)
            X = scaler.transform(X)
        data = dict(X=X, y=y)

        return X.shape[1], data
