package edu.courseflow.commonlibrary.exception;

import edu.courseflow.commonlibrary.utils.MessagesUtils;

/** Domain rule violation that maps to HTTP 409 (e.g. quota full, already enrolled). */
public class ConflictException extends RuntimeException implements ErrorCodeCarrier {

    private final String errorCode;

    public ConflictException(String errorCode, Object... args) {
        super(MessagesUtils.getMessage(errorCode, args));
        this.errorCode = null;
    }

    private ConflictException(String message, String errorCode) {
        super(message);
        this.errorCode = errorCode;
    }

    public static ConflictException coded(String errorCode, String message) {
        return new ConflictException(message, errorCode);
    }

    @Override
    public String errorCode() {
        return errorCode;
    }
}
