package edu.courseflow.commonlibrary.exception;

import edu.courseflow.commonlibrary.utils.MessagesUtils;

/** Thrown when credentials / token are missing or invalid. Maps to HTTP 401. */
public class UnauthorizedException extends RuntimeException {

    public UnauthorizedException(String errorCode, Object... args) {
        super(MessagesUtils.getMessage(errorCode, args));
    }
}
