package edu.courseflow.course.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import java.math.BigDecimal;
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
            List<ItemOutlineDto> items,
            List<ModulePrerequisiteOutlineDto> prerequisites
    ) {
        public ModuleOutlineDto(
                String moduleId,
                String title,
                String description,
                int position,
                String status,
                List<ItemOutlineDto> items
        ) {
            this(moduleId, title, description, position, status, items, List.of());
        }
    }

    public record ModulePrerequisiteOutlineDto(
            String requiredModuleId,
            String ruleType
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

    public record CourseReviewAuditDto(
            String id,
            String courseId,
            int versionNo,
            String actorId,
            String actorRole,
            String action,
            String fromState,
            String toState,
            String note,
            List<String> checklist,
            Instant createdAt
    ) {
    }

    public record CourseReviewQueueItemDto(
            String courseId,
            String title,
            String slug,
            String summary,
            String status,
            String reviewState,
            int currentVersionNo,
            String ownerId,
            String departmentId,
            String lastAuthoredBy,
            int moduleCount,
            int itemCount,
            String submittedBy,
            Instant submittedAt
    ) {
    }

    public record CourseVersionDiffDto(
            String courseId,
            int draftVersionNo,
            Integer publishedVersionNo,
            String baseLabel,
            String targetLabel,
            int addedModules,
            int removedModules,
            int changedModules,
            int movedModules,
            int addedItems,
            int removedItems,
            int changedItems,
            int movedItems,
            int requiredItemsAdded,
            int requiredItemsRemoved,
            List<CourseVersionDiffChangeDto> changes,
            List<String> warnings
    ) {
    }

    public record CourseVersionDiffChangeDto(
            String scope,
            String changeType,
            String moduleId,
            String itemId,
            String title,
            String field,
            String fromValue,
            String toValue
    ) {
    }

    // ---- requests ----

    public record CreateCourseDraftRequestDto(
            @NotBlank String code,
            @NotBlank String title,
            @NotBlank String slug,
            @NotBlank String summary,
            @NotNull UUID departmentId,
            String level,
            @PositiveOrZero BigDecimal listPrice,
            String currency
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

    /** Reviewer decision payload for approve/reject; reject requires a note. */
    public record ReviewDecisionRequestDto(
            String note,
            List<String> checklist
    ) {
    }

    public record RollbackVersionRequestDto(
            String note,
            Integer expectedCurrentVersionNo
    ) {
    }

    /** Create a new authoring module under a course draft. Position is assigned by the server. */
    public record CreateModuleRequestDto(
            @NotBlank String title,
            String description,
            String status
    ) {
    }

    public record UpdateModuleRequestDto(
            @NotBlank String title,
            String description
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

    public record UpdateModuleItemRequestDto(
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
