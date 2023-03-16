from benchopt import BaseDataset


class Dataset(BaseDataset):

    name = "simulated"

    parameters = {
        'a, b': [
            (5, 3)
        ]
    }

    def __init__(self, a=1, b=1):
        self.a, self.b = a, b

    def get_data(self):
        return dict(a=self.a, b=self.b)
