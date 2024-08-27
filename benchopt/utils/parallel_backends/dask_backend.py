

def check_dask_config(config, backend):
    # Setup the client with `dask_*` parameters
    cluster = config.pop('dask_cluster', 'local')
    dask_config = {
        k[5:]: config.pop(k) for k, v in list(config.items())
        if k.startswith('dask_')
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

    from distributed import Client
    config['client'] = Client(**dask_config)

    return config
