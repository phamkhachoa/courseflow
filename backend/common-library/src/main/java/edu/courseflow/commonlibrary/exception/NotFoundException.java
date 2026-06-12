package edu.courseflow.commonlibrary.exception;

import edu.courseflow.commonlibrary.utils.MessagesUtils;

public class NotFoundException extends RuntimeException {

    public NotFoundException(String errorCode, Object... args) {
        super(MessagesUtils.getMessage(errorCode, args));
    }
}
