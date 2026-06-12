package edu.courseflow.organization.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import java.time.LocalDate;

public final class OrganizationDtos {

    private OrganizationDtos() {
    }

    public record DepartmentDto(
            String id,
            String code,
            String name,
            String faculty,
            String status
    ) {
    }

    public record AcademicTermDto(
            String id,
            String code,
            String name,
            LocalDate startDate,
            LocalDate endDate,
            String status
    ) {
    }

    public record CourseSectionDto(
            String id,
            String courseId,
            String termId,
            String sectionCode,
            String instructorId,
            int capacity,
            String status
    ) {
    }

    public record CreateCourseSectionRequestDto(
            @NotBlank String courseId,
            @NotBlank String termId,
            @NotBlank String sectionCode,
            @NotBlank String instructorId,
            @NotNull @Positive Integer capacity
    ) {
    }
}
