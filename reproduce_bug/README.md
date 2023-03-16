# Optimization algorithm

$$\min_{x \in \mathbb{R}} (ax + b)^2, \quad \mathrm{ with } \ a, b \in \mathbb{R}$$


# Solver

Use a solver that performs ``n-epochs`` gradient descent step to solve problem

```python
x = 0.
for _ in range(n_iter):

    # gradient steps
    for _ in range(n_epochs):
        grad = a * (a * x + b)
        x -= step * grad
```

# Reproduce benchmark

Run the followings

```bash
cd reproduce_bug
benchopt run . --config run_config.yml
```


# Benchmark results

In the benchmark, three solvers that uses resp. ``[1, 10, 100]`` epochs are run. 

The benchmark figure shows a awkward zig-zag pattern namely when ``n-epochs `` is small.

<img width="800px" height="400px" src="../reproduce_bug/screenshots/bench_result.png"/>

