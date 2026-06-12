package edu.courseflow.commonlibrary.exception;

/**
 * Raised when the caller is authenticated but not allowed to perform the operation.
 * Services should prefer this shared type over local copy-paste 403 exceptions.
 */
public class ForbiddenException extends RuntimeException {

    public ForbiddenException(String message) {
        super(message);
    }
}
