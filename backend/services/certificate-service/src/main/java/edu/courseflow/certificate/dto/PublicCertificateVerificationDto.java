package edu.courseflow.certificate.dto;

import java.time.Instant;

/**
 * Public-facing verification result for the unauthenticated {@code /public/certificates/verify/{code}}
 * endpoint. Deliberately omits PII (student id, final grade) that the internal DTO carries: anyone with
 * a verification code can hit this endpoint, so it returns only enough to confirm a certificate is
 * genuine and current.
 *
 * @param valid           whether a certificate exists for the code AND is still in ISSUED status
 * @param verificationCode the code that was checked (echoed back)
 * @param courseId        the course the certificate is for (no student/grade detail)
 * @param status          ISSUED / REVOKED
 * @param issuedAt        when it was issued
 */
public record PublicCertificateVerificationDto(
        boolean valid,
        String verificationCode,
        String courseId,
        String status,
        Instant issuedAt
) {
}
