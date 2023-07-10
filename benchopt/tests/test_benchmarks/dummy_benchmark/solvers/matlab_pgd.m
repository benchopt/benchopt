function w = matlab_pgd(X, y, lambda, n_iter)
    L = norm(X, 'fro')^2;
    n_features = size(X, 2);
    w = zeros(n_features, 1);
    t_new = 1;
    for i = 1:n_iter
        grad = X' * (X * w - y');
        w = w - grad / L;
        w = st(w, lambda / L);
    end
end

function w = st(w, t)
    w = sign(w) .* max(abs(w) - t, 0);
end
