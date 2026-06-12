package edu.courseflow.common.error;

import java.time.Instant;

public record ErrorResponse(
        String code,
        String message,
        String traceId,
        Instant timestamp
) {
    public static ErrorResponse of(String code, String message, String traceId) {
        return new ErrorResponse(code, message, traceId, Instant.now());
    }
}
