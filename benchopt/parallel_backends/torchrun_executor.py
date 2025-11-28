import os
import subprocess
import tempfile
import pickle
import hashlib
from pathlib import Path
from contextlib import ExitStack


def get_torchrun_folder(benchmark):
    """Get the folder to store the output of torchrun jobs."""
    torchrun_dir = benchmark.benchmark_dir / "benchopt_run"
    torchrun_dir.mkdir(exist_ok=True)
    return torchrun_dir


def harmonize_torchrun_config(torchrun_cfg):
    """Harmonize torchrun config for handling equivalent key names."""
    torchrun_cfg = {k.removeprefix("torchrun_"): v for k, v in torchrun_cfg.items()}
    return {"torchrun_" + k: v for k, v in torchrun_cfg.items()}


def merge_torchrun_configs(*torchrun_cfgs):
    """Merge multiple torchrun config dicts in order, with later dicts overriding
    earlier ones.
    
    The keys are harmonized before merging.
    """
    torchrun_cfg = {}
    for cfg in torchrun_cfgs:
        cfg = harmonize_torchrun_config(cfg)
        torchrun_cfg.update(cfg)
    return torchrun_cfg


def get_solver_torchrun_config(solver, torchrun_bench_cfg):
    """Generate and merge torchrun configuration for a solver from static,
    dynamic, and benchmark configs.
    """
    static_solver_cfg = getattr(solver, "torchrun_params", {})
    dyn_solver_cfg = {
        k: v for k, v in solver._parameters.items() if k.startswith("torchrun_")
    }
    solver_cfg = merge_torchrun_configs(
        torchrun_bench_cfg,
        static_solver_cfg,
        dyn_solver_cfg,
    )

    return solver_cfg


def hashable_pytree(pytree):
    """Flatten a pytree into a list."""
    if isinstance(pytree, (list, tuple)):
        return tuple(hashable_pytree(item) for item in sorted(pytree))
    elif isinstance(pytree, dict):
        return tuple(
            (k, hashable_pytree(v)) for k, v in sorted(pytree.items())
        )
    else:
        return pytree


def run_on_torchrun(
    benchmark, torchrun_config, run_one_solver, common_kwargs, all_runs
):
    """Run solvers using torchrun for local distributed testing.
    
    This function groups solvers by their torchrun configuration and runs
    each group with the appropriate number of processes.
    """
    import sys
    
    print("[TORCHRUN] Starting run_on_torchrun")
    print(f"[TORCHRUN] torchrun_config: {torchrun_config}")
    
    # Convert generator to list
    all_runs = list(all_runs)
    print(f"[TORCHRUN] Number of runs: {len(all_runs)}")
    
    # Get the torchrun output folder
    torchrun_folder = get_torchrun_folder(benchmark)
    print(f"[TORCHRUN] Output folder: {torchrun_folder}")
    
    # Group runs by torchrun configuration
    executors = {}
    tasks = []
    
    for i, kwargs in enumerate(all_runs):
        print(f"[TORCHRUN] Processing run {i+1}/{len(all_runs)}")
        solver = kwargs.get("solver")
        print(f"[TORCHRUN] Solver: {solver}")
        solver_torchrun_config = get_solver_torchrun_config(solver, torchrun_config)
        print(f"[TORCHRUN] Solver config: {solver_torchrun_config}")
        executor_config = hashable_pytree(solver_torchrun_config)
        
        if executor_config not in executors:
            executors[executor_config] = {
                'config': solver_torchrun_config,
                'runs': []
            }
        
        executors[executor_config]['runs'].append(kwargs)
    
    print(f"[TORCHRUN] Grouped into {len(executors)} executor configs")
    
    results = []
    
    # Execute each group of runs
    for exec_idx, (executor_config, executor_data) in enumerate(executors.items()):
        print(f"\n[TORCHRUN] ===== Executor config {exec_idx+1}/{len(executors)} =====")
        config = executor_data['config']
        runs = executor_data['runs']
        
        # Get number of processes (nproc_per_node)
        nproc = config.get('torchrun_nproc_per_node', 1)
        
        print(f"[TORCHRUN] Running {len(runs)} solver(s) with {nproc} processes")
        print(f"[TORCHRUN] Config: {config}")
        
        for run_idx, run_kwargs in enumerate(runs):
            print(f"\n[TORCHRUN] ----- Run {run_idx+1}/{len(runs)} -----")
            # Create temporary files for arguments and results
            print("[TORCHRUN] Creating temporary files for arguments")
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as args_file:
                args_path = args_file.name
                pickle.dump({
                    'run_one_solver': run_one_solver,
                    'common_kwargs': common_kwargs,
                    'solver_kwargs': run_kwargs,
                }, args_file)
            print(f"[TORCHRUN] Args file: {args_path}")
            
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as result_file:
                result_path = result_file.name
            print(f"[TORCHRUN] Result file: {result_path}")
            
            # Create log file path
            solver_name = run_kwargs.get('solver').name
            
            # Use a hash of the parameters to avoid "File name too long" errors
            params_str = str(sorted(
                (k, str(v)) for k, v in run_kwargs.items() if k != 'solver'
            ))
            params_hash = hashlib.md5(params_str.encode('utf-8')).hexdigest()
            
            log_file = torchrun_folder / f"{solver_name}_{params_hash}.log"
            print(f"[TORCHRUN] Log file: {log_file}")
            
            # Build torchrun command
            print("[TORCHRUN] Building torchrun command")
            cmd = [
                sys.executable, '-m', 'torch.distributed.run',
                '--nnodes=1',
                f'--nproc_per_node={nproc}',
            ]
            
            # Add additional torchrun parameters
            for key, value in config.items():
                if key.startswith('torchrun_') and key != 'torchrun_nproc_per_node':
                    param_name = key.replace('torchrun_', '').replace('_', '-')
                    if isinstance(value, bool):
                        if value:
                            cmd.append(f'--{param_name}')
                    else:
                        cmd.extend([f'--{param_name}', str(value)])
            
            # Add the script to run
            cmd.extend([
                '-m', 'benchopt.parallel_backends.torchrun_executor',
                args_path,
                result_path,
            ])
            
            print(f"\nRunning: {' '.join(cmd)}")
            print(f"Log file: {log_file}")
            
            # Set environment variable for log file
            env = os.environ.copy()
            env['TORCHRUN_LOG_FILE'] = str(log_file)
            
            try:
                # Run torchrun
                print("[TORCHRUN] Executing torchrun command...")
                print(f"[TORCHRUN] Command: {' '.join(cmd)}")
                subprocess.run(cmd, check=True, env=env)
                print("[TORCHRUN] Torchrun completed successfully")
                
                # Load result
                print(f"[TORCHRUN] Loading result from {result_path}")
                with open(result_path, 'rb') as f:
                    result = pickle.load(f)
                
                results.append(result)
                print(f"[TORCHRUN] Result loaded and appended")
                
            except subprocess.CalledProcessError as e:
                print(f"[TORCHRUN] ERROR running torchrun: {e}")
                raise
            except Exception as e:
                print(f"[TORCHRUN] ERROR: {e}")
                import traceback
                traceback.print_exc()
                raise
            finally:
                # Clean up temporary files
                print("[TORCHRUN] Cleaning up temporary files")
                try:
                    os.unlink(args_path)
                    os.unlink(result_path)
                except Exception as e:
                    print(f"[TORCHRUN] Warning: couldn't clean up temp files: {e}")
    
    print(f"\n[TORCHRUN] All runs complete. Returning {len(results)} results")
    return results


