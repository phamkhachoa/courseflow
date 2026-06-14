package edu.courseflow.commonlibrary.exception;

/**
 * Raised when the caller is authenticated but not allowed to perform the operation.
 * Services should prefer this shared type over local copy-paste 403 exceptions.
 */
public class ForbiddenException extends RuntimeException implements ErrorCodeCarrier {

    private final String errorCode;

    public ForbiddenException(String message) {
        super(message);
        this.errorCode = null;
    }

    private ForbiddenException(String message, String errorCode) {
        super(message);
        this.errorCode = errorCode;
    }

    public static ForbiddenException coded(String errorCode, String message) {
        return new ForbiddenException(message, errorCode);
    }

    @Override
    public String errorCode() {
        return errorCode;
    }
}
