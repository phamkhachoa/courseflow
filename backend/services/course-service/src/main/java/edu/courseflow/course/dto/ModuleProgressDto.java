package edu.courseflow.course.dto;

import java.time.Instant;

public record ModuleProgressDto(
        String id,
        String courseId,
        String moduleId,
        String studentId,
        String status,
        Instant completedAt
) {
}
