.. _tweak_datasets:

Tweak a dataset
===============

Paths to data files:
--------------------

For benchmark users
~~~~~~~~~~~~~~~~~~~

If the benchmark maker allows you to customize the path to the data files,
you can modify the benchmark's configuration file with the keys `data_home` and `data_paths`.
The `data_home` key allows you to define a home path where the benchmark will search data files defined in `data_paths`.
The default value for `data_home` is the benchmark directory.
The `data_paths` define paths for each file needed by the benchmark. For instance :

.. code-block:: yaml

    data_home: /path/to/data_home/folder
    data_paths:
        the_key: /path/to/the/file.ext

With this config, the benchmark will retrieve the file located in `/path/to/data_home/folder/path/to/the/file.ext`

To know which keys are needed, please refer to the benchmark documentation.

For benchmark makers
~~~~~~~~~~~~~~~~~~~~

You can use **path configuration** to allow benchmark's users to customize the path to the data files.
Benchopt provides a function `config.get_data_path(key)` that can be used to retrieve user's custom paths that have been filled in config.

.. code-block:: python

    from benchopt import config

    [...]

    class Dataset(BaseDataset):

    [...]

        def get_data(self):
            path = config.get_data_path(key="the_key_name")

The benchmark's user can now update his config file with the following content :

.. code-block:: yaml

    data_paths:
        the_key_name: path/to/file.ext

The variable `path` will contain `{benchmark_dir}/path/to/file.ext`.
