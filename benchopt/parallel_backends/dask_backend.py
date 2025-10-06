try:
    from dask.distributed import Client
except ImportError:
    raise ImportError(
        "To run benchopt with the dask backend, please install "
        "the `distributed` package: `pip install benchopt[dask]` or "
        "`pip install distributed`"
    )


def check_dask_config(config):
    # Setup the client with `dask_*` parameters
    cluster = config.pop('dask_cluster', 'local')
    dask_config = {
        key.replace("dask_", ""): config.pop(key) for key in list(config)
        if key.startswith('dask_')
    }
    if cluster == 'coiled':
        import coiled

        if 'n_jobs' in config:
            dask_config['n_workers'] = config.pop('n_jobs')
        if 'environment_file' in dask_config:
            # If we provide an environment file, we need to make sure the
            # software environment is created first.
            assert 'software' in dask_config, (
                "When 'coiled_environment_file' is provided, the name of the "
                "software environment must be provided through "
                "'coiled_software' as well."
            )
            coiled.create_software_environment(
                name=dask_config['software'],
                conda=dask_config.pop('environment_file')
            )

        # Setup the cluster using coiled with coiled_* parameters
        cluster = coiled.Cluster(**dask_config)
        config['client'] = cluster.get_client()
        return config

    if 'n_jobs' in config:
        dask_config['n_workers'] = config.pop('n_jobs')

    config['client'] = Client(**dask_config)

    return config
