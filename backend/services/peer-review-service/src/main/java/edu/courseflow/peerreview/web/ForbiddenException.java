package edu.courseflow.peerreview.web;

/**
 * Thrown when an authenticated caller is not permitted to perform the requested action
 * (wrong role, or attempting to act on another user's data). Mapped to HTTP 403 by
 * {@link ForbiddenExceptionHandler}.
 *
 * <p>Lives in this service because common-library does not ship a 403 mapping; we must not
 * modify common-library.
 */
public class ForbiddenException extends RuntimeException {

    public ForbiddenException(String message) {
        super(message);
    }
}
