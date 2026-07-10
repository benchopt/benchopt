##' Functions used in GD algorithm
##'
##' @title Functions used in GD algorithm
##' @author Thomas Moreau
##' @export


# Main algorithm
gradient_descent <- function(X, lr, n_iter) {
    # --------- Initialize parameter ---------
    p <- ncol(X)
    parameters <- X * 0

    # --------- Run GD for n_iter iterations ---------
    for (i in 1:n_iter) {
        # Compute the gradient
        grad <- (parameters - X)
        # # Update the parameters
        parameters <- parameters - lr * grad
    }
    return(parameters)
}
