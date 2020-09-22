using Core
using LinearAlgebra
using StatsBase # for sample function

# TODO : import shared functions from common file
# include("./benchmarks/logreg_l2/solvers/logistic.jl")

# Loss evaluation
function logistic_loss(X, y, w::Array{Float64})
    return sum( log.(1. .+  exp.(-(y .* (X*w)))) )
end

# Gradient evaluation
function sigmoid(z::Array{Float64})
    # This function computes the sigmoid function:
    # \sigma(z) = 1 / (1 + e^(-z)) .
    # Let the i-th loss be
    # \phi_i (z) = \log \left( 1 + e^{-y_i z} \right) .
    # Then its derivative is
    # \phi_i^' (z) = -y_i \sigma(-y_i z)
    idx = z .> 0
    out = zeros(size(z))
    out[idx] = (1 .+ exp.(-z[idx])).^(-1)
    exp_t = exp.(z[.~idx])
    out[.~idx] = exp_t ./ (1. .+ exp_t)
    return out
end

function logistic_grad(X, y, w::Array{Float64})
    # lot of computations hidden back here
    z = sigmoid(y .* (X*w))
    return X' * (y .* (z .- 1))
end


function solve_logreg_l2(X, y, lambda::Float64, n_iter::Int64; batch_size::Int64=1, step_size::Float64=1.)
    # Stochastic gradient solver for l2 regularized logistic regression.

    # Define function and gradient with mini-batching and l2 regularization
    # f(w) = \frac{1}{n} \sum_{i=1}^n f_i (w)
    #      = \frac{\lambda}{2} \norm{w}_2^2 + \sum_{i=1}^n \left( \phi_i (x_i^{\top} w) \right)
    # where \phi_i (z) = \log(1 + \exp(-y_i z))

    # Let B be a mini-batch of indices, then the loss of the subsampled function is
    # logreg_l2_subloss(w, B) = (n_samples / length(B)) * logistic_loss(X[B, :], y[B], w) + (0.5 * lambda * norm(w)^2);

    # TODO: choose a step size rule

    n_samples = size(X, 1)
    sgd_grad(w, B) = (n_samples / length(B)) * logistic_grad(X[B, :], y[B], w) .+ (lambda .* w);

    n_features = size(X, 2)
    w = zeros(n_features, 1)
    t_new = 1
    for i ∈ 1:n_iter
        B = sample(1:n_samples, batch_size, replace=false) # sampling a mini-batch
        w -= (step_size / sqrt(i)) .* sgd_grad(w, B)
    end
    return w
end
