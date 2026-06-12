package edu.courseflow.certificate.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * The actor id is taken from the authenticated caller (gateway identity), not the body, so it is not a
 * field here. The body only carries the human-readable revocation reason.
 */
public record RevokeCertificateRequestDto(
        @NotBlank String reason
) {
}
