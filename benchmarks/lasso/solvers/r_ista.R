##' Functions used in ISTA algrithm
##'
##' @title Functions used in ISTA algrithm
##' @author Yuan Zhou, Lingsong Meng
##' @export


# Soft-thresholding operator
St <- function(lambda, X) {
    s <- function(lambda0, x) {
        if (x > lambda0) {
            result0 <- x - lambda0
        } else if (x < (-1) * lambda0) {
            result0 <- x + lambda0
        } else result0 <- 0

        return(result0)
    }
    result <- apply(X, 1, s, lambda0 = lambda)
    return(result)
}


# Main algorithm
ISTA <- function(X, Y, lambda, n_iter = 10000) {
    # --------- Initialize parameter ---------
    p <- ncol(X)
    parameters <- numeric(p)
    step_size <- norm(X, type="2")
    # step_size <- 0.0005

    for (i in 1:n_iter) {
        # Compute the gradient
        # grad <- (-1) * t(X) %*% (Y - X %*% parameters)
        grad <- t(-X) %*% (Y - X %*% parameters)
        # # Update the parameters
        parameters <- St(step_size * lambda, parameters - step_size * grad)
    }
    return(parameters)
}
