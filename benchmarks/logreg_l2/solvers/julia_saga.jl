# using Core
using LinearAlgebra
using StatsBase # sample function

# TODO : import shared functions from file
# include("./benchmarks/logreg_l2/solvers/logistic.jl")

##########################################################

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

##########################################################

function logreg_l2_Jac!(X, y, w::Array{Float64}, lambda::Float64, B::Array{Int64}, Jac::Array{Float64})
    n_samples = size(X, 1)
    z = logistic_diff_phi(y[B] .* (X[B, :]*w));
    Jac[:, B] = n_samples .* X[B, :]' .* (y[B] .* (z .- 1))' .+ (lambda .* w); # J_{:i}^{t+1} <- \nabla f_i (w^t)
end


function solve_logreg_l2(X, y, lambda::Float64, n_iter::Int64; batch_size::Int64=1, unbiased::Bool=false)
    """
    Implementation based on Algorithm 2 of
    N. Gazagnadou, R. Gower, J. Salmon, `Optimal Mini-Batch and Step Sizes for SAGA`, ICML 2019.
    """
    # TODO : use expected smoothness instead -> larger step size
    Lmax = (maximum(sum(X .^ 2, dims=2)) / 4) + lambda
    step_size = 1. / Lmax

    n_samples = size(X, 1)
    n_features = size(X, 2)
    w = zeros(n_features, 1)
    grad_estimator = zeros(n_features, 1) # stochastic gradient estimate, SAGA if unbiased = true, SAG else
    sag_grad = zeros(n_features, 1) # SAG (biased) estimate
    aux = zeros(n_features, 1) # auxiliary vector
    Jac = zeros(n_features, n_samples) # Jacobian estimate
    # logreg_l2_Jac!(X, y, w, lambda, collect(1:n_samples), Jac); # full grad init
    t_new = 1
    for i ∈ 1:n_iter
        B = sample(1:n_samples, batch_size, replace=false) # sampling a mini-batch

        # Assign each gradient to a different column of Jac
        aux[:] = -sum(Jac[:, B], dims=2); # Calculating the auxiliary vector
        # aux = sum_{i \in B} (\nabla f_i (w^t) - J_{:i}^t)
        logreg_l2_Jac!(X, y, w, lambda, B, Jac); # Update of the Jacobian estimate
        aux[:] += sum(Jac[:, B], dims=2);

        # Update of the unbiased gradient estimate: g^k
        if unbiased
            grad_estimator[:] = sag_grad .+ ((1 / length(B)) .* aux);
        else
            grad_estimator[:] = sag_grad;
        end

        # Update SAG estimate: 1/n J^{k+1}1 = 1/n J^k 1 + 1/n (DF^k-J^k) Proj 1
        # Update of the biased gradient estimate v^k
        sag_grad[:] = sag_grad .+ ((1. / n_samples) .* aux);

        w -= step_size .* grad_estimator;
    end
    return w
end