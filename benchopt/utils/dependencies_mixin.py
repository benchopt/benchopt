import traceback

from ..config import RAISE_INSTALL_ERROR

from .class_property import classproperty
from .env_management import get_backend

from .terminal_output import colorify, RED, BLUE, GREEN, YELLOW, TICK, CROSS
RED_CROSS = colorify(CROSS, RED)
GREEN_TICK = colorify(TICK, GREEN)


class DependenciesMixin:
    # Information on how to install the class. The value of install_cmd should
    # be in {'conda', 'shell'}. The API reads:
    #
    # - 'conda': The class should have an attribute `requirements`.
    #          Benchopt will conda install `$requirements`, except for entries
    #          starting with `pip::` which will be installed with `pip` in the
    #          conda env.
    #
    # - 'shell': The solver should have attribute `install_script`. Benchopt
    #           will run `install_script` in a shell and provide the conda
    #           env directory as an argument. The command should then be
    #           installed in the `bin` folder of the env and can be imported
    #           with import_shell_cmd.
    install_cmd = "conda"

    _error_output = None
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
            if hasattr(cls, "_import_ctx") and cls._import_ctx.failed_import:
                exc_type, value, tb = cls._import_ctx.import_error
                if raise_on_not_installed:
                    raise exc_type(value).with_traceback(tb)
                if not cls._error_displayed and not quiet:
                    traceback.print_exception(exc_type, value, tb)
                    cls._error_displayed = True
                elif quiet:
                    cls._error_output = traceback.format_exception(
                        exc_type, value, tb
                    )
                return False

            # Import worked in the current environment, no need to check
            return True

        # Get the current benchmark directory. ``check-install`` always
        # emits a JSON dict (even for a single class) and exits non-zero
        # when at least one class is not installed.
        ref = f"{cls._module_filename}@{cls._base_class_name}"
        exit_code, output = get_backend().run_in_env(
            f"benchopt check-install {cls._benchmark_dir} {ref}",
            env_name=env_name, return_output=True,
            raise_on_error=raise_on_not_installed,
        )
        if exit_code != 0:
            if not quiet:
                print(output)
            else:
                cls._error_output = output
        return exit_code == 0

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
        # Check that install_cmd is valid and if the cls is installed.
        # When force=True targets a specific env (env_name is not None,
        # typically just-created), skip the is_installed check which
        # would spawn a per-class subprocess to confirm nothing is
        # installed yet. For env_name=None the check is in-process and
        # essentially free, so always run it.
        install_cmd_ = cls.install_cmd_
        if force and env_name is not None:
            is_installed = False
        else:
            is_installed = cls.is_installed(env_name=env_name, quiet=True)

        env_suffix = f" in '{env_name}'" if env_name else ""
        if force or not is_installed:
            print(f"- Installing '{cls.name}'{env_suffix}:...",
                  end="", flush=True)
            try:
                cls._pre_install_hook(env_name=env_name)
                if install_cmd_ == "conda":
                    if hasattr(cls, "requirements"):
                        get_backend().install_packages(
                            *cls.requirements, env_name=env_name
                        )
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
                            "   requirements = ['chan::pkg'] # package `pkg` "
                            "in conda channel `chan`\n"
                            "   requirements = ['pip::pkg'] "
                            "# pip package `pkg`"
                        ) from (
                            ImportError(cls._error_output)
                            if cls._error_output else None
                        )
                elif install_cmd_ == "shell":
                    install_file = (
                        cls._module_filename.parents[1] / "install_scripts"
                        / cls.install_script
                    )
                    get_backend().install_shell_script(
                        install_file, env_name=env_name
                    )
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
    def collect(cls, env_name=None, force=False, gpu=False,
                is_installed_cache=None):
        """Collect info for global installation of all classes in an env.

        Parameters
        ----------
        env_name: str or None
            Name of the conda env where the class should be installed. If
            None, tries to install it in the current environment.
        force : boolean (default: False)
            If set to True, forces reinstallation when using conda.
        is_installed_cache : dict or None (default: None)
            Pre-computed ``{cls: is_installed}`` map populated by
            :meth:`Benchmark.check_classes_installed`. When provided,
            avoids spawning one ``benchopt check-install`` subprocess
            per class.

        Returns
        -------
        conda_requirements: list of str
            List of all requirements for this class.
        shell_install_script: str
            Name of the install script to run.
        post_install_hooks: list of callable
            Post install hooks if one need to be run.
        """
        colored_cls_name = colorify(cls.name, BLUE)
        print(f"- {colored_cls_name}: ", end="", flush=True)

        def fail_fast(exc):
            if RAISE_INSTALL_ERROR:
                raise exc
            print(f"failed to get requirements {RED_CROSS}\n{exc}")
            return [], [], [], cls

        # Check that install_cmd is valid and if the cls is installed.
        # When force=True targets a specific env (typically just-created),
        # skip the per-class is_installed check — it would spawn a
        # subprocess to confirm nothing is installed yet. Otherwise
        # prefer the pre-computed cache (one batched subprocess) if the
        # caller provided one; fall back to a per-class check.
        try:
            install_cmd_ = cls.install_cmd_
        except Exception as exc:
            return fail_fast(exc)
        if force and env_name is not None:
            is_installed = False
        elif is_installed_cache is not None and cls in is_installed_cache:
            is_installed = is_installed_cache[cls]
        else:
            is_installed = cls.is_installed(env_name=env_name, quiet=True)

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
                try:
                    conda_reqs = getattr(cls, "requirements", [])
                except Exception as exc:
                    return fail_fast(exc)

                if isinstance(conda_reqs, dict):
                    try:
                        conda_reqs = (conda_reqs["gpu"] if gpu
                                      else conda_reqs["cpu"])
                    except KeyError:
                        raise ValueError(
                            "If `requirements` is a dict, its keys should be "
                            f"`cpu` and `gpu`, got {list(conda_reqs.keys())}"
                        )

                # Skip-with-warn: if the active backend cannot install
                # any of the requirements (e.g. `chan::pkg` under uv),
                # drop the class from this install run. The class will
                # still be reported as not-installed by the post-install
                # verification loop, surfacing the warning to the user.
                backend = get_backend()
                unsupported = [
                    r for r in conda_reqs if not backend.can_install(r)
                ]
                if unsupported:
                    print(colorify(
                        f"skipped (backend {backend.name!r} cannot install"
                        f" {unsupported})", YELLOW
                    ))
                    return [], [], [], None

                # The "no requirements declared" heuristic only fires
                # when we have a real is_installed answer. When we
                # short-circuited the check (force=True targeting a
                # specific env), defer the diagnostic to post-install
                # verification.
                if (not force and not is_installed
                        and len(conda_reqs) == 0):
                    missing_deps = cls
            post_install_hooks = [cls._post_install_hook]
            print("collected", GREEN_TICK)
        else:
            env_suffix = f" in '{env_name}'" if env_name else ""
            print(f"already available{env_suffix}", GREEN_TICK)

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
