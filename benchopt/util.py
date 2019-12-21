import os
import yaml
import venv


VENV_DIR = './.venv/'


if not os.path.exists(VENV_DIR):
    os.mkdir(VENV_DIR)


CHECK_PIP_INSTALL_CMD = "python -c 'import {package_name}' 1>/dev/null 2>&1"
CHECK_SOLVER_INSTALL_CMD = "type $'{solver_cmd}' 1>/dev/null 2>&1"


def _run_in_bash(script):
    with open("/tmp/script_bash_benchopt.sh", 'w') as f:
        f.write(script)

    return os.system("bash /tmp/script_bash_benchopt.sh")


def _run_in_bench_env(bench, script):
    env_name = f"{VENV_DIR}/{bench}"

    bench_env_script = f"""
    source {env_name}/bin/activate
    {script}
    """

    return _run_in_bash(bench_env_script)


def check_package_in_env(bench, package_name):
    check_pip_install_cmd = CHECK_PIP_INSTALL_CMD.format(
        package_name=package_name)
    return _run_in_bench_env(bench, check_pip_install_cmd) == 0


def check_solver_in_env(bench, solver_cmd):
    check_solver_install_cmd = CHECK_SOLVER_INSTALL_CMD.format(
        solver_cmd=solver_cmd)
    return _run_in_bench_env(bench, check_solver_install_cmd) == 0


def get_solvers(benchmark):

    # Load the name of the available solvers
    with open('solvers.yml') as f:
        all_solvers = yaml.safe_load(f)

    # Get the solvers to run for benchmark and the install procedure
    benchmark_solvers = []
    pip_install = []
    sh_install = []
    for solver, infos in all_solvers.items():
        if benchmark in infos['bench']:
            benchmark_solvers.append(solver)
            if 'pip_install' in infos:
                if not check_package_in_env(benchmark, infos['package_name']):
                    pip_install.append(infos['pip_install'])
            elif 'sh_install' in infos:
                if not check_solver_in_env(benchmark, infos['solver_cmd']):
                    sh_install.append(infos['sh_install'])

    return benchmark_solvers, pip_install, sh_install


def create_bench_env(bench):
    solvers, pip, sh = get_solvers(bench)

    # Create a virtual env for the benchmark
    env_name = f"{VENV_DIR}/{bench}"
    if not os.path.exists(env_name):
        venv.create(env_name, with_pip=True)

    # Install the packages necessary for the benchmark's solvers with pip
    script = f"""
        pip install numpy cython  # Utilities to compile some python packages
        pip install . {" ".join(pip)}
    """
    print(f"Installing venv for {bench}:....", end='', flush=True)
    exit_code = _run_in_bench_env(bench, script)
    if exit_code != 0:
        raise RuntimeError("The installation failed in the venv")
    print("done")

    # Install the packages necessary for the benchmark's solvers with pip
    # if len(sh) > 0:
    #     raise NotImplementedError("Cannot install packages with bash yet.")
    for install_script in sh:
        script = f"bash install_scripts/{install_script} {env_name}"
        _run_in_bench_env(script)
