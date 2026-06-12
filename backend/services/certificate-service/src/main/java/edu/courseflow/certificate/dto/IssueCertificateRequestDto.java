package edu.courseflow.certificate.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;

/**
 * {@code actorId} is NOT validated/trusted from the request body: the controller overwrites it with the
 * authenticated caller's id from the gateway identity ({@code CurrentUser}). It remains in the record so
 * internal callers (e.g. the final-grade consumer issuing as "system") can pass it directly to the service.
 */
public record IssueCertificateRequestDto(
        @NotBlank String studentId,
        @NotBlank String courseId,
        @NotNull BigDecimal finalGrade,
        String actorId
) {
}
