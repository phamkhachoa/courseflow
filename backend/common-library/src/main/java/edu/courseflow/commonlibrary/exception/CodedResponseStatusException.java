package edu.courseflow.commonlibrary.exception;

import org.springframework.http.HttpStatusCode;
import org.springframework.web.server.ResponseStatusException;

public class CodedResponseStatusException extends ResponseStatusException implements ErrorCodeCarrier {

    private final String errorCode;

    public CodedResponseStatusException(HttpStatusCode status, String errorCode, String reason) {
        super(status, reason);
        this.errorCode = errorCode;
    }

    @Override
    public String errorCode() {
        return errorCode;
    }
}
