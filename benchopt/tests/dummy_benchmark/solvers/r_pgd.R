##' Functions used in ISTA algorithm
##'
##' @title Functions used in ISTA algorithm
##' @author Thomas Moreau
##' @export


# Soft-thresholding operator
St <- function(lambda, X) {
    st <- function(lambda0, x) {
        if (x > lambda0) {
            result0 <- x - lambda0
        } else if (x < (-1) * lambda0) {
            result0 <- x + lambda0
        } else result0 <- 0

        return(result0)
    }
    result <- apply(X, 1, st, lambda0 = lambda)
    return(result)
}


# Main algorithm
proximal_gradient_descent <- function(X, Y, lambda, n_iter) {
    # --------- Initialize parameter ---------
    p <- ncol(X)
    parameters <- numeric(p)

    # --------- Run ISTA for n_iter iterations ---------
    step_size <- 1 / norm(X, "2") ** 2
    for (i in 1:n_iter) {
        # Compute the gradient
        grad <- t(-X) %*% (Y - X %*% parameters)
        # # Update the parameters
        parameters <- St(step_size * lambda, parameters - step_size * grad)
    }
    return(parameters)
}
