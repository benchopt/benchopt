# BenchOpt

* API
   - Easy to adapt new algorithms
   - Think about f/f_prime API?
   - Independent of python implementation?
   - Multiple datasets
   - Easy install
   - Easy command line interface/venv

* Support
   - TPU/GPU/parallelism
   - PR + unit test
   - Can run in local
   - Local run with a callback API?

* complicated part:
   - Same definition of the loss (mean vs sum)


## Current TODO:

- [ ] Adapt n_iter spacing to time (while loop)
- [ ] Compute optimal solution
- [ ] Argument in client to pass solvers to run in benchmark
- [ ] Make CI run the benchmark and check install

