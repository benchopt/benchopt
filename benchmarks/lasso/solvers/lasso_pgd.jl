using MAT
using Core
using LinearAlgebra


function st(w, t)
    w = map(sign, w) .* map(x -> max(x, 0), w)
end


function lasso(data_fname, model_fname, lambda, n_iter)
    data = MAT.matread(data_fname)
    X, y = data["X"], data["y"]'
    L = norm(X)^2

    n_features = size(X, 2)
    w = zeros(n_features, 1)
    t_new = 1
    for i ∈ 1:n_iter
        grad = X' * (X * w - y)
        w -= grad / L
        w = st(w, lambda / L)
    end

    out = Dict()
    out["w"] = w
    MAT.matwrite(model_fname, out)
end

args = Core.ARGS

lambda = parse(Float64, args[2])
n_iter = parse(Int64, args[3])
data_fname = args[4]
model_fname = args[5]

lasso(data_fname, model_fname, lambda, n_iter)
