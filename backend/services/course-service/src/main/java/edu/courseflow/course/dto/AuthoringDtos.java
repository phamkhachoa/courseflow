package edu.courseflow.course.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public final class AuthoringDtos {

    private AuthoringDtos() {
    }

    public record CourseDraftDto(
            String courseId,
            String title,
            String slug,
            String summary,
            String status,
            String reviewState,
            int currentVersionNo,
            String lastAuthoredBy,
            List<ModuleOutlineDto> modules
    ) {
    }

    public record ModuleOutlineDto(
            String moduleId,
            String title,
            String description,
            int position,
            String status,
            List<ItemOutlineDto> items
    ) {
    }

    public record ItemOutlineDto(
            String itemId,
            String itemType,
            String refId,
            String title,
            String description,
            String videoMediaId,
            List<String> documentMediaIds,
            String contentUrl,
            Integer estimatedMinutes,
            int position,
            boolean required
    ) {
    }

    public record CourseVersionDto(
            String id,
            String courseId,
            int versionNo,
            String state,
            String createdBy,
            String note,
            Instant createdAt,
            Instant publishedAt
    ) {
    }

    // ---- requests ----

    public record CreateCourseDraftRequestDto(
            @NotBlank String code,
            @NotBlank String title,
            @NotBlank String slug,
            @NotBlank String summary,
            @NotNull UUID departmentId,
            String level
    ) {
    }

    /**
     * Full reorder of the curriculum: client sends the desired module/item order.
     * The server rewrites positions to match.
     */
    public record UpdateCurriculumRequestDto(
            @NotNull List<ModuleOrderDto> modules
    ) {
    }

    public record ModuleOrderDto(
            @NotBlank String moduleId,
            List<String> itemIds
    ) {
    }

    public record CreateVersionRequestDto(
            String note
    ) {
    }

    public record SubmitReviewRequestDto() {
    }

    /** Reviewer decision payload for approve/reject; the note is optional reviewer feedback. */
    public record ReviewDecisionRequestDto(
            String note
    ) {
    }

    /** Create a new authoring module under a course draft. Position is assigned by the server. */
    public record CreateModuleRequestDto(
            @NotBlank String title,
            String description,
            String status
    ) {
    }

    /** Create a new item inside a module. Position is assigned by the server. */
    public record CreateModuleItemRequestDto(
            @NotBlank String itemType,
            String refId,
            @NotBlank String title,
            String description,
            UUID videoMediaId,
            List<String> documentMediaIds,
            String contentUrl,
            Integer estimatedMinutes,
            Boolean required
    ) {
    }
}
