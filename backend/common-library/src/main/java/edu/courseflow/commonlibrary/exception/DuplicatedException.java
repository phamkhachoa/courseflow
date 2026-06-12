package edu.courseflow.commonlibrary.exception;

import edu.courseflow.commonlibrary.utils.MessagesUtils;

public class DuplicatedException extends RuntimeException {

    public DuplicatedException(String errorCode, Object... args) {
        super(MessagesUtils.getMessage(errorCode, args));
    }
}
