package edu.courseflow.commonlibrary.dto.error;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.util.ArrayList;
import java.util.List;

/**
 * RFC-7807-flavoured error body returned by every service. Stable shape so that all clients
 * (React, Next.js, Flutter) can parse failures the same way.
 */
public record ErrorDto(String statusCode,
                       String title,
                       String detail,
                       @JsonInclude(JsonInclude.Include.NON_NULL) String errorCode,
                       List<String> fieldErrors) {

    public ErrorDto {
        if (fieldErrors == null) {
            fieldErrors = new ArrayList<>();
        }
    }

    public ErrorDto(String statusCode, String title, String detail) {
        this(statusCode, title, detail, null, new ArrayList<>());
    }

    public ErrorDto(String statusCode, String title, String detail, List<String> fieldErrors) {
        this(statusCode, title, detail, null, fieldErrors);
    }
}
