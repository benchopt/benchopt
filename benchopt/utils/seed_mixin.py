import hashlib


class SeedMixin:
    """Mixin class to manage random seed for reproducibility."""
    def __init__(self):
        super().__init__()
        self.seed_params = {
            "use_objective": False,
            "use_dataset": False,
            "use_solver": False,
            "use_repetition": False
        }
        self.last_seed = None

    def _get_seed(
        self, use_objective, use_dataset,
        use_solver, use_repetition
    ):
        if not hasattr(self, "seed_dict"):
            raise ValueError(f"seed_dict was not initialized for {self}")

        use_keys = {
            "base_seed": True,
            "objective": use_objective,
            "dataset": use_dataset,
            "solver": use_solver,
            "repetition": use_repetition
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
        self, use_objective=True, use_dataset=True,
        use_solver=True, use_repetition=True,
    ):
        """Get the random seed for this solver instance. Setting use_objective,
        use_dataset, use_solver or use_repetition to False will return a seed
        that is not affected by the corresponding component.
        """
        seed = self._get_seed(
            use_objective, use_dataset,
            use_solver, use_repetition
        )

        # We save the most restrictive seed parameters to avoid recomputing
        # the seed if they are not changed.
        for key in self.seed_params:
            self.seed_params[key] = eval(key) or self.seed_params[key]

        self.last_seed = self._get_seed(**self.seed_params)

        return seed
