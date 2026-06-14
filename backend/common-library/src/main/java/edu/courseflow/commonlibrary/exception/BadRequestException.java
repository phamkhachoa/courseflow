package edu.courseflow.commonlibrary.exception;

import edu.courseflow.commonlibrary.utils.MessagesUtils;

public class BadRequestException extends RuntimeException implements ErrorCodeCarrier {

    private final String errorCode;

    public BadRequestException(String errorCode, Object... args) {
        super(MessagesUtils.getMessage(errorCode, args));
        this.errorCode = null;
    }

    private BadRequestException(String message, String errorCode) {
        super(message);
        this.errorCode = errorCode;
    }

    public static BadRequestException coded(String errorCode, String message) {
        return new BadRequestException(message, errorCode);
    }

    @Override
    public String errorCode() {
        return errorCode;
    }
}
