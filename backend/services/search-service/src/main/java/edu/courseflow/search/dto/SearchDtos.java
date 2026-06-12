package edu.courseflow.search.dto;

import jakarta.validation.constraints.NotBlank;
import java.time.Instant;
import java.util.List;

public final class SearchDtos {

    private SearchDtos() {
    }

    public record CourseSearchDto(
            String id,
            String code,
            String title,
            String slug,
            String summary,
            String departmentId,
            String level,
            String status,
            Instant updatedAt
    ) {
    }

    /**
     * A page of search hits. {@code totalHits} is the total number of matching documents across all
     * pages (Elasticsearch total hit count), not the size of {@code content}.
     */
    public record CourseSearchPageDto(
            List<CourseSearchDto> content,
            long totalHits,
            int page,
            int size
    ) {
    }

    public record CourseRecommendationDto(
            CourseSearchDto course,
            String reason
    ) {
    }

    public record IndexCourseRequestDto(
            @NotBlank String id,
            @NotBlank String code,
            @NotBlank String title,
            @NotBlank String slug,
            @NotBlank String summary,
            @NotBlank String departmentId,
            @NotBlank String level,
            @NotBlank String status
    ) {
    }
}
