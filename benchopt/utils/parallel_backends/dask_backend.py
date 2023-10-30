

def check_dask_config(config, backend):
    # Setup the client with `dask_*` parameters
    client_config = {
        k[5:]: config.pop(k) for k, v in list(config.items())
        if k.startswith('dask_')
    }
    coiled_config = {
        k[7:]: config.pop(k) for k, v in list(config.items())
        if k.startswith('coiled_')
    }
    if len(coiled_config) > 0:
        # Setup the cluster using coiled with coiled_* parameters
        if 'n_jobs' in config:
            coiled_config['n_workers'] = config.pop('n_jobs')
        import coiled
        cluster = coiled.Cluster(**coiled_config)
        client_config['cluster'] = cluster

    if 'n_jobs' in config:
        client_config['n_workers'] = config.pop('n_jobs')

    from distributed import Client
    config['client'] = Client(**client_config)

    return config
