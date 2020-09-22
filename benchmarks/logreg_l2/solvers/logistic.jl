
# Loss evaluation
function logistic_loss(X, y, w::Array{Float64})
    # return sum( log.(1. .+  exp.(-(y .* (X*w)))) ) # other implementation
    return -sum( log.(logistic_diff_phi(y .* (X*w))) )
end

# Gradient evaluation
function logistic_diff_phi(z::Array{Float64})
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

# Define function and gradient with mini-batching and l2 regularization
# f(w) = \frac{1}{n} \sum_{i=1}^n f_i (w)
#      = \frac{\lambda}{2} \norm{w}_2^2 + \sum_{i=1}^n \left( \phi_i (x_i^{\top} w) \right)
# where \phi_i (z) = \log(1+\exp(-y_i z))

# B stands for a mini-batch of indices
# logreg_l2_loss(w, B) = (n_samples / length(B)) * logistic_loss(X[B, :], y[B], w) + (0.5 * lambda * norm(w)^2);
# logreg_l2_grad(w, B) = (n_samples / length(B)) * logistic_grad(X[B, :], y[B], w) .+ (lambda .* w);