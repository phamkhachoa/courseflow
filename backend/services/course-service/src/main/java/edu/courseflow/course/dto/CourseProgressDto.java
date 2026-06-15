package edu.courseflow.course.dto;

import java.time.Instant;
import java.util.List;

public record CourseProgressDto(
        String courseId,
        Integer publishedVersionNo,
        String studentId,
        int totalModules,
        int completedModules,
        int totalItems,
        int completedItems,
        int totalRequiredItems,
        int completedRequiredItems,
        int percentComplete,
        boolean completed,
        List<ProgressBreakdownDto> breakdown,
        List<ModuleProgressSummaryDto> modules,
        List<ItemProgressDto> items,
        List<MissingRequirementDto> missingRequirements
) {
    public CourseProgressDto(
            String courseId,
            String studentId,
            int totalModules,
            int completedModules,
            int totalItems,
            int completedItems,
            int totalRequiredItems,
            int completedRequiredItems,
            int percentComplete,
            boolean completed,
            List<ProgressBreakdownDto> breakdown,
            List<ModuleProgressSummaryDto> modules,
            List<ItemProgressDto> items,
            List<MissingRequirementDto> missingRequirements
    ) {
        this(courseId, null, studentId, totalModules, completedModules, totalItems, completedItems,
                totalRequiredItems, completedRequiredItems, percentComplete, completed, breakdown, modules,
                items, missingRequirements);
    }

    public record ProgressBreakdownDto(
            String itemType,
            int total,
            int completed,
            int required,
            int completedRequired
    ) {
    }

    public record ModuleProgressSummaryDto(
            String moduleId,
            int totalItems,
            int completedItems,
            int totalRequiredItems,
            int completedRequiredItems,
            int percentComplete,
            boolean completed
    ) {
    }

    public record ItemProgressDto(
            String itemId,
            String moduleId,
            String itemType,
            String title,
            boolean required,
            String status,
            String progressType,
            Instant completedAt
    ) {
    }

    public record MissingRequirementDto(
            String itemId,
            String moduleId,
            String itemType,
            String title
    ) {
    }
}
