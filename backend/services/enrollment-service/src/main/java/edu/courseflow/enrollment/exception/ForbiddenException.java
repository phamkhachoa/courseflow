package edu.courseflow.enrollment.exception;

/**
 * Raised when an authenticated caller lacks the role or ownership required for an action.
 * Mapped to HTTP 403 by {@link LocalExceptionHandler}. Kept local to the service because
 * common-library does not (yet) ship a Forbidden type and must not be modified here.
 */
public class ForbiddenException extends RuntimeException {

    public ForbiddenException(String message) {
        super(message);
    }
}
