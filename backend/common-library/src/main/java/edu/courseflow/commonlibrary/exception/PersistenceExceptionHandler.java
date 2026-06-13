package edu.courseflow.commonlibrary.exception;

import edu.courseflow.commonlibrary.dto.error.ErrorDto;
import jakarta.persistence.OptimisticLockException;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
@ConditionalOnClass(name = {
        "org.springframework.dao.DataIntegrityViolationException",
        "org.springframework.orm.ObjectOptimisticLockingFailureException",
        "jakarta.persistence.OptimisticLockException"
})
public class PersistenceExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(PersistenceExceptionHandler.class);

    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<ErrorDto> handleDataIntegrity(DataIntegrityViolationException ex) {
        log.warn("Data integrity violation", ex);
        return build(HttpStatus.CONFLICT, "Request conflicts with existing data");
    }

    @ExceptionHandler({ObjectOptimisticLockingFailureException.class, OptimisticLockException.class})
    public ResponseEntity<ErrorDto> handleOptimisticLock(Exception ex) {
        log.warn("Optimistic locking conflict", ex);
        return build(HttpStatus.CONFLICT, "Resource was modified concurrently; retry the request");
    }

    private ResponseEntity<ErrorDto> build(HttpStatus status, String detail) {
        ErrorDto body = new ErrorDto(status.toString(), status.getReasonPhrase(), detail, List.of());
        return ResponseEntity.status(status).body(body);
    }
}
