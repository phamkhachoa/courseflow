package edu.courseflow.course.dto;

import java.time.Instant;
import java.util.List;

public final class LearningDtos {

    private LearningDtos() {
    }

    public record LearnerNextActionDto(
            Instant generatedAt,
            String kind,
            CourseSummaryDto course,
            ModuleSummaryDto module,
            ItemSummaryDto item,
            TargetDto target,
            String href,
            String ctaLabel,
            String reason,
            String reasonCode,
            int priorityScore,
            Instant dueAt
    ) {
        public LearnerNextActionDto(
                Instant generatedAt,
                String kind,
                CourseSummaryDto course,
                ModuleSummaryDto module,
                ItemSummaryDto item,
                TargetDto target,
                String href,
                String ctaLabel,
                String reason
        ) {
            this(generatedAt, kind, course, module, item, target, href, ctaLabel, reason, null, 0, null);
        }
    }

    public record CourseSummaryDto(
            String id,
            String title,
            String slug,
            int progressPercent
    ) {
    }

    public record ModuleSummaryDto(
            String id,
            String title,
            int progressPercent,
            int totalItems,
            int completedItems,
            int totalRequiredItems,
            int completedRequiredItems,
            boolean completed
    ) {
    }

    public record ItemSummaryDto(
            String id,
            String type,
            String title,
            boolean required,
            String status,
            String refId
    ) {
    }

    public record TargetDto(
            String type,
            String id,
            String refId
    ) {
    }

    public record LearnerCoursePlayerDto(
            Instant generatedAt,
            String courseId,
            Integer publishedVersionNo,
            List<CourseModuleDto> modules,
            CourseProgressDto progress,
            CertificateEligibilityDto certificateEligibility,
            CoursePlayerNextActionDto nextAction,
            List<CoursePlayerModuleStateDto> moduleStates,
            List<CoursePlayerItemStateDto> itemStates
    ) {
        public LearnerCoursePlayerDto(
                Instant generatedAt,
                String courseId,
                List<CourseModuleDto> modules,
                CourseProgressDto progress,
                CertificateEligibilityDto certificateEligibility,
                CoursePlayerNextActionDto nextAction,
                List<CoursePlayerModuleStateDto> moduleStates,
                List<CoursePlayerItemStateDto> itemStates
        ) {
            this(generatedAt, courseId, null, modules, progress, certificateEligibility, nextAction, moduleStates,
                    itemStates);
        }
    }

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
            java.math.BigDecimal finalGrade,
            java.math.BigDecimal gradeThreshold,
            String finalGradeStatus,
            String certificateId,
            String verificationCode,
            Instant issuedAt,
            List<CertificateMissingRequirementDto> missingRequirements
    ) {
        public CertificateEligibilityDto {
            missingRequirements = missingRequirements == null ? List.of() : List.copyOf(missingRequirements);
        }
    }

    public record CertificateMissingRequirementDto(
            String code,
            String label,
            String detail
    ) {
    }

    public record CoursePlayerNextActionDto(
            String kind,
            String moduleId,
            String itemId,
            String itemType,
            String title,
            boolean locked,
            String ctaLabel,
            String reason
    ) {
    }

    public record CoursePlayerModuleStateDto(
            String moduleId,
            boolean locked,
            String lockedReasonCode,
            String lockedReasonText,
            List<CoursePlayerPrerequisiteDto> unmetPrerequisites
    ) {
    }

    public record CoursePlayerPrerequisiteDto(
            String moduleId,
            String title,
            boolean completed
    ) {
    }

    public record CoursePlayerItemStateDto(
            String itemId,
            String moduleId,
            String itemType,
            boolean required,
            String progressStatus,
            String progressType,
            Instant completedAt,
            String completionMode,
            boolean locked,
            String lockedReasonCode,
            String lockedReasonText,
            String sourceStatus,
            Instant sourceDueAt,
            Instant sourceLockAt
    ) {
    }

    public record LearnerLearningPathDto(
            Instant generatedAt,
            String courseId,
            Integer publishedVersionNo,
            String studentId,
            String cohortId,
            String sectionId,
            CourseProgressDto progress,
            CoursePlayerNextActionDto nextAction,
            List<LearningPathModuleDto> modules
    ) {
    }

    public record LearningPathModuleDto(
            String moduleId,
            String title,
            String description,
            int position,
            boolean locked,
            String lockedReasonCode,
            String lockedReasonText,
            int percentComplete,
            int totalItems,
            int completedItems,
            int totalRequiredItems,
            int completedRequiredItems,
            boolean completed,
            List<CoursePlayerPrerequisiteDto> unmetPrerequisites,
            List<LearningPathItemDto> items
    ) {
    }

    public record LearningPathItemDto(
            String itemId,
            String itemType,
            String refId,
            String title,
            Integer estimatedMinutes,
            int position,
            boolean required,
            String progressStatus,
            String progressType,
            Instant completedAt,
            String completionMode,
            boolean locked,
            String lockedReasonCode,
            String sourceStatus,
            Instant sourceDueAt,
            Instant sourceLockAt
    ) {
    }

    public record LearningSourceStatusDto(
            String sourceType,
            String sourceId,
            String courseId,
            String title,
            String sourceStatus,
            Instant availableAt,
            Instant dueAt,
            Instant lockAt,
            String latestProgressStatus,
            String latestProgressId,
            int attemptsUsed,
            Integer attemptsAllowed,
            boolean completed,
            boolean overdue
    ) {
    }

    public record LearningAccessCheckRequestDto(
            String studentId,
            String sourceType,
            String sourceId
    ) {
    }

    public record LearningAccessCheckDto(
            Instant generatedAt,
            String courseId,
            String studentId,
            String sourceType,
            String sourceId,
            boolean allowed,
            String reasonCode,
            String reasonText,
            String moduleId,
            String itemId
    ) {
    }
}
