using Core
using LinearAlgebra


function st(w, t)
    w = map(sign, w) .* map(x -> max(abs(x) - t, 0), w)
end


function solve_lasso(X, y, lambda, n_iter)
    L = opnorm(X)^2

    n_features = size(X, 2)
    w = zeros(n_features, 1)
    t_new = 1
    for i ∈ 1:n_iter
        grad = X' * (X * w - y)
        w -= grad / L
        w = st(w, lambda / L)
    end

    return w
end
