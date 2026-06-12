package edu.courseflow.course.exception;

import edu.courseflow.commonlibrary.dto.error.ErrorDto;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * Maps service-local exceptions that the shared {@code ApiExceptionHandler} does not know about.
 * Spring resolves the most specific exception handler across all advices, so the 403 mapping here
 * wins over the shared catch-all {@code Exception -> 500} handler.
 */
@RestControllerAdvice
public class LocalExceptionHandler {

    @ExceptionHandler(ForbiddenException.class)
    public ResponseEntity<ErrorDto> handleForbidden(ForbiddenException ex) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
                .body(new ErrorDto(HttpStatus.FORBIDDEN.toString(),
                        HttpStatus.FORBIDDEN.getReasonPhrase(), ex.getMessage()));
    }
}
