package edu.courseflow.commonlibrary.exception;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.dto.error.ErrorDto;
import java.util.List;
import java.util.Objects;
import org.junit.jupiter.api.Test;
import org.springframework.http.ResponseEntity;

class ApiExceptionHandlerTest {

    private final ApiExceptionHandler handler = new ApiExceptionHandler();
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void codedExceptionIncludesMachineReadableErrorCode() {
        ResponseEntity<ErrorDto> response = handler.handleConflict(
                ConflictException.coded("COUPON_IMPORT_RESULT_HASH_MISMATCH", "Result hash no longer matches"));

        ErrorDto body = Objects.requireNonNull(response.getBody());
        assertThat(response.getStatusCode().value()).isEqualTo(409);
        assertThat(body.statusCode()).isEqualTo("409 CONFLICT");
        assertThat(body.detail()).isEqualTo("Result hash no longer matches");
        assertThat(body.errorCode()).isEqualTo("COUPON_IMPORT_RESULT_HASH_MISMATCH");
        assertThat(body.fieldErrors()).isEmpty();
    }

    @Test
    void legacyErrorDtoOmitsNullErrorCodeFromJson() throws Exception {
        ErrorDto body = new ErrorDto("400 BAD_REQUEST", "Bad Request", "Invalid request", List.of());

        String json = objectMapper.writeValueAsString(body);

        assertThat(json).contains("\"statusCode\":\"400 BAD_REQUEST\"");
        assertThat(json).doesNotContain("errorCode");
    }
}
