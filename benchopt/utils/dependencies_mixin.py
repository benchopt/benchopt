import traceback

from ..config import RAISE_INSTALL_ERROR

from .class_property import classproperty
from .shell_cmd import _run_shell_in_conda_env
from .conda_env_cmd import install_in_conda_env
from .conda_env_cmd import shell_install_in_conda_env

from .terminal_output import colorify, YELLOW


class DependenciesMixin:
    # Information on how to install the class. The value of install_cmd should
    # be in {'conda', 'shell'}. The API reads:
    #
    # - 'conda': The class should have an attribute `requirements`.
    #          Benchopt will conda install `$requirements`, except for entries
    #          starting with `pip:` which will be installed with `pip` in the
    #          conda env.
    #
    # - 'shell': The solver should have attribute `install_script`. Benchopt
    #           will run `install_script` in a shell and provide the conda
    #           env directory as an argument. The command should then be
    #           installed in the `bin` folder of the env and can be imported
    #           with import_shell_cmd in the safe_import_context.
    install_cmd = "conda"

    _error_displayed = False

    @classproperty
    def benchmark(cls):
        return cls.__module__.split(".")[1]

    @classproperty
    def name(cls):
        return cls.__module__.split(".")[-1]

    @classproperty
    def install_cmd_(cls):
        if cls.install_cmd not in ["conda", "shell"]:
            raise ValueError(
                f"{cls.install_cmd} is not a valid install command. "
                "Please use 'conda' or 'shell' as install command."
            )
        return cls.install_cmd

    @classmethod
    def is_installed(cls, env_name=None, raise_on_not_installed=None,
                     quiet=False):
        """Check if the module caught a failed import to assert install.

        Parameters
        ----------
        env_name: str or None
            Name of the conda env where the install should be checked. If
            None, check the install in the current environment.
        raise_on_not_installed: boolean or None
            If set to True, raise an error if the requirements are not
            installed. This is mainly for testing purposes.
        quiet: boolean
            Hide import error information.

        Returns
        -------
        is_installed: bool
            returns True if no import failure has been detected.
        """
        if env_name is None:
            if cls._import_ctx.failed_import:
                exc_type, value, tb = cls._import_ctx.import_error
                if raise_on_not_installed:
                    raise exc_type(value).with_traceback(tb)
                if not cls._error_displayed and not quiet:
                    traceback.print_exception(exc_type, value, tb)
                    cls._error_displayed = True
                return False
            else:
                return True
        else:
            return (
                _run_shell_in_conda_env(
                    f"benchopt check-install {cls._benchmark_dir} "
                    f"{cls._module_filename} {cls._base_class_name}",
                    env_name=env_name,
                    raise_on_error=raise_on_not_installed,
                ) == 0
            )

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
        # Check that install_cmd is valid and if the cls is installed
        install_cmd_ = cls.install_cmd_
        is_installed = cls.is_installed(env_name=env_name)

        env_suffix = f" in '{env_name}'" if env_name else ""
        if force or not is_installed:
            print(f"- Installing '{cls.name}'{env_suffix}:...",
                  end="", flush=True)
            try:
                cls._pre_install_hook(env_name=env_name)
                if install_cmd_ == "conda":
                    if hasattr(cls, "requirements"):
                        install_in_conda_env(*cls.requirements,
                                             env_name=env_name,
                                             force=force)
                    else:
                        # get details of class
                        cls_type = cls.__base__.__name__.replace("Base", "")

                        raise AttributeError(
                            f"Could not find dependencies for {cls.name} "
                            f"{cls_type} while it is not importable. This is "
                            "probably due to missing dependency specification."
                            " The dependencies should be specified in class "
                            "attribute `requirements`.\n"
                            "Examples:\n"
                            "   requirements = ['pkg'] # conda package `pkg`\n"
                            "   requirements = ['chan:pkg'] # package `pkg` in"
                            "conda channel `chan`\n"
                            "   requirements = ['pip:pkg'] # pip package `pkg`"
                        )
                elif install_cmd_ == "shell":
                    install_file = (
                        cls._module_filename.parents[1] / "install_scripts"
                        / cls.install_script
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
            print(f"- '{cls.name}' already available{env_suffix}")

        return is_installed

    @classmethod
    def collect(cls, env_name=None, force=False):
        """Collect info for global installation of all classes in an env.

        Parameters
        ----------
        env_name: str or None
            Name of the conda env where the class should be installed. If
            None, tries to install it in the current environment.
        force : boolean (default: False)
            If set to True, forces reinstallation when using conda.

        Returns
        -------
        conda_requirements: list of str
            List of all requirements for this class.
        shell_install_script: str
            Name of the install script to run.
        post_install_hooks: list of callable
            Post install hooks if one need to be run.
        """
        # Check that install_cmd is valid and if the cls is installed
        install_cmd_ = cls.install_cmd_
        is_installed = cls.is_installed(env_name=env_name)

        missing_deps = None
        conda_reqs, shell_install_scripts, post_install_hooks = [], [], []
        if force or not is_installed:
            cls._pre_install_hook(env_name=env_name)
            if install_cmd_ == "shell":
                shell_install_scripts = [
                    cls._module_filename.parents[1] / "install_scripts"
                    / cls.install_script
                ]
            else:
                conda_reqs = getattr(cls, "requirements", [])
                if not is_installed and len(conda_reqs) == 0:
                    missing_deps = cls
            post_install_hooks = [cls._post_install_hook]
        else:
            env_suffix = f" in '{env_name}'" if env_name else ""
            colored_cls_name = colorify(cls.name, YELLOW)
            print(
                f"- {colored_cls_name} already available{env_suffix}\n"
                f"  No ImportError raised from {cls._module_filename}."
            )

        return (
            conda_reqs, shell_install_scripts, post_install_hooks, missing_deps
        )

    @classmethod
    def _pre_install_hook(cls, env_name=None):
        """Hook called before installing dependencies with conda or pip."""
        pass

    @classmethod
    def _post_install_hook(cls, env_name=None):
        """Hook called after installing dependencies with conda or pip."""
        pass
