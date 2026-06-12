package edu.courseflow.commonlibrary.dto.error;

import java.util.ArrayList;
import java.util.List;

/**
 * RFC-7807-flavoured error body returned by every service. Stable shape so that all clients
 * (React, Next.js, Flutter) can parse failures the same way.
 */
public record ErrorDto(String statusCode, String title, String detail, List<String> fieldErrors) {

    public ErrorDto(String statusCode, String title, String detail) {
        this(statusCode, title, detail, new ArrayList<>());
    }
}
