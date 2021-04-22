from ..config import RAISE_INSTALL_ERROR

from .class_property import classproperty
from .shell_cmd import _run_shell_in_conda_env
from .conda_env_cmd import install_in_conda_env
from .conda_env_cmd import shell_install_in_conda_env


class DependenciesMixin:
    # Information on how to install the class. The value of install_cmd should
    # be in {None, 'conda', 'shell'}. The API reads:
    #
    # - 'conda': The class should have an attribute `requirements`.
    #          BenchOpt will conda install `$requirements`, except for entries
    #          starting with `pip:` which will be installed with `pip` in the
    #          conda env.
    #
    # - 'shell': The solver should have attribute `install_script`. BenchOpt
    #           will run `install_script` in a shell and provide the conda
    #           env directory as an argument. The command should then be
    #           installed in the `bin` folder of the env and can be imported
    #           with import_shell_cmd in the safe_import_context.
    install_cmd = None

    @classproperty
    def benchmark(cls):
        return cls.__module__.split('.')[1]

    @classproperty
    def name(cls):
        return cls.__module__.split('.')[-1]

    @classmethod
    def is_installed(cls, env_name=None, raise_on_not_installed=None):
        """Check if the module caught a failed import to assert install.

        Parameters
        ----------
        env_name: str or None
            Name of the conda env where the install should be checked. If
            None, check the install in the current environment.
        raise_on_not_installed: boolean or None
            If set to True, raise an error if the requirements are not
            installed. This is mainly for testing purposes.

        Returns
        -------
        is_installed: bool
            returns True if no import failure has been detected.
        """
        if env_name is None:
            if (cls._import_ctx is not None
                    and cls._import_ctx.failed_import):
                if raise_on_not_installed:
                    exc_type, value, tb = cls._import_ctx.import_error
                    raise exc_type(value).with_traceback(tb)
                return False
            else:
                return True
        else:
            return _run_shell_in_conda_env(
                f"benchopt check-install {cls._module_filename} "
                f"{cls._base_class_name}",
                env_name=env_name, raise_on_error=raise_on_not_installed
            ) == 0

    @classmethod
    def install(cls, env_name=None, force=False):
        """Install the class in the given conda env.

        Parameters
        ----------
        env_name: str or None
            Name of the conda env where the class should be installed. If
            None, tries to install it in the current environment.
        force : boolean (default: False)
            If set to True, forces reinstallation when using conda.

        Returns
        -------
        is_installed: bool
            True if the class is correctly installed in the environment.
        """
        is_installed = cls.is_installed(env_name=env_name)

        env_suffix = f" in '{env_name}'" if env_name else ''
        if force or not is_installed:
            print(f"- Installing '{cls.name}'{env_suffix}:...",
                  end='', flush=True)
            try:
                cls._pre_install_hook(env_name=env_name)
                if cls.install_cmd == 'conda':
                    install_in_conda_env(*cls.requirements, env_name=env_name,
                                         force=force)
                elif cls.install_cmd == 'shell':
                    install_file = (
                        cls._module_filename.parents[1] / 'install_scripts' /
                        cls.install_script
                    )
                    shell_install_in_conda_env(install_file, env_name=env_name)
                cls._post_install_hook(env_name=env_name)

            except Exception as exception:
                if RAISE_INSTALL_ERROR:
                    raise exception

            is_installed = cls.is_installed(env_name=env_name)
            if is_installed:
                print(" done")
            else:
                print(" failed")
        else:
            print(f"- '{cls.name}' already available{env_suffix}",
                  flush=True)

        return is_installed

    @classmethod
    def _pre_install_hook(cls, env_name=None):
        """Hook called before installing dependencies with conda or pip."""
        pass

    @classmethod
    def _post_install_hook(cls, env_name=None):
        """Hook called after installing dependencies with conda or pip."""
        pass
