package edu.courseflow.certificate.dto;

import java.math.BigDecimal;
import java.time.Instant;

public record CertificateVerificationDto(
        String certificateId,
        String verificationCode,
        String publicSlug,
        String studentId,
        String courseId,
        BigDecimal finalGrade,
        String status,
        Instant issuedAt
) {
}
