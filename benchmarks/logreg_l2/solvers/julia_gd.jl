using Core
using LinearAlgebra

# TODO : import shared functions from file
# include("./benchmarks/logreg_l2/solvers/logistic.jl")

##########################################################""

# Loss evaluation
function logistic_loss(X, y, w::Array{Float64}) # correct
    # return sum( log.(1. .+  exp.(-(y .* (X*w)))) ) # other implementation
    return -sum( log.(logistic_diff_phi(y .* (X*w))) )
end

# Gradient evaluation
function logistic_diff_phi(z::Array{Float64}) # correct
    # Derivative of phi_i is ``more or less" the sigmoid
    # phi'(z) = 1 / (1 + e^(-z))
    idx = z .> 0
    out = zeros(size(z))
    out[idx] = (1 .+ exp.(-z[idx])).^(-1)
    exp_t = exp.(z[.~idx])
    out[.~idx] = exp_t ./ (1. .+ exp_t)
    return out
end

function logistic_grad(X, y, w::Array{Float64}) # correct
    # lot of computations hidden back here
    z = logistic_diff_phi(y .* (X*w))
    return X' * (y .* (z .- 1))
end

##########################################################""



function logistic_eval(X, y, w::Array{Float64})
    return -sum( log.( logistic_phi(y .* (X*w)) ) )
end

function logistic_phi(t::Array{Float64})
    idx = t .> 0
    out = zeros(size(t))
    out[idx] = (1 .+ exp.(-t[idx])).^(-1)
    exp_t = exp.(t[.~idx])
    out[.~idx] = exp_t ./ (1. .+ exp_t)
    return out
end

function logistic_grad(X, y, w::Array{Float64})
    t = logistic_phi(y .* (X*w))
    return X' * (y .* (t .- 1))
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