if __name__ == '__main__':
    # This is the entry point when running as a module with torchrun
    import sys
    
    print("[TORCHRUN WORKER] Starting worker process")
    print(f"[TORCHRUN WORKER] Args: {sys.argv}")
    
    if len(sys.argv) < 3:
        print("[TORCHRUN WORKER] ERROR: Not enough arguments")
        print("Usage: python -m benchopt.parallel_backends.torchrun_executor <args_file> <result_file>")
        sys.exit(1)
    
    args_file = sys.argv[1]
    result_file = sys.argv[2]
    log_file = os.environ.get('TORCHRUN_LOG_FILE')
    
    print(f"[TORCHRUN WORKER] Args file: {args_file}")
    print(f"[TORCHRUN WORKER] Result file: {result_file}")
    print(f"[TORCHRUN WORKER] Log file env: {log_file}")
    
    # Get rank info from environment
    rank = int(os.environ.get("RANK", 0))
    world_size = int(os.environ.get("WORLD_SIZE", 1))
    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    
    print(f"[TORCHRUN WORKER] Rank: {rank}/{world_size}, Local rank: {local_rank}")
    
    # Redirect output to log file
    if log_file:
        print(f"[TORCHRUN WORKER] Redirecting output to log file")
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Append rank to log file name
        log_file_rank = log_path.parent / f"{log_path.stem}_rank{rank}{log_path.suffix}"
        
        sys.stdout = open(log_file_rank, 'w', buffering=1)
        sys.stderr = sys.stdout
    
    print(f"[Rank {rank}/{world_size}] Starting torchrun process")
    print(f"[Rank {rank}/{world_size}] Local rank: {local_rank}")
    
    # Load pickled arguments
    print(f"[Rank {rank}/{world_size}] Loading arguments from {args_file}")
    try:
        with open(args_file, 'rb') as f:
            args = pickle.load(f)
        print(f"[Rank {rank}/{world_size}] Arguments loaded successfully")
    except Exception as e:
        print(f"[Rank {rank}/{world_size}] ERROR loading arguments: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    run_one_solver = args['run_one_solver']
    common_kwargs = args['common_kwargs']
    solver_kwargs = args['solver_kwargs']
    
    print(f"[Rank {rank}/{world_size}] Running solver...")
    # Run the solver
    try:
        result = run_one_solver(**common_kwargs, **solver_kwargs)
        print(f"[Rank {rank}/{world_size}] Solver completed successfully")
    except Exception as e:
        print(f"[Rank {rank}/{world_size}] ERROR running solver: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Only rank 0 saves the result
    if rank == 0:
        print(f"[Rank {rank}/{world_size}] Saving result to {result_file}")
        try:
            with open(result_file, 'wb') as f:
                pickle.dump(result, f)
            print(f"[Rank {rank}/{world_size}] Result saved successfully")
        except Exception as e:
            print(f"[Rank {rank}/{world_size}] ERROR saving result: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    print(f"[Rank {rank}/{world_size}] Completed")
    
    # Cleanup
    if log_file:
        sys.stdout.close()
        sys.stderr = sys.__stderr__
        sys.stdout = sys.__stdout__
