package edu.courseflow.commonlibrary.exception;

import edu.courseflow.commonlibrary.utils.MessagesUtils;

public class BadRequestException extends RuntimeException {

    public BadRequestException(String errorCode, Object... args) {
        super(MessagesUtils.getMessage(errorCode, args));
    }
}
