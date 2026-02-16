import hashlib


class SeedMixin:
    """Mixin class to manage random seed for reproducibility."""
    def __init__(self):
        super().__init__()
        # Tracks which components are used for the seed, uses
        # the most restrictive seed parameters for later caching.
        self._seed_params = {
            "use_objective": False,
            "use_dataset": False,
            "use_solver": False,
            "use_repetition": False
        }
        # We save the seed using the most restrictive seed parameters
        self._used_seed = None

    def _get_seed(
        self, use_objective, use_dataset,
        use_solver, use_repetition
    ):
        if not hasattr(self, "seed_dict"):
            from benchopt import BaseDataset, BaseObjective, BaseSolver
            msg = ""
            if isinstance(self, BaseDataset):
                msg = "Make sure to call get_seed from the get_data method."
            elif isinstance(self, BaseObjective):
                msg = (
                    "Make sure to call get_seed from the get_objective or "
                    " set_data methods."
                )
            elif isinstance(self, BaseSolver):
                msg = (
                    "Make sure to call get_seed from the set_objective method."
                )
            raise ValueError(
                f"seed_dict was not initialized for {self}. {msg}"
            )

        use_keys = {
            "base_seed": True,
            "objective": use_objective,
            "dataset": use_dataset,
            "solver": use_solver,
            "repetition": use_repetition,
            "class": True
        }
        hash_list = []
        for key in use_keys:
            if key not in self.seed_dict:
                raise ValueError(
                    f"Seed dict is not initialized correctly, "
                    f"missing {key} key."
                )
            elif use_keys[key]:
                hash_list.append(self.seed_dict[key])
            else:
                hash_list.append("*")

        hash_string = "_".join(hash_list)
        digest = hashlib.sha256(hash_string.encode()).hexdigest()
        seed = int(digest, 16) % (2**32 - 1)
        return seed

    def get_seed(
        self, use_objective=False, use_dataset=False,
        use_solver=False, use_repetition=False,
    ):
        """Get the random seed for this solver instance. Setting use_objective,
        use_dataset, use_solver or use_repetition to False will return a seed
        that is not affected by the corresponding component.
        The seed is computed by hashing the names of the components and
        the base seed. The seed is in the range [0, 2**32 - 1].
        """
        seed = self._get_seed(
            use_objective, use_dataset,
            use_solver, use_repetition
        )

        # We save the most restrictive seed parameters for later caching
        for key in self._seed_params:
            self._seed_params[key] |= locals()[key]

        self._used_seed = self._get_seed(**self._seed_params)

        return seed
