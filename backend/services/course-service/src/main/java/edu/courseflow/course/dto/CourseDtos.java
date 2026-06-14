package edu.courseflow.course.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public final class CourseDtos {

    private CourseDtos() {
    }

    public record CourseDto(
            String id,
            String code,
            String title,
            String slug,
            String summary,
            String departmentId,
            String ownerId,
            String level,
            String status,
            BigDecimal listPrice,
            String currency,
            String priceStatus,
            Instant createdAt,
            List<CourseMaterialDto> materials
    ) {
    }

    public record CourseMetadataDto(
            String id,
            String status,
            String reviewState,
            String ownerId,
            String departmentId,
            String title,
            String slug,
            BigDecimal listPrice,
            String currency,
            String priceStatus
    ) {
    }

    public record CoursePricingDto(
            String courseId,
            BigDecimal listPrice,
            String currency,
            String priceStatus,
            boolean purchasable,
            String priceSource
    ) {
    }

    public record CourseMaterialDto(
            String id,
            String courseId,
            String title,
            String materialType,
            String mediaId,
            int position
    ) {
    }

    public record CreateCourseRequestDto(
            @NotBlank String code,
            @NotBlank String title,
            @NotBlank String slug,
            @NotBlank String summary,
            @NotNull UUID departmentId,
            @NotBlank String level,
            @PositiveOrZero BigDecimal listPrice,
            String currency
    ) {
        public CreateCourseRequestDto(
                String code,
                String title,
                String slug,
                String summary,
                UUID departmentId,
                String level) {
            this(code, title, slug, summary, departmentId, level, null, null);
        }
    }

    public record UpdateCoursePricingRequestDto(
            @PositiveOrZero BigDecimal listPrice,
            String currency
    ) {
    }

    public record AddCourseMaterialRequestDto(
            @NotBlank String title,
            @JsonAlias("type") @NotBlank String materialType,
            UUID mediaId,
            @PositiveOrZero Integer position
    ) {
    }

    public record PresignedDownloadDto(
            String storageKey,
            String downloadUrl,
            Instant expiresAt
    ) {
    }
}
