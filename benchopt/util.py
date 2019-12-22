import os
import yaml
import venv
from glob import glob


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
    bench_env_dir = f"{VENV_DIR}/{bench}"

    bench_env_script = f"""
        source {bench_env_dir}/bin/activate
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


def get_all_benchmarks():
    benchmark_files = glob("benchmarks/*/bench*.py")
    benchmarks = []
    for benchmark_file in benchmark_files:
        benchmark_name = benchmark_file.split(os.path.sep)[1]
        benchmarks.append(benchmark_name)
    return benchmarks


def check_benchmarks(benchmarks, all_benchmarks):
    unknown_benchmarks = set(benchmarks) - set(all_benchmarks)
    assert len(unknown_benchmarks) == 0, (
        "{} is not a valid benchmark. Should be one of: {}"
        .format(unknown_benchmarks, all_benchmarks)
    )


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
    solvers, pip_to_install, sh_to_install = get_solvers(bench)

    # Create a virtual env for the benchmark
    bench_env_dir = f"{VENV_DIR}/{bench}"
    if not os.path.exists(bench_env_dir):
        print(f"Creating venv for {bench}:...", end='', flush=True)
        venv.create(bench_env_dir, with_pip=True)
        print(" done")

    # Install the packages necessary for the benchmark's solvers with pip
    script = f"""
        pip install -qq numpy cython  # Utilities to compile python packages
        pip install -qq . {" ".join(pip_to_install)}
    """
    print(f"Installing python packages for {bench}:...", end='', flush=True)
    exit_code = _run_in_bench_env(bench, script)
    if exit_code != 0:
        raise RuntimeError("The installation failed in the venv")
    print(" done")

    # Run install script for necessary for the benchmark's solvers that cannot
    # be installed via pip
    print(f"Running bash install script for {bench}:...", end='', flush=True)
    for install_script in sh_to_install:
        script = f"bash install_scripts/{install_script} {bench_env_dir}"
        _run_in_bench_env(script)
    print(" done")
