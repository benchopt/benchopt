import hashlib


def get_seed(seed_dict, use_objective, use_dataset,
             use_solver, use_repetition):
    use_keys = {
        "base_seed": True,
        "objective": use_objective,
        "dataset": use_dataset,
        "solver": use_solver,
        "repetition": use_repetition
    }
    hash_list = []
    for key in use_keys:
        if key not in seed_dict:
            raise ValueError(f"Seed dict is not initialized correctly, "
                             f"missing {key} key.")
        elif use_keys[key]:
            hash_list.append(seed_dict[key])
        else:
            hash_list.append("*")

    hash_string = "_".join(hash_list)
    digest = hashlib.sha256(hash_string.encode()).hexdigest()
    seed = int(digest, 16) % (2**32 - 1)
    return seed


class SeedMixin:
    """Mixin class to manage random seed for reproducibility."""

    def get_seed(
        self, use_objective=True, use_dataset=True,
        use_solver=True, use_repetition=True,
    ):
        """Get the random seed for this solver instance. Setting use_objective,
        use_dataset, use_solver or use_repetition to False will return a seed
        that is not affected by the corresponding component.
        """
        if not hasattr(self, "seed_dict"):
            raise ValueError(f"seed_dict was not initialized for {self}")

        return get_seed(
            self.seed_dict, use_objective, use_dataset,
            use_solver, use_repetition
        )
