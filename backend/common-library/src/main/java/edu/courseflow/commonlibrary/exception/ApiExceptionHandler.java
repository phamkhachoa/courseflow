package edu.courseflow.commonlibrary.exception;

import edu.courseflow.commonlibrary.dto.error.ErrorDto;
import jakarta.validation.ConstraintViolationException;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.converter.HttpMessageNotReadableException;

/**
 * Single error contract for every service. Imported by each service's component
 * scan so the
 * JSON error shape ({@link ErrorDto}) is identical everywhere. Domain code
 * throws typed
 * exceptions; this advice maps them to HTTP status codes.
 */
@RestControllerAdvice
public class ApiExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);
    private static final String INVALID_REQUEST = "Request information is not valid";

    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<ErrorDto> handleNotFound(NotFoundException ex) {
        return build(HttpStatus.NOT_FOUND, ex.getMessage(), ex, null);
    }

    @ExceptionHandler(UnauthorizedException.class)
    public ResponseEntity<ErrorDto> handleUnauthorized(UnauthorizedException ex) {
        return build(HttpStatus.UNAUTHORIZED, ex.getMessage(), ex, null);
    }

    @ExceptionHandler(ForbiddenException.class)
    public ResponseEntity<ErrorDto> handleForbidden(ForbiddenException ex) {
        return build(HttpStatus.FORBIDDEN, ex.getMessage(), ex, null);
    }

    @ExceptionHandler(BadRequestException.class)
    public ResponseEntity<ErrorDto> handleBadRequest(RuntimeException ex) {
        return build(HttpStatus.BAD_REQUEST, ex.getMessage(), ex, null);
    }

    @ExceptionHandler({ DuplicatedException.class, ConflictException.class })
    public ResponseEntity<ErrorDto> handleConflict(RuntimeException ex) {
        return build(HttpStatus.CONFLICT, ex.getMessage(), ex, null);
    }

    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<ErrorDto> handleResponseStatus(ResponseStatusException ex) {
        HttpStatus status = HttpStatus.valueOf(ex.getStatusCode().value());
        String detail = ex.getReason() == null ? status.getReasonPhrase() : ex.getReason();
        return build(status, detail, ex, null);
    }

    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
    public ResponseEntity<ErrorDto> handleUnsupportedMediaType(HttpMediaTypeNotSupportedException ex) {
        return build(HttpStatus.UNSUPPORTED_MEDIA_TYPE, ex.getMessage(), ex, null);
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ErrorDto> handleUnsupportedMethod(HttpRequestMethodNotSupportedException ex) {
        return build(HttpStatus.METHOD_NOT_ALLOWED, ex.getMessage(), ex, null);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorDto> handleValidation(MethodArgumentNotValidException ex) {
        List<String> errors = ex.getBindingResult().getFieldErrors().stream()
                .map(e -> e.getField() + " " + e.getDefaultMessage())
                .toList();
        return build(HttpStatus.BAD_REQUEST, INVALID_REQUEST, ex, errors);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorDto> handleUnreadableBody(HttpMessageNotReadableException ex) {
        return build(HttpStatus.BAD_REQUEST, INVALID_REQUEST, ex,
                List.of("request body contains malformed JSON or an invalid field type"));
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ErrorDto> handleTypeMismatch(MethodArgumentTypeMismatchException ex) {
        String field = ex.getName() == null ? "request value" : ex.getName();
        String type = ex.getRequiredType() == null ? "expected type" : ex.getRequiredType().getSimpleName();
        return build(HttpStatus.BAD_REQUEST, INVALID_REQUEST, ex, List.of(field + " must be a valid " + type));
    }

    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<ErrorDto> handleConstraintViolation(ConstraintViolationException ex) {
        List<String> errors = ex.getConstraintViolations().stream()
                .map(v -> v.getPropertyPath() + ": " + v.getMessage())
                .toList();
        return build(HttpStatus.BAD_REQUEST, INVALID_REQUEST, ex, errors);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorDto> handleOther(Exception ex) {
        log.error("Unhandled exception", ex);
        return build(HttpStatus.INTERNAL_SERVER_ERROR, "Internal server error", ex, null);
    }

    private ResponseEntity<ErrorDto> build(HttpStatus status, String detail, Throwable ex, List<String> fieldErrors) {
        String errorCode = errorCode(ex);
        ErrorDto body = fieldErrors == null
                ? new ErrorDto(status.toString(), status.getReasonPhrase(), detail, errorCode, null)
                : new ErrorDto(status.toString(), status.getReasonPhrase(), detail, errorCode, fieldErrors);
        return ResponseEntity.status(status).body(body);
    }

    private String errorCode(Throwable ex) {
        if (ex instanceof ErrorCodeCarrier carrier) {
            return carrier.errorCode();
        }
        return null;
    }
}
