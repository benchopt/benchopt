

def loss_function(X, y, lmbd, beta):
    diff = y - X.dot(beta)
    return .5 * diff.dot(diff) + lmbd * abs(beta).sum()
