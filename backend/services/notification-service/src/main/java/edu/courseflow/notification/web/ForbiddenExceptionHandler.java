package edu.courseflow.notification.web;

import edu.courseflow.commonlibrary.dto.error.ErrorDto;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * Maps {@link ForbiddenException} to HTTP 403 using the shared {@link ErrorDto} shape.
 * common-library's ApiExceptionHandler has no 403 mapping; this service-local advice fills the
 * gap. Spring selects the most specific @ExceptionHandler, so this wins over the common catch-all.
 */
@RestControllerAdvice
public class ForbiddenExceptionHandler {

    @ExceptionHandler(ForbiddenException.class)
    public ResponseEntity<ErrorDto> handleForbidden(ForbiddenException ex) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
                .body(new ErrorDto(HttpStatus.FORBIDDEN.toString(),
                        HttpStatus.FORBIDDEN.getReasonPhrase(), ex.getMessage()));
    }
}
