from benchopt import BaseDataset
from benchopt import safe_import_context

with safe_import_context() as import_ctx:
    # your dependencies here
    pass


class Dataset(BaseDataset):
    name = "{name}"

    def __init__(self):
        pass

    def get_data(self):
        return dict()
