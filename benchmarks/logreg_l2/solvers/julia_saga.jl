using Core
using LinearAlgebra
using StatsBase # sample function

# TODO : import shared functions from file
# include("./benchmarks/logreg_l2/solvers/logistic.jl")

# Loss evaluation
function logistic_loss(X, y, w::Array{Float64})
    return sum( log.(1. .+  exp.(-(y .* (X*w)))) )
end

function logreg_l2_loss(X, y, w::Array{Float64}, lambda)
    return logistic_loss(X, y, w) + (.5 * lambda * norm(w));
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

function logreg_l2_grad(X, y, w::Array{Float64}, lambda)
    return logistic_grad(X, y, w) .+ (lambda .* w);
end

function logreg_l2_Jac!(X, y, w::Array{Float64}, lambda::Float64, B::Array{Int64}, Jac::Array{Float64})
    n_samples = size(X, 1)
    z = sigmoid(y[B] .* (X[B, :]*w));
    Jac[:, B] = n_samples .* X[B, :]' .* (y[B] .* (z .- 1))' .+ (lambda .* w); # J_{:i}^{t+1} <- \nabla f_i (w^t)
end

function logreg_l2_Jac(X, y, w::Array{Float64}, lambda::Float64, B::Array{Int64})
    n_samples = size(X, 1)
    z = sigmoid(y[B] .* (X[B, :]*w));
    return n_samples .* X[B, :]' .* (y[B] .* (z .- 1))' .+ (lambda .* w); # J_{:i}^{t+1} <- \nabla f_i (w^t)
end

function solve_logreg_l2(X, y, lambda::Float64, n_iter::Int64; batch_size::Int64=1, unbiased::Bool=false)
    """
    Implementation based on Algorithm 2 of
    N. Gazagnadou, R. Gower, J. Salmon, `Optimal Mini-Batch and Step Sizes for SAGA`, ICML 2019.
    """
    # TODO : use expected smoothness instead -> larger step size with minibatching

    n_samples = size(X, 1)
    Lmax = (n_samples/4) * maximum(sum(X .^ 2, dims=2)) + lambda
    step_size = 1. / Lmax
    println("Step size SAGA = ", step_size, "\n")

    n_features = size(X, 2)
    w = zeros(n_features, 1)

    Jac = zeros(n_features, n_samples) # Jacobian estimate
    # Jac = logreg_l2_Jac(X, y, w, lambda, collect(1:n_samples)); # full gradient Jacobian init
    aux = zeros(n_features, 1) # auxiliary vector
    grad_estim = zeros(n_features, 1) # stochastic gradient estimate, SAGA if unbiased = true, SAG else
    u = sum(Jac, dims=2) # SAG (biased) estimate
    for i ∈ 1:n_iter
        B = sample(1:n_samples, batch_size, replace=false) # sampling a mini-batch

        # Assign each gradient to a different column of Jac
        aux[:] = -sum(Jac[:, B], dims=2); # Calculating the auxiliary vector
        logreg_l2_Jac!(X, y, w, lambda, B, Jac); # Update of the Jacobian estimate
        # Jac[:, B] = logreg_l2_Jac(X, y, w, lambda, B); # Update of the Jacobian estimate
        aux[:] += sum(Jac[:, B], dims=2); # aux = \sum_{i \in B} (\nabla f_i (w^t) - J_{:i}^t)

        # Update of the unbiased gradient estimate: g^k
        if unbiased
            grad_estim[:] = u .+ ((1. / length(B)) .* aux); # SAGA unbiased descent direction
        else
            grad_estim[:] = u; # SAG biased descent direction
        end

        # if i % 500 == 1
        #     full_grad = logreg_l2_grad(X, y, w, lambda)
        #     println("Iter: ", i, " | logreg_l2_loss = ", logreg_l2_loss(X, y, w, lambda), " | norm(full_grad) = ", norm(full_grad))
        # end

        # Update SAG biased estimate: 1/n J^{k+1}1 = 1/n J^k 1 + 1/n (DF^k-J^k) Proj 1
        u[:] = u .+ ((1. / n_samples) .* aux);

        # Update the vector of weights through a stochastic step
        w -= step_size .* grad_estim;
    end
    return w
end


#########################################################################################

# using Core
# using LinearAlgebra
# using StatsBase # for sample function

# # TODO : import shared functions from common file
# # include("./benchmarks/logreg_l2/solvers/logistic.jl")

# # Loss evaluation
# function logistic_loss(X, y, w::Array{Float64})
#     return sum( log.(1. .+  exp.(-(y .* (X*w)))) )
# end

# # Gradient evaluation
# function sigmoid(z::Array{Float64})
#     # This function computes the sigmoid function:
#     # \sigma(z) = 1 / (1 + e^(-z)) .
#     # Let the i-th loss be
#     # \phi_i (z) = \log \left( 1 + e^{-y_i z} \right) .
#     # Then its derivative is
#     # \phi_i^' (z) = -y_i \sigma(-y_i z)
#     idx = z .> 0
#     out = zeros(size(z))
#     out[idx] = (1 .+ exp.(-z[idx])).^(-1)
#     exp_t = exp.(z[.~idx])
#     out[.~idx] = exp_t ./ (1. .+ exp_t)
#     return out
# end

# function logistic_grad(X, y, w::Array{Float64})
#     # lot of computations hidden back here
#     z = sigmoid(y .* (X*w))
#     return X' * (y .* (z .- 1))
# end


# function solve_logreg_l2(X, y, lambda::Float64, n_iter::Int64; batch_size::Int64=1, step_size::Float64=1.)
#     # Stochastic gradient solver for l2 regularized logistic regression.

#     # Define function and gradient with mini-batching and l2 regularization
#     # f(w) = \frac{1}{n} \sum_{i=1}^n f_i (w)
#     #      = \frac{\lambda}{2} \norm{w}_2^2 + \sum_{i=1}^n \left( \phi_i (x_i^{\top} w) \right)
#     # where \phi_i (z) = \log(1 + \exp(-y_i z))

#     # Let B be a mini-batch of indices, then the loss of the subsampled function is
#     # logreg_l2_subloss(w, B) = (n_samples / length(B)) * logistic_loss(X[B, :], y[B], w) + (0.5 * lambda * norm(w)^2);

#     # TODO: choose a step size rule

#     n_samples = size(X, 1)
#     sgd_grad(w, B) = (n_samples / length(B)) * logistic_grad(X[B, :], y[B], w) .+ (lambda .* w);

#     n_features = size(X, 2)
#     w = zeros(n_features, 1)
#     t_new = 1
#     for i ∈ 1:n_iter
#         B = sample(1:n_samples, batch_size, replace=false) # sampling a mini-batch
#         w -= (step_size / sqrt(i)) .* sgd_grad(w, B)
#     end
#     return w
# end