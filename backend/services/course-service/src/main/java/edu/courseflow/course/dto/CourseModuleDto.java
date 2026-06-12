package edu.courseflow.course.dto;

import java.util.List;

public record CourseModuleDto(
        String id,
        String title,
        String description,
        int position,
        String status,
        List<ModuleItemDto> items
) {
}
