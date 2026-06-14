package edu.courseflow.commonlibrary.exception;

import edu.courseflow.commonlibrary.utils.MessagesUtils;

public class NotFoundException extends RuntimeException implements ErrorCodeCarrier {

    private final String errorCode;

    public NotFoundException(String errorCode, Object... args) {
        super(MessagesUtils.getMessage(errorCode, args));
        this.errorCode = null;
    }

    private NotFoundException(String message, String errorCode) {
        super(message);
        this.errorCode = errorCode;
    }

    public static NotFoundException coded(String errorCode, String message) {
        return new NotFoundException(message, errorCode);
    }

    @Override
    public String errorCode() {
        return errorCode;
    }
}
