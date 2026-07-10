using Core


function gradient_descent(X, lr, n_iter)
    X_hat = zeros(size(X))
    for i ∈ 1:n_iter
        grad = X_hat - X
        X_hat -= lr * grad
    end

    return X_hat
end
