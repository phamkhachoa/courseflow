package edu.courseflow.certificate.dto;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record CertificateEligibilityDto(
        Instant generatedAt,
        String courseId,
        String studentId,
        boolean eligible,
        String status,
        boolean completionEligible,
        boolean gradeEligible,
        boolean requiredItemsEligible,
        boolean issued,
        BigDecimal finalGrade,
        BigDecimal gradeThreshold,
        String finalGradeStatus,
        String certificateId,
        String verificationCode,
        Instant issuedAt,
        List<MissingRequirementDto> missingRequirements
) {
    public CertificateEligibilityDto {
        missingRequirements = missingRequirements == null ? List.of() : List.copyOf(missingRequirements);
    }

    public record MissingRequirementDto(
            String code,
            String label,
            String detail
    ) {
    }
}
