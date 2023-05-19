import random
from pathlib import Path
from contextlib import contextmanager


WORDS_URL = (
    'https://raw.githubusercontent.com/dwyl/english-words/'
    'master/words_dictionary.json'
)


def generate_id(seed, n_words=2):
    """Generate a n_words Id based on a given non-mutable seed."""
    # If not present, download and preprocess a list of english words.
    word_list = Path("~/.cache/benchopt/word_list.txt").expanduser()
    if not word_list.exists():
        from urllib.request import urlopen
        word_list.parent.mkdir(exist_ok=True)
        with urlopen(WORDS_URL) as f:
            # List english words
            words = [
                s.decode().split(":")[0].split()[0][1:-1]
                for s in f.readlines() if 16 > len(s) > 12
            ]
            word_list.write_text("\n".join(words))
    else:
        words = word_list.read_text().splitlines()

    rng = random.Random(seed)
    N_WORDS = len(words)
    name = "-".join([words[rng.randint(0, N_WORDS)] for _ in range(n_words)])
    return name


@contextmanager
def wandb_ctx(meta, wandb):
    """Context manager to init and close wandb logging.

    This yields a callback that can be used to log the objective in wandb.

    Parameters
    ----------
    meta : dict
        Meta data on the benchmark run. Used to setup the run names and stored
        as the run configuration.
    wandb : bool
        If set to False, this context does nothing and return None. Else, setup
        wandb and returns a callback to log the information to wandb.
    """
    if not wandb:
        yield None
        return

    try:
        import wandb as wb
    except ImportError:
        raise ImportError(
            "To be able to use wandb, please install and configure it. "
            "See first step in https://wandb.ai/quickstart/python-script."
        )
    try:
        assert wb.login()
    except (wb.errors.UsageError, AssertionError):
        raise RuntimeError(
            "wandb is not setup. Need to run `wandb login` to allow for wandb "
            "reports upload."
        )

    try:
        # In order to get separate plots for different datasets and objectives,
        # group the metric based on a tag. This separates each setup in
        # different pannels.
        tag = f'{meta["data_name"]}/{meta["objective_name"]}'
        # In order to make it easy to navigate the different pannels, we group
        # the run by common tags (i.e. couple of data and objective names), and
        # we add tag to simplify filtering the results.
        # For tags and group, we cannot use directly the names as the length
        # of these fields are limited. We thus generate reasonable length
        # two-word identifiers with `generate_id`.
        run = wb.init(
            project=meta['benchmark_name'], name=meta['solver_name'],
            group=generate_id(tag), job_type=meta['solver_name'], tags=[
                generate_id(meta["data_name"]),
                generate_id(meta["objective_name"])
            ], config=meta, reinit=True,
        )

        # Callback to be called in the runner.
        def cb(objective_dict):
            # Remove the leading "objective_" from the column name. Also log
            # the time and stop_val
            run.log({
                f'{tag}/{k.replace("objective_", "")}': v
                for k, v in objective_dict.items()
                if k.startswith('objective') or k in ["time", "stop_val"]
            })

        yield cb
    finally:
        run.finish(quiet=True)
