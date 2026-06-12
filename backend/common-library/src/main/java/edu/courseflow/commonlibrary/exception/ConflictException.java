package edu.courseflow.commonlibrary.exception;

import edu.courseflow.commonlibrary.utils.MessagesUtils;

/** Domain rule violation that maps to HTTP 409 (e.g. quota full, already enrolled). */
public class ConflictException extends RuntimeException {

    public ConflictException(String errorCode, Object... args) {
        super(MessagesUtils.getMessage(errorCode, args));
    }
}
