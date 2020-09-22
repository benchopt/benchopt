using Core
using LinearAlgebra

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


function solve_logreg_l2(X, y, lambda, n_iter)
    L = (opnorm(X)^2 / 4) + lambda

    n_features = size(X, 2)
    w = zeros(n_features, 1)
    t_new = 1
    for i ∈ 1:n_iter
        grad = logistic_grad(X, y, w) .+ (lambda .* w); # correct
        w -= grad ./ L
    end

    return w
end
