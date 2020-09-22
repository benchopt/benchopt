## From benchOpt directory, run
# $ julia test_julia/test_logreg_l2_grad.jl

using StatsBase
using LinearAlgebra
include("../benchmarks/logreg_l2/solvers/logistic.jl")


# Testing the logistic loss and its derivative
# logistic_phi
# logistic_grad


## Basic parameters
n_samples = 200;
n_features = 10;
X = rand(n_samples, n_features);
y = rand(n_samples);
y = convert.(Float64, rand(Bool, n_samples));
min_y = minimum(y); # Way faster implementation
max_y = maximum(y);
y[findall(x->x==min_y, y)] .= -1;
y[findall(x->x==max_y, y)] .= 1;

lambda = 0.001;
# lambda = 1.;


# Mini-batch L2 regularized logistic loss and SGD estimate
logreg_l2_loss(w, B) = (n_samples / length(B)) * logistic_loss(X[B, :], y[B], w) + (0.5 * lambda * norm(w)^2); # correct
logreg_l2_grad(w, B) = (n_samples / length(B)) * logistic_grad(X[B, :], y[B], w) .+ (lambda .* w); # correct


## Testing loss code
w = zeros(n_features);
B_full = collect(1:n_samples)
@assert logreg_l2_loss(w, B_full) ≈ n_samples * log(2)


## Testing gradient code
error = 0;
n_trials = 1000;
eps = 10.0^(-7);
grad = zeros(n_features);
batch_size = n_samples
for i = 1:n_trials
    B = sample(1:n_samples, batch_size, replace=false);
    w = rand(n_features);
    d = rand(n_features);

    grad_estim_scalar_d = (logreg_l2_loss(w + eps.*d, B) - logreg_l2_loss(w, B)) / eps;

    grad_scalar_d = logreg_l2_grad(w, B)' * d;

    global error = error + norm(grad_estim_scalar_d - grad_scalar_d);
end
error = error / n_trials;
println("average grad error: ", error)