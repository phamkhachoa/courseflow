package edu.courseflow.course.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
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
            Instant createdAt,
            List<CourseMaterialDto> materials
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
            @NotBlank String level
    ) {
    }

    public record AddCourseMaterialRequestDto(
            @NotBlank String title,
            @JsonAlias("type") @NotBlank String materialType,
            UUID mediaId,
            @PositiveOrZero Integer position
    ) {
    }
}
